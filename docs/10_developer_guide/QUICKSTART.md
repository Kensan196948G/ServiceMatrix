# ServiceMatrix クイックスタートガイド

## 前提条件

- Docker Desktop / Docker Engine + Docker Compose
- Python 3.12+
- Node.js 24+

## 5分セットアップ

### 方法1: Makefile（推奨）

```bash
git clone https://github.com/Kensan196948G/ServiceMatrix.git
cd ServiceMatrix
make setup
make dev
```

ブラウザで http://localhost:3000 を開く。

### 方法2: GitHub Codespaces

1. GitHubリポジトリページで **Code → Codespaces → New codespace**
2. 自動セットアップが完了するまで待つ（3〜5分）
3. ポート転送が自動で設定される

### 方法3: Dev Containers (VS Code)

1. VS Code に Dev Containers 拡張をインストール
2. リポジトリをクローン後 VS Code で開く
3. `Reopen in Container` を選択
4. 自動セットアップが完了するまで待つ

## コマンド一覧

```bash
make help        # ヘルプ表示
make setup       # 環境セットアップ
make seed        # サンプルデータ投入
make dev         # 開発サーバー起動
make test        # テスト実行
make lint        # Lint
make format      # フォーマット
make clean       # クリーンアップ
```

## 環境変数

`.env.example` をコピーして `.env` を作成:

```bash
cp .env.example .env
```

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `DATABASE_URL` | PostgreSQL接続URL | sqlite+aiosqlite:///./dev.db |
| `REDIS_URL` | Redis接続URL | redis://localhost:6379 |
| `SECRET_KEY` | JWT署名キー | dev-only-key |
| `ALLOWED_ORIGINS` | CORS許可Origin | http://localhost:3000 |
