#!/usr/bin/env bash
# start-frontend.sh — ServiceMatrix フロントエンド起動スクリプト
# /opt/servicematrix/scripts/linux/start-frontend.sh
# chmod +x required

set -euo pipefail

APP_DIR="/opt/servicematrix"
if [[ ! -d "$APP_DIR" ]]; then
  APP_DIR="/mnt/LinuxHDD/ServiceMatrix"
fi

FRONTEND_DIR="${APP_DIR}/frontend"
ENV_FILE="${APP_DIR}/.env"
LOG_TAG="servicematrix-frontend"

log() {
  echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] $*"
}

# .env ロード
if [[ -f "$ENV_FILE" ]]; then
  set -o allexport
  # shellcheck disable=SC1090
  source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE")
  set +o allexport
fi

NODE_PORT="${NODE_PORT:-3000}"
BIND_IP="${BIND_IP:-0.0.0.0}"

log "Starting ServiceMatrix Frontend — IP=$BIND_IP PORT=$NODE_PORT"

if [[ ! -d "$FRONTEND_DIR" ]]; then
  log "ERROR: Frontend directory not found: $FRONTEND_DIR"
  exit 1
fi

cd "$FRONTEND_DIR"

# .next/standalone があれば Node.js サーバ直接起動
if [[ -f ".next/standalone/server.js" ]]; then
  log "Using standalone Next.js server"

  # standalone モードでは static/ と public/ を手動コピーする必要がある
  if [[ ! -d ".next/standalone/.next/static" ]] && [[ -d ".next/static" ]]; then
    log "Copying .next/static -> .next/standalone/.next/static"
    cp -r ".next/static" ".next/standalone/.next/static"
  fi
  if [[ ! -d ".next/standalone/public" ]] && [[ -d "public" ]]; then
    log "Copying public -> .next/standalone/public"
    cp -r "public" ".next/standalone/public"
  fi

  export PORT="$NODE_PORT"
  export HOSTNAME="$BIND_IP"
  exec node .next/standalone/server.js
fi

# npm/npx で next start
NPM_BIN=$(command -v npm 2>/dev/null || true)
if [[ -z "$NPM_BIN" ]]; then
  log "ERROR: npm not found"
  exit 1
fi

log "exec: npm run start -- --port $NODE_PORT --hostname $BIND_IP"
exec "$NPM_BIN" run start -- --port "$NODE_PORT" --hostname "$BIND_IP"
