#!/usr/bin/env bash
# uninstall-service.sh — ServiceMatrix systemd サービス アンインストールスクリプト
# /mnt/LinuxHDD/ServiceMatrix/scripts/linux/uninstall-service.sh
# chmod +x required
# Usage: sudo bash uninstall-service.sh [--purge]

set -euo pipefail

INSTALL_DIR="/opt/servicematrix"
SYSTEMD_DIR="/etc/systemd/system"
LOG_TAG="servicematrix-uninstall"

PURGE=false
for arg in "$@"; do
  [[ "$arg" == "--purge" ]] && PURGE=true
done

log()  { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] INFO  $*"; }
warn() { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] WARN  $*" >&2; }
die()  { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [$LOG_TAG] ERROR $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "このスクリプトは root 権限で実行してください: sudo $0"

log "=== ServiceMatrix アンインストール開始 ==="

SERVICES=(
  "servicematrix-backend"
  "servicematrix-frontend"
  "servicematrix-docker"
)

# ---- サービスの停止・無効化 ----
log "--- サービス停止・無効化 ---"
for svc in "${SERVICES[@]}"; do
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    log "停止: $svc"
    systemctl stop "$svc" 2>/dev/null || warn "$svc の停止に失敗しました"
  fi
  if systemctl is-enabled --quiet "$svc" 2>/dev/null; then
    log "無効化: $svc"
    systemctl disable "$svc" 2>/dev/null || warn "$svc の無効化に失敗しました"
  fi
done

# ---- サービスファイルの削除 ----
log "--- サービスファイル削除 ---"
for svc in "${SERVICES[@]}"; do
  SERVICE_FILE="${SYSTEMD_DIR}/${svc}.service"
  if [[ -f "$SERVICE_FILE" ]]; then
    rm -f "$SERVICE_FILE"
    log "削除: $SERVICE_FILE"
  fi
done

systemctl daemon-reload
log "systemctl daemon-reload 完了"

# ---- ファイアウォールルール削除 ----
log "--- ファイアウォールルール削除 ---"
if command -v ufw &>/dev/null; then
  ufw delete allow 8000/tcp 2>/dev/null || true
  ufw delete allow 8001/tcp 2>/dev/null || true
  ufw delete allow 3000/tcp 2>/dev/null || true
  ufw delete allow 3001/tcp 2>/dev/null || true
  log "ufw ルールを削除しました"
fi

# ---- --purge オプション: シンボリックリンク・ユーザー削除 ----
if $PURGE; then
  log "--- [--purge] シンボリックリンク・ユーザー削除 ---"

  if [[ -L "$INSTALL_DIR" ]]; then
    rm -f "$INSTALL_DIR"
    log "シンボリックリンク削除: $INSTALL_DIR"
  elif [[ -d "$INSTALL_DIR" ]]; then
    warn "$INSTALL_DIR はシンボリックリンクではなく実ディレクトリです。手動で削除してください"
  fi

  if id "servicematrix" &>/dev/null; then
    userdel "servicematrix" 2>/dev/null || warn "ユーザー servicematrix の削除に失敗しました"
    log "ユーザー servicematrix を削除しました"
  fi
fi

log "=== アンインストール完了 ==="
if ! $PURGE; then
  log "ソースコードは削除されていません。完全削除は --purge オプションを使用してください"
  log "  sudo $0 --purge"
fi
