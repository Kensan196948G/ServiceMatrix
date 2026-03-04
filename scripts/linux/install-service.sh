#!/usr/bin/env bash
# install-service.sh — ServiceMatrix systemd サービス インストールスクリプト
# /mnt/LinuxHDD/ServiceMatrix/scripts/linux/install-service.sh
# chmod +x required
# Usage: sudo bash install-service.sh [--docker-only]

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_DIR="/opt/servicematrix"
SERVICE_USER="servicematrix"
SYSTEMD_DIR="/etc/systemd/system"
LOG_TAG="servicematrix-install"

DOCKER_ONLY=false
for arg in "$@"; do
  [[ "$arg" == "--docker-only" ]] && DOCKER_ONLY=true
done

log()  { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] INFO  $*"; }
warn() { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] WARN  $*" >&2; }
die()  { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] ERROR $*" >&2; exit 1; }

# ---- root 確認 ----
[[ $EUID -eq 0 ]] || die "このスクリプトは root 権限で実行してください: sudo $0"

log "=== ServiceMatrix インストール開始 ==="
log "REPO_DIR=$REPO_DIR  INSTALL_DIR=$INSTALL_DIR"

# ---- 依存ツール確認 ----
check_cmd() {
  local cmd="$1"; local pkg="${2:-$1}"
  if command -v "$cmd" &>/dev/null; then
    log "  ✔ $cmd: $(command -v "$cmd")"
  else
    warn "  ✘ $cmd が見つかりません (パッケージ: $pkg)"
  fi
}

log "--- 依存ツールチェック ---"
check_cmd python3 python3
check_cmd pip3 python3-pip
check_cmd node nodejs
check_cmd npm npm
check_cmd docker docker.io
check_cmd docker-compose "docker-compose (or docker compose plugin)"

HAS_DOCKER=false
if command -v docker &>/dev/null; then
  HAS_DOCKER=true
  log "  Docker version: $(docker --version 2>/dev/null)"
fi

# ---- servicematrix ユーザー作成 ----
log "--- ユーザー確認 ---"
if id "$SERVICE_USER" &>/dev/null; then
  log "ユーザー '$SERVICE_USER' は既に存在します"
else
  useradd --system --no-create-home --shell /usr/sbin/nologin \
    --comment "ServiceMatrix service account" "$SERVICE_USER"
  log "ユーザー '$SERVICE_USER' を作成しました"
fi

# Docker グループに追加
if $HAS_DOCKER && getent group docker &>/dev/null; then
  usermod -aG docker "$SERVICE_USER" 2>/dev/null || true
  log "ユーザー '$SERVICE_USER' を docker グループに追加しました"
fi

# ---- /opt/servicematrix セットアップ ----
log "--- インストール先セットアップ ---"
if [[ -L "$INSTALL_DIR" ]]; then
  log "$INSTALL_DIR はすでにシンボリックリンクです ($(readlink -f "$INSTALL_DIR"))"
elif [[ -d "$INSTALL_DIR" ]]; then
  warn "$INSTALL_DIR はすでに存在するディレクトリです。スキップします"
else
  ln -s "$REPO_DIR" "$INSTALL_DIR"
  log "シンボリックリンクを作成: $INSTALL_DIR -> $REPO_DIR"
fi

chown -h "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" 2>/dev/null || true

# ---- .env ファイル確認 ----
log "--- .env 確認 ---"
if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
  if [[ -f "${INSTALL_DIR}/.env.example" ]]; then
    cp "${INSTALL_DIR}/.env.example" "${INSTALL_DIR}/.env"
    warn ".env.example をコピーしました。${INSTALL_DIR}/.env を編集して秘密情報を設定してください"
  else
    cat > "${INSTALL_DIR}/.env" <<'EOF'
# ServiceMatrix 環境変数
PORT=8000
NODE_PORT=3000
POSTGRES_PORT=5432
REDIS_PORT=6379
BIND_IP=0.0.0.0
LOG_LEVEL=info
UVICORN_WORKERS=2
EOF
    warn ".env を新規作成しました。${INSTALL_DIR}/.env を編集してください"
  fi
fi
chown "$SERVICE_USER:$SERVICE_USER" "${INSTALL_DIR}/.env"
chmod 640 "${INSTALL_DIR}/.env"

# ---- スクリプトに実行権限付与 ----
log "--- スクリプト権限設定 ---"
chmod +x "${INSTALL_DIR}/scripts/linux/"*.sh
log "scripts/linux/*.sh に +x を設定しました"

# ---- Python 仮想環境構築 ----
if ! $DOCKER_ONLY; then
  log "--- Python 仮想環境構築 ---"
  if command -v poetry &>/dev/null && [[ -f "${INSTALL_DIR}/pyproject.toml" ]]; then
    log "poetry でパッケージをインストールします"
    cd "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" poetry install --no-interaction --no-ansi 2>&1 | tail -5
  elif command -v python3 &>/dev/null; then
    VENV="${INSTALL_DIR}/.venv"
    if [[ ! -d "$VENV" ]]; then
      python3 -m venv "$VENV"
      log "仮想環境を作成: $VENV"
    fi
    if [[ -f "${INSTALL_DIR}/requirements.txt" ]]; then
      "${VENV}/bin/pip" install -q -r "${INSTALL_DIR}/requirements.txt"
      log "requirements.txt からパッケージをインストールしました"
    fi
    chown -R "$SERVICE_USER:$SERVICE_USER" "$VENV"
  else
    warn "python3 が見つからないため仮想環境をスキップします"
  fi
fi

# ---- frontend ビルド確認 ----
if ! $DOCKER_ONLY; then
  log "--- Frontend ビルド確認 ---"
  FRONTEND_DIR="${INSTALL_DIR}/frontend"
  if [[ -d "$FRONTEND_DIR" ]] && command -v npm &>/dev/null; then
    if [[ ! -d "${FRONTEND_DIR}/.next" ]]; then
      log "frontend をビルドします (npm run build)"
      cd "$FRONTEND_DIR"
      sudo -u "$SERVICE_USER" npm ci --quiet 2>&1 | tail -3
      sudo -u "$SERVICE_USER" npm run build 2>&1 | tail -5
    else
      log "frontend .next ディレクトリが存在します。ビルドをスキップします"
    fi
  fi
fi

# ---- systemd サービスファイルのコピー・有効化 ----
log "--- systemd サービスインストール ---"

install_service() {
  local name="$1"
  local src="${INSTALL_DIR}/systemd/${name}.service"
  local dst="${SYSTEMD_DIR}/${name}.service"
  if [[ ! -f "$src" ]]; then
    warn "サービスファイルが見つかりません: $src"
    return
  fi
  cp "$src" "$dst"
  chmod 644 "$dst"
  log "コピー: $src -> $dst"
}

if $DOCKER_ONLY || $HAS_DOCKER; then
  install_service "servicematrix-docker"
  systemctl daemon-reload
  systemctl enable servicematrix-docker
  log "servicematrix-docker を有効化しました"
fi

if ! $DOCKER_ONLY; then
  install_service "servicematrix-backend"
  install_service "servicematrix-frontend"
  systemctl daemon-reload
  systemctl enable servicematrix-backend servicematrix-frontend
  log "servicematrix-backend / servicematrix-frontend を有効化しました"
fi

# ---- ファイアウォール設定 (ufw) ----
log "--- ファイアウォール設定 ---"
if command -v ufw &>/dev/null; then
  ufw allow 8000/tcp comment "ServiceMatrix Backend"  2>/dev/null || true
  ufw allow 8001/tcp comment "ServiceMatrix Backend (alt1)" 2>/dev/null || true
  ufw allow 3000/tcp comment "ServiceMatrix Frontend" 2>/dev/null || true
  ufw allow 3001/tcp comment "ServiceMatrix Frontend (alt1)" 2>/dev/null || true
  log "ufw ルールを追加しました (8000,8001,3000,3001)"
else
  warn "ufw が見つかりません。ファイアウォールの設定を手動で行ってください"
fi

log "=== インストール完了 ==="
log ""
log "次のコマンドでサービスを開始できます:"
if $DOCKER_ONLY || $HAS_DOCKER; then
  log "  sudo systemctl start servicematrix-docker"
fi
if ! $DOCKER_ONLY; then
  log "  sudo systemctl start servicematrix-backend servicematrix-frontend"
fi
log ""
log "ログ確認:"
log "  journalctl -u servicematrix-backend -f"
log "  journalctl -u servicematrix-frontend -f"
