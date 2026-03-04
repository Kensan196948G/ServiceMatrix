#!/usr/bin/env python3
"""
ServiceMatrix 環境設定自動生成スクリプト
Windows / Linux 両対応

起動時に動的IPアドレスとポート競合を自動検出し、.envファイルを生成します。
"""

import os
import platform
import secrets
import socket
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


def get_local_ip() -> str:
    """動的に割り当てられたIPアドレスを取得"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def is_port_free(port: int) -> bool:
    """ポートが空いているか確認"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def find_free_port(start: int, end: int = None) -> int:
    """startから順にフリーなポートを返す"""
    if end is None:
        end = start + 10
    for port in range(start, end):
        if is_port_free(port):
            return port
    raise RuntimeError(f"ポート {start}〜{end} が全て使用中です")


def load_existing_env() -> dict:
    """既存の.envを読み込む"""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def generate_env(force: bool = False) -> None:
    """動的設定で .env を生成/更新する"""
    existing = load_existing_env()

    local_ip = get_local_ip()
    backend_port = find_free_port(8000)
    frontend_port = find_free_port(3000)
    postgres_port = find_free_port(5432)
    redis_port = find_free_port(6379)

    # 既存のSECRET_KEYを使い回す（変更しない）
    secret_key = existing.get("SECRET_KEY", "")
    if not secret_key or len(secret_key) < 32:
        secret_key = secrets.token_hex(32)

    new_values = {
        "# == ServiceMatrix 自動生成設定 ==": "",
        "# 生成日時": f"{__import__('datetime').datetime.now().isoformat()}",
        "# プラットフォーム": f"{platform.system()} {platform.release()}",
        "ENVIRONMENT": existing.get("ENVIRONMENT", "production"),
        "LOCAL_IP": local_ip,
        "BIND_HOST": "0.0.0.0",
        "BACKEND_PORT": str(backend_port),
        "FRONTEND_PORT": str(frontend_port),
        "POSTGRES_PORT": str(postgres_port),
        "REDIS_PORT": str(redis_port),
        "SECRET_KEY": secret_key,
        "DATABASE_URL": f"postgresql+asyncpg://servicematrix:changeme@localhost:{postgres_port}/servicematrix",
        "REDIS_URL": f"redis://localhost:{redis_port}/0",
        "ALLOWED_ORIGINS": (
            f'["http://localhost:{frontend_port}",'
            f'"http://{local_ip}:{frontend_port}",'
            f'"http://127.0.0.1:{frontend_port}"]'
        ),
        "BACKEND_URL": f"http://{local_ip}:{backend_port}",
        "FRONTEND_URL": f"http://{local_ip}:{frontend_port}",
        "RATE_LIMIT_PER_MINUTE": existing.get("RATE_LIMIT_PER_MINUTE", "200"),
        "RATE_LIMIT_ENABLED": existing.get("RATE_LIMIT_ENABLED", "true"),
        "SECURITY_HEADERS_ENABLED": existing.get("SECURITY_HEADERS_ENABLED", "true"),
        "POSTGRES_USER": existing.get("POSTGRES_USER", "servicematrix"),
        "POSTGRES_PASSWORD": existing.get("POSTGRES_PASSWORD", secrets.token_urlsafe(16)),
        "POSTGRES_DB": existing.get("POSTGRES_DB", "servicematrix"),
    }

    lines = []
    for key, value in new_values.items():
        if key.startswith("#"):
            lines.append(f"{key}{' ' + value if value else ''}")
        else:
            lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"✅ .env ファイルを生成しました: {ENV_FILE}")
    print(f"   ローカルIP:       {local_ip}")
    print(f"   バックエンドポート: {backend_port}")
    print(f"   フロントエンドポート: {frontend_port}")
    print(f"   PostgreSQLポート:  {postgres_port}")
    print(f"   Redisポート:       {redis_port}")


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    generate_env(force=force)
