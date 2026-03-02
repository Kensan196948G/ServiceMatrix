# データベースマイグレーション手順

## マイグレーション一覧

| Revision | 内容 |
|----------|------|
| 001 | 初期スキーマ作成 |
| 002 | incidents.sla_breached_at カラム追加 |
| 003 | incidents.ai_triage_notes カラム追加 |
| 004 | CIRelationship overlaps設定（スキーマ変更なし） |

## 実行方法

```bash
# 最新に適用
alembic upgrade head

# 特定バージョンに適用
alembic upgrade 003

# ロールバック
alembic downgrade -1

# 現在のバージョン確認
alembic current

# マイグレーション履歴確認
alembic history
```
