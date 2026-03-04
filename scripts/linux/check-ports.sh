#!/usr/bin/env bash
# check-ports.sh — ポート競合確認・代替ポート自動選択
# /opt/servicematrix/scripts/linux/check-ports.sh
# chmod +x required

set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/servicematrix/.env}"
# フォールバック: 開発環境
if [[ ! -f "$ENV_FILE" ]]; then
  ENV_FILE="/mnt/LinuxHDD/ServiceMatrix/.env"
fi

LOG_TAG="servicematrix-check-ports"

log() {
  echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] $*" >&2
}

# ポートが使用中かチェック (ss優先、なければlsof)
port_in_use() {
  local port="$1"
  if command -v ss &>/dev/null; then
    ss -tulpn 2>/dev/null | grep -q ":${port}[[:space:]]"
  elif command -v lsof &>/dev/null; then
    lsof -i ":${port}" &>/dev/null
  else
    # フォールバック: /proc/net/tcp を直接読む
    local hex_port
    hex_port=$(printf '%04X' "$port")
    grep -qi ":[0-9A-F]*:${hex_port} " /proc/net/tcp /proc/net/tcp6 2>/dev/null
  fi
}

# 空きポートを探して返す
find_free_port() {
  local -a candidates=("$@")
  for p in "${candidates[@]}"; do
    if ! port_in_use "$p"; then
      echo "$p"
      return 0
    fi
    log "PORT $p is already in use, trying next..."
  done
  log "ERROR: All candidate ports are in use: ${candidates[*]}"
  return 1
}

# .env からキーを読み込む
env_get() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'"
}

# .env のキーを上書き or 追記
env_set() {
  local key="$1"
  local value="$2"
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "${key}=${value}" > "$ENV_FILE"
    return
  fi
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

# ---- バックエンドポート (8000→8001→8002) ----
BACKEND_PORT=$(env_get "PORT" || true)
BACKEND_PORT="${BACKEND_PORT:-8000}"
FREE_BACKEND=$(find_free_port 8000 8001 8002) || {
  log "FATAL: No free backend port available (tried 8000-8002)"
  exit 1
}
if [[ "$FREE_BACKEND" != "$BACKEND_PORT" ]]; then
  log "Backend port conflict: $BACKEND_PORT → using $FREE_BACKEND"
  env_set "PORT" "$FREE_BACKEND"
fi
log "Backend port: $FREE_BACKEND"

# ---- フロントエンドポート (3000→3001→3002) ----
NODE_PORT=$(env_get "NODE_PORT" || true)
NODE_PORT="${NODE_PORT:-3000}"
FREE_NODE=$(find_free_port 3000 3001 3002) || {
  log "FATAL: No free frontend port available (tried 3000-3002)"
  exit 1
}
if [[ "$FREE_NODE" != "$NODE_PORT" ]]; then
  log "Frontend port conflict: $NODE_PORT → using $FREE_NODE"
  env_set "NODE_PORT" "$FREE_NODE"
fi
log "Frontend port: $FREE_NODE"

# ---- PostgreSQL ポート (5432→5433) ----
PG_PORT=$(env_get "POSTGRES_PORT" || true)
PG_PORT="${PG_PORT:-5432}"
FREE_PG=$(find_free_port 5432 5433) || {
  log "WARNING: No free PostgreSQL port (tried 5432-5433); relying on running instance"
  FREE_PG="$PG_PORT"
}
if [[ "$FREE_PG" != "$PG_PORT" ]]; then
  log "PostgreSQL port conflict: $PG_PORT → using $FREE_PG"
  env_set "POSTGRES_PORT" "$FREE_PG"
fi
log "PostgreSQL port: $FREE_PG"

# ---- Redis ポート (6379→6380) ----
REDIS_PORT=$(env_get "REDIS_PORT" || true)
REDIS_PORT="${REDIS_PORT:-6379}"
FREE_REDIS=$(find_free_port 6379 6380) || {
  log "WARNING: No free Redis port (tried 6379-6380); relying on running instance"
  FREE_REDIS="$REDIS_PORT"
}
if [[ "$FREE_REDIS" != "$REDIS_PORT" ]]; then
  log "Redis port conflict: $REDIS_PORT → using $FREE_REDIS"
  env_set "REDIS_PORT" "$FREE_REDIS"
fi
log "Redis port: $FREE_REDIS"

# ---- BIND_IP を動的に取得 ----
BIND_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
BIND_IP="${BIND_IP:-0.0.0.0}"
env_set "BIND_IP" "$BIND_IP"
log "Bind IP: $BIND_IP"

log "Port check completed. ENV_FILE=$ENV_FILE"
