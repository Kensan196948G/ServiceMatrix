#!/bin/bash
# OpenAPI TypeScript SDK 生成スクリプト
# 使用方法: ./scripts/generate_sdk.sh [--check]

set -e

OPENAPI_URL="${OPENAPI_URL:-http://localhost:8000/openapi.json}"
SDK_OUTPUT_DIR="sdk/typescript"
SCHEMA_FILE="sdk/openapi.json"

echo "📐 OpenAPI スキーマ取得中..."
mkdir -p sdk
curl -sf "$OPENAPI_URL" -o "$SCHEMA_FILE" || {
    echo "⚠️  バックエンド未起動。スキーマファイルが存在する場合はそれを使用します"
    if [ ! -f "$SCHEMA_FILE" ]; then
        echo "❌ スキーマファイルが見つかりません: $SCHEMA_FILE"
        exit 1
    fi
}

echo "🔧 TypeScript SDK 生成中..."
mkdir -p "$SDK_OUTPUT_DIR"
npx --yes openapi-typescript "$SCHEMA_FILE" -o "$SDK_OUTPUT_DIR/schema.d.ts"

echo "✅ SDK 生成完了: $SDK_OUTPUT_DIR/schema.d.ts"

if [ "$1" = "--check" ]; then
    echo "🔍 変更チェックモード"
    if git diff --quiet "$SDK_OUTPUT_DIR/schema.d.ts" 2>/dev/null; then
        echo "✅ SDK は最新です（変更なし）"
    else
        echo "⚠️  SDK の更新が必要です（openapi スキーマが変更されました）"
        git diff "$SDK_OUTPUT_DIR/schema.d.ts"
    fi
fi
