# SQLite to PostgreSQL Migration Guide

ServiceMatrixデータベースをSQLiteからPostgreSQL 16へ移行する手順書。

---

## 前提条件

- Docker / Docker Compose が利用可能
- Python 3.12+ と仮想環境がセットアップ済み
- `pip install -e ".[dev]"` で依存パッケージがインストール済み

## 1. 環境変数の設定

### 方法A: DATABASE_URL を直接指定

```bash
export DATABASE_URL="postgresql+asyncpg://servicematrix:your_password@localhost:5432/servicematrix"
```

### 方法B: 個別の環境変数を指定

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=servicematrix
export POSTGRES_USER=servicematrix
export POSTGRES_PASSWORD=your_password
```

> `DATABASE_URL` がpostgresqlで始まる場合、個別変数より優先されます。
> どちらも未設定の場合、SQLiteがデフォルトで使用されます。

### 方法C: .env ファイルを使用

プロジェクトルートに `.env` ファイルを作成:

```
DATABASE_URL=postgresql+asyncpg://servicematrix:your_password@localhost:5432/servicematrix
```

## 2. Docker Compose によるPostgreSQL起動

```bash
# PostgreSQLとRedisを起動
docker compose up -d db redis

# ヘルスチェック確認
docker compose ps
```

## 3. Alembicマイグレーション実行

```bash
# マイグレーション実行
alembic upgrade head

# または Docker Compose のmigrateサービスを利用
docker compose --profile tools run --rm migrate
```

### マイグレーション状態の確認

```bash
# 現在のリビジョン確認
alembic current

# 履歴確認
alembic history
```

## 4. アプリケーション起動

```bash
# ローカル起動
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Docker Compose で全スタック起動
docker compose up -d
```

## 5. マイグレーションの構成

| リビジョン | 内容 |
|-----------|------|
| 001 | 初期スキーマ（全テーブル・月次パーティション・シーケンス） |
| 002 | パフォーマンスインデックス追加（problems, changes, service_requests, CMDB, audit_logs） |

## トラブルシューティング

### PostgreSQLに接続できない

```bash
# コンテナの状態を確認
docker compose logs db

# 手動接続テスト
psql -h localhost -U servicematrix -d servicematrix
```

### マイグレーションが失敗する

```bash
# 現在の状態を確認
alembic current

# 一つ前に戻す
alembic downgrade -1

# やり直し
alembic upgrade head
```

### SQLiteに戻す場合

環境変数を削除またはunsetすれば、自動的にSQLiteがデフォルトとして使用されます:

```bash
unset DATABASE_URL
unset POSTGRES_HOST
```

> **注意**: SQLiteではパーティション・シーケンスなどのPostgreSQL固有機能は利用できません。テスト環境向けの簡易モードとなります。
