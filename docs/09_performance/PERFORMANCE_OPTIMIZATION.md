# パフォーマンス最適化設計書

## 目標値

| メトリクス | 目標値 | CI緩和値 |
|-----------|--------|---------|
| P99レスポンスタイム | 200ms以下 | 500ms以下 |
| エラーレート (5xx) | 0% | 5%未満 |
| 同時ユーザー数 | 100 | 10 |
| スループット | 500 req/s | - |

## 実施した最適化

### 1. DBインデックス

主要クエリに対するインデックスを追加し、フルテーブルスキャンを排除する。

対象テーブル・カラム:

- `incidents`: `status`, `priority`, `created_at`, `assigned_to`
- `changes`: `status`, `change_type`, `scheduled_start`
- `audit_logs`: `entity_type`, `entity_id`, `created_at`
- `cmdb_items`: `item_type`, `status`

```sql
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_priority ON incidents(priority);
CREATE INDEX idx_changes_status ON changes(status);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
```

### 2. 接続プール

SQLAlchemy の非同期接続プール設定を最適化する。

```python
# src/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

### 3. Redisキャッシュ

頻繁にアクセスされる読み取り専用データをキャッシュする。

対象エンドポイント:

- `GET /api/v1/incidents` (TTL: 30秒)
- `GET /api/v1/changes` (TTL: 60秒)
- `GET /api/v1/cmdb/items` (TTL: 120秒)

```python
# キャッシュキー設計
cache_key = f"incidents:list:{page}:{limit}:{status_filter}"
```

## k6 負荷テスト実行方法

### 前提条件

```bash
# k6 インストール (Ubuntu/Debian)
sudo gpg --no-default-keyring \
  --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] \
  https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

### CIスモークテスト（10ユーザー×30秒）

```bash
k6 run tests/load/k6_smoke_test.js
```

### 本番負荷テスト（100ユーザー×10分）

```bash
BASE_URL=http://api.example.com k6 run tests/load/k6_full_test.js
```

### 結果確認

```
✓ http_req_duration............: p(99)=185ms
✓ http_req_failed..............: 0.00%
✓ incidents ok.................: 100%
```

## 計測ダッシュボード設計（Prometheus / Grafana）

### Prometheus メトリクス収集

FastAPI アプリケーションに `prometheus-fastapi-instrumentator` を組み込み、
以下のメトリクスを `/metrics` エンドポイントで公開する。

| メトリクス | 説明 |
|-----------|------|
| `http_request_duration_seconds` | リクエスト処理時間 (histogram) |
| `http_requests_total` | リクエスト総数 (counter) |
| `db_query_duration_seconds` | DBクエリ時間 (histogram) |
| `cache_hit_total` / `cache_miss_total` | キャッシュ命中率 |

### Grafana ダッシュボードパネル構成

```
┌──────────────────────────────────────────────┐
│  ServiceMatrix Performance Dashboard         │
├─────────────────┬────────────────────────────┤
│ P99 Latency     │ Request Rate (req/s)       │
│ [200ms目標]     │ [500 req/s目標]            │
├─────────────────┼────────────────────────────┤
│ Error Rate      │ DB Query P99               │
│ [0%目標]        │ [50ms目標]                 │
├─────────────────┼────────────────────────────┤
│ Cache Hit Rate  │ Active Connections         │
│ [80%以上目標]   │ [pool_size以内]            │
└─────────────────┴────────────────────────────┘
```

### 導入手順（参考）

```bash
# docker-compose.monitoring.yml を使用
docker compose -f docker-compose.monitoring.yml up -d

# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
```

## 改善サイクル

1. k6 スモークテストを CI で定期実行
2. Grafana で P99 レイテンシ推移を監視
3. 閾値超過時は自動アラート (PagerDuty / Slack)
4. ボトルネック特定後、インデックス追加またはキャッシュ拡張で対応
