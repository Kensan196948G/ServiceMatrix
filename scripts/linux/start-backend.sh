#!/usr/bin/env bash
# start-backend.sh — ServiceMatrix バックエンド起動スクリプト
# /opt/servicematrix/scripts/linux/start-backend.sh
# chmod +x required

set -euo pipefail

# インストールパス / 開発環境フォールバック
APP_DIR="/opt/servicematrix"
if [[ ! -d "$APP_DIR" ]]; then
  APP_DIR="/mnt/LinuxHDD/ServiceMatrix"
fi

ENV_FILE="${APP_DIR}/.env"
LOG_TAG="servicematrix-backend"

log() {
  echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] $*"
}

# .env ロード
if [[ -f "$ENV_FILE" ]]; then
  # export しながら読み込む（コメント・空行を除外）
  set -o allexport
  # shellcheck disable=SC1090
  source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE")
  set +o allexport
fi

PORT="${PORT:-8000}"
BIND_IP="${BIND_IP:-0.0.0.0}"

log "Starting ServiceMatrix Backend — IP=$BIND_IP PORT=$PORT"

# Docker が利用可能な場合は docker-compose を優先
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  COMPOSE_FILE="${APP_DIR}/docker-compose.prod.yml"
  if [[ -f "$COMPOSE_FILE" ]]; then
    log "Docker detected. Starting via docker-compose: $COMPOSE_FILE"
    exec docker compose -f "$COMPOSE_FILE" up --remove-orphans
  fi
fi

# ---- 直接起動 (uvicorn) ----
log "Starting uvicorn directly"

VENV="${APP_DIR}/.venv"
if [[ -f "${VENV}/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "${VENV}/bin/activate"
  log "Activated virtualenv: $VENV"
elif command -v poetry &>/dev/null && [[ -f "${APP_DIR}/pyproject.toml" ]]; then
  cd "$APP_DIR"
  exec poetry run uvicorn src.main:app \
    --host "$BIND_IP" \
    --port "$PORT" \
    --workers "${UVICORN_WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}"
fi

# uvicorn をシステム or venv から実行
UVICORN_BIN=$(command -v uvicorn 2>/dev/null || echo "${VENV}/bin/uvicorn")

cd "$APP_DIR"
log "exec: $UVICORN_BIN src.main:app --host $BIND_IP --port $PORT"
exec "$UVICORN_BIN" src.main:app \
  --host "$BIND_IP" \
  --port "$PORT" \
  --workers "${UVICORN_WORKERS:-1}" \
  --log-level "${LOG_LEVEL:-info}"
