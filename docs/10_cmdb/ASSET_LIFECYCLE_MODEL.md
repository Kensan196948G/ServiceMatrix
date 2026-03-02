# 資産ライフサイクルモデル（Asset Lifecycle Model）

ASSET_LIFECYCLE_MODEL.md
Version: 2.0
Category: CMDB
Compliance: ITIL 4 / ISO 20000

---

## 1. 目的

本ドキュメントは、ServiceMatrixが管理するIT資産（CI）の
ライフサイクル全体にわたる管理プロセスを定義する。

計画・調達から廃止・処分まで、すべてのフェーズにおける
管理責任・承認フロー・記録要件を規定する。

---

## 2. ライフサイクル全体像

### 2.1 ライフサイクルフェーズ

```mermaid
graph LR
    A[計画<br>Planning] --> B[調達<br>Procurement]
    B --> C[受入<br>Reception]
    C --> D[構成<br>Configuration]
    D --> E[稼働<br>Operation]
    E --> F[保守<br>Maintenance]
    F --> E
    E --> G[廃止<br>Retirement]
    G --> H[処分<br>Disposal]
```

### 2.2 フェーズ詳細

| フェーズ | CIステータス | 期間目安 | 主要活動 |
|---------|-------------|---------|---------|
| 計画 | Planned | 1〜4週 | 要件定義、見積取得、予算確保 |
| 調達 | Ordered | 1〜8週 | 発注、納期管理 |
| 受入 | Received | 1〜2週 | 検収、資産番号付与、CMDB登録 |
| 構成 | Received → Active | 1〜4週 | セットアップ、テスト、本番展開 |
| 稼働 | Active | 3〜7年 | 運用、監視、SLA管理 |
| 保守 | Maintenance | 随時 | パッチ適用、アップグレード、修理 |
| 廃止 | Retired | 1〜4週 | 移行、データ退避、サービス停止 |
| 処分 | Disposed | 1〜2週 | データ消去、物理廃棄/返却 |

---

## 3. ライフサイクルイベント記録テーブル

### 3.1 PostgreSQL DDL

```sql
-- 資産ライフサイクルイベントテーブル
CREATE TABLE asset_lifecycle_events (
    event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 対象CI
    ci_id               UUID NOT NULL REFERENCES configuration_items(ci_id),

    -- イベント種別
    event_type          VARCHAR(50) NOT NULL,
    CONSTRAINT chk_event_type CHECK (
        event_type IN (
            'planned', 'ordered', 'received', 'configured',
            'activated', 'maintenance_start', 'maintenance_end',
            'retired', 'disposed', 'cancelled',
            'eol_alert', 'replacement_review', 'disposal_reminder'
        )
    ),

    -- ステータス遷移
    from_status         VARCHAR(50),
    to_status           VARCHAR(50),

    -- 実行者
    actor_id            UUID REFERENCES users(user_id),
    actor_type          VARCHAR(20) NOT NULL DEFAULT 'user',
    -- 例: 'user', 'agent', 'system'

    -- 関連記録
    related_change_id   VARCHAR(100),
    related_issue_number INTEGER,
    related_budget_ref  VARCHAR(100),

    -- コスト情報
    cost_amount         DECIMAL(15, 2),
    cost_currency       VARCHAR(3) DEFAULT 'JPY',
    cost_category       VARCHAR(50),
    -- 例: 'initial', 'configuration', 'operation', 'maintenance', 'disposal'

    -- メモ・詳細
    reason              TEXT,
    notes               TEXT,
    evidence_url        TEXT,

    -- 監査
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata            JSONB DEFAULT '{}'::jsonb
);

-- インデックス
CREATE INDEX idx_lifecycle_ci_id ON asset_lifecycle_events (ci_id, timestamp DESC);
CREATE INDEX idx_lifecycle_event_type ON asset_lifecycle_events (event_type, timestamp DESC);
CREATE INDEX idx_lifecycle_timestamp ON asset_lifecycle_events (timestamp DESC);

-- ライフサイクルコスト集計ビュー
CREATE VIEW ci_lifecycle_cost_summary AS
SELECT
    ci_id,
    SUM(CASE WHEN cost_category = 'initial' THEN cost_amount ELSE 0 END) AS initial_cost,
    SUM(CASE WHEN cost_category = 'configuration' THEN cost_amount ELSE 0 END) AS config_cost,
    SUM(CASE WHEN cost_category = 'operation' THEN cost_amount ELSE 0 END) AS operation_cost,
    SUM(CASE WHEN cost_category = 'maintenance' THEN cost_amount ELSE 0 END) AS maintenance_cost,
    SUM(CASE WHEN cost_category = 'disposal' THEN cost_amount ELSE 0 END) AS disposal_cost,
    SUM(cost_amount) AS total_lifecycle_cost,
    MIN(timestamp) AS first_event_at,
    MAX(timestamp) AS last_event_at
FROM asset_lifecycle_events
WHERE cost_amount IS NOT NULL
GROUP BY ci_id;
```

### 3.2 ライフサイクルイベント JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Asset Lifecycle Event",
  "type": "object",
  "required": ["event_id", "ci_id", "event_type", "timestamp", "actor"],
  "properties": {
    "event_id": {
      "type": "string",
      "pattern": "^LCE-[0-9]{4}-[0-9]{6}$",
      "description": "ライフサイクルイベントID"
    },
    "ci_id": {
      "type": "string",
      "description": "対象CI ID"
    },
    "event_type": {
      "type": "string",
      "enum": [
        "planned", "ordered", "received", "configured",
        "activated", "maintenance_start", "maintenance_end",
        "retired", "disposed", "cancelled",
        "eol_alert", "replacement_review", "disposal_reminder"
      ],
      "description": "イベント種別"
    },
    "from_status": {
      "type": "string",
      "description": "遷移前ステータス"
    },
    "to_status": {
      "type": "string",
      "description": "遷移後ステータス"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "イベント日時"
    },
    "actor": {
      "type": "string",
      "description": "実行者（user_id / agent名）"
    },
    "reason": {
      "type": "string",
      "description": "イベント理由"
    },
    "related_issue": {
      "type": "string",
      "description": "関連GitHub Issue番号"
    },
    "related_change": {
      "type": "string",
      "description": "関連変更要求ID"
    },
    "cost": {
      "type": "object",
      "properties": {
        "amount": { "type": "number" },
        "currency": { "type": "string", "default": "JPY" },
        "category": { "type": "string" }
      },
      "description": "関連コスト"
    },
    "notes": {
      "type": "string",
      "description": "備考"
    }
  }
}
```

---

## 4. 各フェーズの詳細

### 4.1 計画フェーズ（Planning）

#### 目的
新規CI導入の必要性を評価し、導入計画を策定する。

#### 活動

| 活動 | 責任者 | 成果物 |
|------|--------|--------|
| 要件定義 | サービスオーナー | 要件定義書 |
| 既存CI評価 | CMDB管理者 | 既存CI活用可能性レポート |
| コスト見積 | 調達担当 | 見積書 |
| 予算承認 | マネージャー | 承認記録 |
| 導入スケジュール | プロジェクトリーダー | スケジュール |
| CMDB事前登録 | CMDB管理者 | CI（ステータス: Planned） |

#### CI登録時の必須情報

```json
{
  "ci_id": "CI-SRV-xxx",
  "ci_type": "Server",
  "name": "（仮称）",
  "status": "Planned",
  "owner": "要件定義者",
  "criticality": "（予定重要度）",
  "environment": "（予定環境）",
  "planned_date": "YYYY-MM-DD",
  "budget_ref": "BUDGET-YYYY-NNN"
}
```

### 4.2 調達フェーズ（Procurement）

#### 活動

| 活動 | 責任者 | 成果物 |
|------|--------|--------|
| 発注 | 調達担当 | 発注書 |
| 納期管理 | 調達担当 | 納期トラッキング |
| ベンダー連絡 | 調達担当 | 連絡記録 |
| CIステータス更新 | CMDB管理者 | CI（ステータス: Ordered） |

### 4.3 受入フェーズ（Reception）

#### 活動

| 活動 | 責任者 | 成果物 |
|------|--------|--------|
| 物理検収 | インフラチーム | 検収記録 |
| スペック確認 | インフラチーム | スペック確認書 |
| 資産番号付与 | CMDB管理者 | 資産台帳更新 |
| CMDB属性更新 | CMDB管理者 | CI属性（実スペック入力） |
| CIステータス更新 | CMDB管理者 | CI（ステータス: Received） |

### 4.4 構成フェーズ（Configuration）

#### 活動

| 活動 | 責任者 | 成果物 |
|------|--------|--------|
| OSインストール | インフラチーム | セットアップ記録 |
| ミドルウェア構成 | アプリチーム/インフラチーム | 構成記録 |
| セキュリティ設定 | セキュリティチーム | セキュリティ設定記録 |
| ネットワーク接続 | ネットワークチーム | 接続確認記録 |
| テスト実施 | テストチーム | テスト結果 |
| CMDB関係性設定 | CMDB管理者 | リレーションシップ登録 |
| 監視設定 | 運用チーム | 監視設定記録 |
| 本番展開承認 | サービスオーナー | 展開承認記録 |
| CIステータス更新 | CMDB管理者 | CI（ステータス: Active） |

### 4.5 稼働フェーズ（Operation）

#### 活動

| 活動 | 頻度 | 責任者 |
|------|------|--------|
| 日常監視 | 継続 | 運用チーム |
| SLA測定 | 月次 | SLA管理者 |
| CI属性確認 | 四半期 | CIオーナー |
| セキュリティスキャン | 月次 | セキュリティチーム |
| 性能評価 | 四半期 | 運用チーム |
| キャパシティ管理 | 月次 | インフラチーム |

#### 稼働中のCI属性自動更新

| 自動更新項目 | 取得元 | 頻度 |
|-------------|--------|------|
| OS パッチレベル | 監視エージェント | 日次 |
| ディスク使用率 | 監視エージェント | 15分 |
| 稼働状態 | ヘルスチェック | 5分 |
| 接続中サービス数 | ロードバランサ | 15分 |

### 4.6 保守フェーズ（Maintenance）

#### 保守の種別

| 種別 | 説明 | 承認 | CIステータス |
|------|------|------|-------------|
| 定期保守 | パッチ適用、バックアップ検証 | 標準変更 | Active のまま |
| 計画保守 | ファームウェア更新、ハード交換 | 通常変更 | Maintenance |
| 緊急保守 | 障害対応、緊急パッチ | 緊急変更 | Maintenance |
| ライフサイクル更新 | メジャーバージョン更新 | 通常変更 | Maintenance |

#### 保守フロー

```mermaid
graph TD
    A[保守要求] --> B{保守種別}
    B -->|定期保守| C[標準変更フロー]
    B -->|計画保守| D[通常変更フロー]
    B -->|緊急保守| E[緊急変更フロー]
    B -->|ライフサイクル更新| D
    C --> F[CI ステータス: Active維持]
    D --> G[CI ステータス: Maintenance]
    E --> G
    F --> H[保守実施]
    G --> H
    H --> I[保守完了確認]
    I --> J[CI属性更新]
    J --> K[CI ステータス: Active復帰]
    K --> L[保守記録の登録]
```

### 4.7 廃止フェーズ（Retirement）

#### 廃止判断基準

| 基準 | 説明 |
|------|------|
| EOL（End of Life） | ベンダーのサポート終了 |
| 技術的陳腐化 | 性能要件を満たせなくなった |
| コスト非効率 | 維持コストが更新コストを上回る |
| リプレース | 後継システムへの移行完了 |
| サービス終了 | 関連サービスが終了した |

#### 廃止フロー

```mermaid
graph TD
    A[廃止判断] --> B[移行計画策定]
    B --> C[依存CI確認]
    C --> D{依存CIあり?}
    D -->|Yes| E[依存CI移行/代替措置]
    D -->|No| F[データ退避]
    E --> F
    F --> G[サービス停止]
    G --> H[CI ステータス: Retired]
    H --> I[廃止記録]
```

### 4.8 処分フェーズ（Disposal）

#### 処分プロセス

| 活動 | 責任者 | 要件 |
|------|--------|------|
| データ消去 | セキュリティチーム | NIST 800-88準拠の消去 |
| 消去証明書取得 | セキュリティチーム | 消去証明書の保管 |
| 物理廃棄/返却 | インフラチーム | 廃棄業者への引渡し記録 |
| CMDB最終更新 | CMDB管理者 | CI ステータス: Disposed |
| 資産台帳更新 | 経理部門 | 除却処理 |

---

## 5. ライフサイクル管理指標

### 5.1 資産管理KPI

| KPI | 計算式 | 目標 |
|-----|--------|------|
| CI情報鮮度 | 最終更新が90日以内のCIの割合 | 95%以上 |
| 未登録CI率 | 検出された未登録CIの割合 | 2%以下 |
| 廃止CI処分率 | Retired後90日以内にDisposedになったCIの割合 | 90%以上 |
| 資産利用率 | Active CI / (Active + Maintenance) CI の割合 | 90%以上 |
| 計画精度 | 計画日±2週以内に稼働開始したCIの割合 | 85%以上 |

### 5.2 ライフサイクルコスト追跡クエリ

```sql
-- CI別のライフサイクル総コスト確認
SELECT
    ci.ci_id,
    ci.name,
    ci.ci_type,
    ci.status,
    lcs.initial_cost,
    lcs.config_cost,
    lcs.operation_cost,
    lcs.maintenance_cost,
    lcs.disposal_cost,
    lcs.total_lifecycle_cost,
    -- 稼働年数
    EXTRACT(YEAR FROM AGE(NOW(), ci.created_at)) AS years_in_service,
    -- 年間平均コスト
    CASE
        WHEN EXTRACT(EPOCH FROM AGE(NOW(), ci.created_at)) > 0
        THEN lcs.total_lifecycle_cost / (EXTRACT(EPOCH FROM AGE(NOW(), ci.created_at)) / 86400 / 365.25)
        ELSE 0
    END AS annual_avg_cost
FROM configuration_items ci
LEFT JOIN ci_lifecycle_cost_summary lcs ON ci.ci_id = lcs.ci_id
WHERE ci.status != 'Disposed'
ORDER BY lcs.total_lifecycle_cost DESC NULLS LAST;

-- EOL警告対象CI一覧（6ヶ月以内にEOLを迎えるCI）
SELECT
    ci.ci_id,
    ci.name,
    ci.ci_type,
    (ci.attributes->>'eol_date')::date AS eol_date,
    (ci.attributes->>'eol_date')::date - CURRENT_DATE AS days_until_eol
FROM configuration_items ci
WHERE
    ci.status = 'Active'
    AND ci.attributes->>'eol_date' IS NOT NULL
    AND (ci.attributes->>'eol_date')::date < CURRENT_DATE + INTERVAL '6 months'
ORDER BY eol_date ASC;
```

---

## 6. 資産タイプ別ライフサイクル特性

### 6.1 ハードウェア資産

| 属性 | 値 |
|------|-----|
| 標準耐用年数 | サーバー: 5年、ネットワーク機器: 7年、ストレージ: 5年 |
| 減価償却 | 定額法 |
| EOL管理 | ベンダーEOLアナウンスから12ヶ月以内にリプレース計画策定 |
| 廃棄要件 | データ消去証明必須、産業廃棄物処理 |

### 6.2 ソフトウェア資産

| 属性 | 値 |
|------|-----|
| ライセンス管理 | ライセンスキー・契約期間・更新日を記録 |
| EOL管理 | ベンダーサポート終了前にアップグレード計画策定 |
| パッチ管理 | セキュリティパッチは30日以内に適用 |
| バージョン管理 | メジャー・マイナーバージョンをCMDBに記録 |

### 6.3 サービス資産

| 属性 | 値 |
|------|-----|
| SLA連携 | サービスCIにSLA定義を紐付け |
| 依存関係管理 | サービスを構成するCI群の依存関係を管理 |
| サービスカタログ | サービスCIの情報をカタログとして公開 |

---

## 7. 自動化トリガールール

### 7.1 ライフサイクル自動化ルール

| トリガー | 自動アクション | 実装方式 |
|----------|--------------|---------|
| CI作成（Planned） | 計画レビューIssue自動作成 | GitHub Actions |
| ステータス→Active | 監視設定の自動適用 | Webhook → Agent |
| ステータス→Maintenance | SLA除外時間の記録開始 | Event Bus |
| ステータス→Active復帰 | SLA除外時間の記録終了 | Event Bus |
| 稼働期間が耐用年数の80%超過 | リプレース検討Issue自動作成 | 夜間バッチ |
| ベンダーEOL日まで6ヶ月 | EOLアラートIssue自動作成 | 夜間バッチ |
| ステータス→Retired | 処分計画Issue自動作成 | GitHub Actions |
| Retired後90日経過 | 処分催促通知 | 夜間バッチ |

### 7.2 バッチ処理クエリ（夜間自動実行）

```sql
-- EOLアラート対象CIの検出（6ヶ月以内）
WITH eol_approaching AS (
    SELECT
        ci_id,
        name,
        (attributes->>'eol_date')::date AS eol_date
    FROM configuration_items
    WHERE
        status = 'Active'
        AND (attributes->>'eol_date')::date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '180 days'
        AND ci_id NOT IN (
            -- 既にeol_alertイベントが直近30日に記録されているCIを除外
            SELECT DISTINCT ci_id
            FROM asset_lifecycle_events
            WHERE event_type = 'eol_alert'
              AND timestamp > NOW() - INTERVAL '30 days'
        )
)
SELECT * FROM eol_approaching ORDER BY eol_date;

-- リプレース検討対象CI（耐用年数80%超過）
WITH replacement_review AS (
    SELECT
        ci.ci_id,
        ci.name,
        ci.ci_type,
        ci.created_at,
        (ci.attributes->>'useful_life_years')::integer AS useful_life_years,
        EXTRACT(EPOCH FROM AGE(NOW(), ci.created_at)) / 86400 / 365.25 AS years_in_service
    FROM configuration_items ci
    WHERE
        ci.status = 'Active'
        AND ci.attributes->>'useful_life_years' IS NOT NULL
)
SELECT
    ci_id,
    name,
    ci_type,
    useful_life_years,
    ROUND(years_in_service::numeric, 2) AS years_in_service,
    ROUND((years_in_service / useful_life_years * 100)::numeric, 1) AS lifecycle_percent
FROM replacement_review
WHERE years_in_service / useful_life_years >= 0.8
ORDER BY lifecycle_percent DESC;
```

---

## 8. 関連ドキュメント

| ドキュメント | 参照先 |
|-------------|--------|
| CMDBデータモデル | `docs/10_cmdb/CMDB_DATA_MODEL.md` |
| CI管理ポリシー | `docs/10_cmdb/CONFIGURATION_ITEM_POLICY.md` |
| リレーションシップモデル | `docs/10_cmdb/RELATIONSHIP_MODEL.md` |
| 影響分析ロジック | `docs/10_cmdb/IMPACT_ANALYSIS_LOGIC.md` |
| データ保持ポリシー | `docs/11_data_model/DATA_RETENTION_POLICY.md` |

---

## 9. 改定履歴

| 版数 | 日付 | 変更内容 | 承認者 |
|------|------|----------|--------|
| 1.0 | 2026-03-02 | 初版作成 | Service Governance Authority |
| 2.0 | 2026-03-02 | PostgreSQL DDL追加、コスト集計ビュー追加、バッチクエリ追加、KPI拡張 | Architecture Committee |

---

*最終更新: 2026-03-02*
*バージョン: 2.0.0*
*承認者: Architecture Committee*
