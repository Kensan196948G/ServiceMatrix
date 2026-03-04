# ServiceMatrix 環境戦略 (Environment Strategy)

Version: 1.0  
Effective: 2024-03

---

## 1. ブランチ=環境マッピング

| ブランチ | 対応環境 | 用途 |
|---------|---------|------|
| `develop` | **開発環境** | 機能開発・統合テスト（デフォルトブランチ） |
| `main` | **本番環境** | リリース・安定版（develop→main PR経由のみ） |
| `feature/**` | ローカル開発 | 各機能ブランチ（develop へ PR） |
| `fix/**` | バグ修正 | develop または main へ PR |

---

## 2. 開発環境 (develop)

### インフラ
- **Backend**: `http://192.168.0.185:8001` (systemd: servicematrix-backend)
- **Frontend**: `http://192.168.0.185:3000` (systemd: servicematrix-frontend)
- **DB**: SQLite (`./servicematrix.db`) または PostgreSQL (ローカル)

### Docker (開発用)
```bash
docker-compose up -d   # docker-compose.yml 使用
# Backend: localhost:8001, Frontend: localhost:3000
```

### デプロイフロー
```
feature/xxx → develop (PR+CI) → 開発環境へ自動反映
```

### CI条件
- Python テスト通過 (カバレッジ ≥ 75%)
- Frontend ビルド成功
- Ruff lint + bandit セキュリティチェック

---

## 3. 本番環境 (main)

### インフラ
- **Nginx リバースプロキシ**: `:80` / `:443`
- **Backend**: FastAPI + Gunicorn (内部 8001)
- **Frontend**: Next.js standalone (内部 3000)
- **DB**: PostgreSQL 15
- **Cache**: Redis 7

### Docker (本番用)
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### デプロイフロー
```
develop → main (PR + レビュー + CI通過) → 本番環境へ手動デプロイ
```

### 本番移行チェックリスト
- [ ] develop での全機能動作確認
- [ ] E2Eテスト通過
- [ ] パフォーマンステスト実施
- [ ] セキュリティスキャン通過
- [ ] ロールバック手順確認
- [ ] DBマイグレーション適用 (`alembic upgrade head`)

---

## 4. ワークフロー

### 機能開発
```bash
git checkout develop
git checkout -b feature/xxx
# 開発・テスト
git push origin feature/xxx
gh pr create --base develop --title "feat: xxx"
# CI通過後 → develop にマージ
```

### 本番リリース
```bash
# develop で十分検証後
gh pr create --base main --head develop --title "release: vX.Y.Z"
# レビュー + CI通過後 → main にマージ
# 本番デプロイ実行
docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d
```

---

## 5. 環境変数

| 変数 | 開発 | 本番 |
|------|------|------|
| `DATABASE_URL` | sqlite:///./servicematrix.db | postgresql+asyncpg://... |
| `SECRET_KEY` | dev-secret-key | ランダム64文字 |
| `ENVIRONMENT` | development | production |
| `POSTGRES_HOST` | (未設定) | postgres |
| `REDIS_URL` | (未設定) | redis://redis:6379 |

---

## 6. 本番移行タイミング

以下の条件を満たした時点で develop→main PR を提出する:

1. ✅ バックエンド全APIエンドポイント実装済み
2. ✅ フロントエンド全25ページ動作確認
3. ✅ テストカバレッジ 80% 以上
4. ✅ WebSocket/リアルタイム通知動作確認
5. ✅ CMDB・SLA機能動作確認
6. ⬜ 担当者管理・通知永続化
7. ⬜ 本番用PostgreSQLマイグレーション確認
