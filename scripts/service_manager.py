#!/usr/bin/env python3
"""
ServiceMatrix クロスプラットフォーム サービスマネージャー
Windows 11 / Linux (Ubuntu) 対応

使用方法:
    python3 scripts/service_manager.py start    # 全サービス起動
    python3 scripts/service_manager.py stop     # 全サービス停止
    python3 scripts/service_manager.py restart  # 全サービス再起動
    python3 scripts/service_manager.py status   # サービス状態確認
    python3 scripts/service_manager.py setup    # 環境セットアップ（.env生成）
"""

import json
import logging
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ===== 設定定数 =====
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PID_FILE = PROJECT_ROOT / ".service_pids.json"
ENV_FILE = PROJECT_ROOT / ".env"
LOG_FILE = PROJECT_ROOT / "logs" / "service_manager.log"

# デフォルトポート（競合時は自動で次のポートを試す）
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_REDIS_PORT = 6379

# ポート検索範囲（各サービス最大10ポートを試す）
PORT_SEARCH_RANGE = 10

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# ===== ログ設定 =====
LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("service_manager")


# ===== ユーティリティ関数 =====

def get_local_ip() -> str:
    """動的に割り当てられたローカルIPアドレスを取得"""
    try:
        # 外部接続でローカルIPを検出（実際の接続は行わない）
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        pass

    # フォールバック: ホスト名からIP解決
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """ポートが使用可能かどうかを確認"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(start_port: int, search_range: int = PORT_SEARCH_RANGE) -> int:
    """利用可能なポートを検索して返す"""
    for port in range(start_port, start_port + search_range):
        if is_port_available(port):
            logger.info(f"ポート {port} が利用可能です")
            return port
        else:
            logger.warning(f"ポート {port} は使用中です。次を試します...")
    raise RuntimeError(
        f"ポート {start_port}〜{start_port + search_range - 1} がすべて使用中です"
    )


def load_pids() -> dict:
    """PIDファイルを読み込む"""
    if PID_FILE.exists():
        try:
            return json.loads(PID_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_pids(pids: dict) -> None:
    """PIDファイルを保存する"""
    PID_FILE.write_text(json.dumps(pids, indent=2), encoding="utf-8")


def is_process_running(pid: int) -> bool:
    """プロセスが実行中かどうか確認"""
    if pid <= 0:
        return False
    try:
        if IS_WINDOWS:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def kill_process(pid: int, force: bool = False) -> bool:
    """プロセスを停止する"""
    if not is_process_running(pid):
        return True
    try:
        if IS_WINDOWS:
            os.kill(pid, signal.SIGTERM)
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
        time.sleep(1)
        return not is_process_running(pid)
    except Exception as e:
        logger.error(f"プロセス {pid} の停止に失敗: {e}")
        return False


def read_env() -> dict:
    """現在の.envファイルを読み込む"""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def write_env(env: dict) -> None:
    """現在の.envファイルに設定を書き込む（既存値を上書き）"""
    lines = []
    if ENV_FILE.exists():
        existing_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
        existing_keys = set()
        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in env:
                    lines.append(f"{key}={env[key]}")
                    existing_keys.add(key)
                else:
                    lines.append(line)
            else:
                lines.append(line)
        # 新しいキーを追加
        for key, value in env.items():
            if key not in existing_keys:
                lines.append(f"{key}={value}")
    else:
        for key, value in env.items():
            lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info(f".env ファイルを更新しました: {ENV_FILE}")


# ===== 環境セットアップ =====

def setup_environment() -> dict:
    """
    動的IP・ポート検出を行い .env を生成/更新する
    Returns: 確定した設定辞書
    """
    logger.info("=== 環境設定の自動検出を開始 ===")

    local_ip = get_local_ip()
    logger.info(f"検出されたローカルIPアドレス: {local_ip}")

    backend_port = find_available_port(DEFAULT_BACKEND_PORT)
    frontend_port = find_available_port(DEFAULT_FRONTEND_PORT)
    postgres_port = find_available_port(DEFAULT_POSTGRES_PORT)
    redis_port = find_available_port(DEFAULT_REDIS_PORT)

    config = {
        "BIND_HOST": "0.0.0.0",
        "BACKEND_PORT": str(backend_port),
        "FRONTEND_PORT": str(frontend_port),
        "LOCAL_IP": local_ip,
        "BACKEND_URL": f"http://{local_ip}:{backend_port}",
        "FRONTEND_URL": f"http://{local_ip}:{frontend_port}",
        "DATABASE_URL": f"postgresql+asyncpg://servicematrix:changeme@localhost:{postgres_port}/servicematrix",
        "REDIS_URL": f"redis://localhost:{redis_port}/0",
        "ALLOWED_ORIGINS": (
            f'["http://localhost:{frontend_port}",'
            f'"http://{local_ip}:{frontend_port}"]'
        ),
        "SECRET_KEY": _generate_secret_key(),
        "ENVIRONMENT": "production",
        "POSTGRES_PORT": str(postgres_port),
        "REDIS_PORT": str(redis_port),
    }

    write_env(config)

    logger.info(f"バックエンドURL: {config['BACKEND_URL']}")
    logger.info(f"フロントエンドURL: {config['FRONTEND_URL']}")
    return config


def _generate_secret_key() -> str:
    """既存のSECRET_KEYを使用するか新規生成"""
    existing = read_env().get("SECRET_KEY", "")
    if existing and len(existing) >= 32:
        return existing
    import secrets
    return secrets.token_hex(32)


# ===== サービス起動・停止 =====

def _get_venv_python() -> str:
    """仮想環境のPythonパスを返す"""
    if IS_WINDOWS:
        candidates = [
            PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
            PROJECT_ROOT / ".venv" / "Scripts" / "python3.exe",
        ]
    else:
        candidates = [
            PROJECT_ROOT / ".venv" / "bin" / "python3",
            PROJECT_ROOT / ".venv" / "bin" / "python",
        ]
    for p in candidates:
        if p.exists():
            return str(p)
    return sys.executable  # システムのPythonにフォールバック


def _get_uvicorn_path() -> str:
    """uvicornの実行パスを返す"""
    if IS_WINDOWS:
        p = PROJECT_ROOT / ".venv" / "Scripts" / "uvicorn.exe"
    else:
        p = PROJECT_ROOT / ".venv" / "bin" / "uvicorn"
    if p.exists():
        return str(p)
    return "uvicorn"


def _get_node_env() -> dict:
    """Node.js実行用の環境変数辞書を返す"""
    env = os.environ.copy()
    env_config = read_env()
    env["PORT"] = env_config.get("FRONTEND_PORT", str(DEFAULT_FRONTEND_PORT))
    env["NEXT_PUBLIC_API_URL"] = env_config.get(
        "BACKEND_URL", f"http://localhost:{DEFAULT_BACKEND_PORT}"
    )
    return env


def start_backend() -> Optional[int]:
    """バックエンド(FastAPI/uvicorn)を起動する"""
    env_config = read_env()
    host = env_config.get("BIND_HOST", "0.0.0.0")
    port = env_config.get("BACKEND_PORT", str(DEFAULT_BACKEND_PORT))

    # ポート再確認
    if not is_port_available(int(port)):
        port = str(find_available_port(int(port)))
        write_env({"BACKEND_PORT": port})

    uvicorn = _get_uvicorn_path()
    cmd = [uvicorn, "src.main:app", "--host", host, "--port", port, "--workers", "1"]

    env = os.environ.copy()
    env.update({k: v for k, v in env_config.items()})

    logger.info(f"バックエンド起動: {' '.join(cmd)} (WorkDir: {PROJECT_ROOT})")

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=open(PROJECT_ROOT / "logs" / "backend.log", "a"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0,
    )
    logger.info(f"バックエンド起動完了: PID={proc.pid}, Port={port}")
    return proc.pid


def start_frontend() -> Optional[int]:
    """フロントエンド(Next.js)を起動する"""
    frontend_dir = PROJECT_ROOT / "frontend"
    if not frontend_dir.exists():
        logger.warning("フロントエンドディレクトリが見つかりません。スキップします。")
        return None

    env_config = read_env()
    port = env_config.get("FRONTEND_PORT", str(DEFAULT_FRONTEND_PORT))

    if not is_port_available(int(port)):
        port = str(find_available_port(int(port)))
        write_env({"FRONTEND_PORT": port})

    # npm/node の検出
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    cmd = [npm_cmd, "start", "--", "-p", port]

    env = _get_node_env()
    env["PORT"] = port

    logger.info(f"フロントエンド起動: port={port} (WorkDir: {frontend_dir})")

    proc = subprocess.Popen(
        cmd,
        cwd=str(frontend_dir),
        env=env,
        stdout=open(PROJECT_ROOT / "logs" / "frontend.log", "a"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0,
    )
    logger.info(f"フロントエンド起動完了: PID={proc.pid}, Port={port}")
    return proc.pid


def start_services() -> None:
    """全サービスを起動する"""
    logger.info("=== ServiceMatrix サービス起動開始 ===")
    logger.info(f"プラットフォーム: {platform.system()} {platform.release()}")
    logger.info(f"プロジェクトルート: {PROJECT_ROOT}")

    # 環境設定を更新
    setup_environment()

    pids = {}

    # バックエンド起動
    backend_pid = start_backend()
    if backend_pid:
        pids["backend"] = backend_pid
        time.sleep(2)  # バックエンドの起動を少し待つ

    # フロントエンド起動
    frontend_pid = start_frontend()
    if frontend_pid:
        pids["frontend"] = frontend_pid

    save_pids(pids)

    env_config = read_env()
    logger.info("=== サービス起動完了 ===")
    logger.info(f"バックエンド:    {env_config.get('BACKEND_URL', 'N/A')}")
    logger.info(f"フロントエンド:  {env_config.get('FRONTEND_URL', 'N/A')}")
    logger.info(f"APIドキュメント: {env_config.get('BACKEND_URL', 'http://localhost:8000')}/docs")

    print("\n" + "="*50)
    print("ServiceMatrix が起動しました！")
    print(f"  バックエンド:    {env_config.get('BACKEND_URL', 'N/A')}")
    print(f"  フロントエンド:  {env_config.get('FRONTEND_URL', 'N/A')}")
    print(f"  API ドキュメント: {env_config.get('BACKEND_URL', 'http://localhost:8000')}/docs")
    print("="*50 + "\n")


def stop_services() -> None:
    """全サービスを停止する"""
    logger.info("=== ServiceMatrix サービス停止開始 ===")
    pids = load_pids()

    if not pids:
        logger.info("起動中のサービスが見つかりません")
        return

    for service_name, pid in pids.items():
        if is_process_running(pid):
            logger.info(f"{service_name} (PID={pid}) を停止中...")
            if kill_process(pid):
                logger.info(f"{service_name} を停止しました")
            else:
                logger.warning(f"{service_name} の停止に失敗。強制終了を試みます...")
                kill_process(pid, force=True)
        else:
            logger.info(f"{service_name} (PID={pid}) はすでに停止しています")

    PID_FILE.unlink(missing_ok=True)
    logger.info("=== サービス停止完了 ===")


def show_status() -> None:
    """サービスの状態を表示する"""
    pids = load_pids()
    env_config = read_env()
    local_ip = get_local_ip()

    print("\n" + "="*60)
    print("ServiceMatrix サービス状態")
    print("="*60)
    print(f"プラットフォーム: {platform.system()} {platform.release()}")
    print(f"ローカルIP:       {local_ip}")
    print()

    services = {
        "backend": {
            "port": env_config.get("BACKEND_PORT", str(DEFAULT_BACKEND_PORT)),
            "url": env_config.get("BACKEND_URL", "N/A"),
        },
        "frontend": {
            "port": env_config.get("FRONTEND_PORT", str(DEFAULT_FRONTEND_PORT)),
            "url": env_config.get("FRONTEND_URL", "N/A"),
        },
    }

    for service_name, info in services.items():
        pid = pids.get(service_name, 0)
        running = is_process_running(pid) if pid else False
        port_listening = not is_port_available(int(info["port"])) if info["port"] else False

        status_symbol = "✅" if (running or port_listening) else "❌"
        pid_str = f"PID={pid}" if pid else "PID=不明"
        print(f"  {status_symbol} {service_name:<12} {pid_str:<12} Port={info['port']:<6} {info['url']}")

    print()
    # ポート空き確認
    for port_name, default_port in [
        ("PostgreSQL", DEFAULT_POSTGRES_PORT),
        ("Redis", DEFAULT_REDIS_PORT),
    ]:
        configured_port = int(env_config.get(f"{port_name.upper()}_PORT", str(default_port)))
        in_use = not is_port_available(configured_port)
        symbol = "✅" if in_use else "⚠️ "
        print(f"  {symbol} {port_name:<12} Port={configured_port} {'(起動中)' if in_use else '(停止中)'}")

    print("="*60 + "\n")


def restart_services() -> None:
    """全サービスを再起動する"""
    logger.info("=== ServiceMatrix サービス再起動 ===")
    stop_services()
    time.sleep(2)
    start_services()


# ===== メインエントリポイント =====

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    commands = {
        "start": start_services,
        "stop": stop_services,
        "restart": restart_services,
        "status": show_status,
        "setup": lambda: setup_environment() and print("環境設定が完了しました"),
    }

    if command not in commands:
        print(f"不明なコマンド: {command}")
        print(f"使用可能なコマンド: {', '.join(commands.keys())}")
        sys.exit(1)

    try:
        commands[command]()
    except KeyboardInterrupt:
        logger.info("中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
