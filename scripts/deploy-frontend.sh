#!/bin/bash
# フロントエンドビルド＆デプロイスクリプト
# Next.js standalone ビルドに静的ファイルをコピーし、サービスを再起動する

set -e

REPO=/mnt/LinuxHDD/ServiceMatrix
FRONTEND=$REPO/frontend
STANDALONE=$FRONTEND/.next/standalone

echo "=== ServiceMatrix フロントエンド デプロイ ==="

# ビルド
echo "[1/3] npm run build..."
cd "$FRONTEND" && npm run build

# 静的ファイルをstandaloneにコピー
echo "[2/3] 静的ファイルをコピー..."
cp -r "$FRONTEND/.next/static" "$STANDALONE/.next/"
cp -r "$FRONTEND/public/." "$STANDALONE/public/"

# systemd サービス再起動
echo "[3/3] servicematrix-frontend 再起動..."
sudo systemctl restart servicematrix-frontend

sleep 3
sudo systemctl status servicematrix-frontend --no-pager | head -8

echo "=== デプロイ完了 ==="
