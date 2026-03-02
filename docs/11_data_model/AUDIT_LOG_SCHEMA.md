# 監査ログスキーマ定義

AUDIT_LOG_SCHEMA.md
Version: 2.0
Category: Data Model
Compliance: J-SOX / ISO 20000 / ITIL 4

---

## 1. 目的

本ドキュメントは、ServiceMatrixにおける監査ログのデータスキーマを定義する。
すべてのユーザー操作・AI決定・システムイベントを改ざん不能な形式で記録し、
J-SOX内部統制・ISO 20000監査要件を満たすことを目的とする。

**v2.0 強化内容:**

- `audit_logs` パーティション自動生成ストアド関数追加
- `ai_audit_logs` バイアス検知・モデルドリフト監視フィールド追加
- メルクルツリー検証 PostgreSQL 実装追加
- 監視・アラートクエリ追加（異常検知・ゼロトラスト検証）
- アクション定義の大幅拡充（問題管理・CMDB・SLA カテゴリ追加）
- 自動パーティション管理ストアド関数追加

---

## 2. 監査ログテーブル定義

### 2.1 メイン監査ログテーブル（audit_logs）

```sql
-- 監査ログテーブル（月次パーティション）
CREATE TABLE audit_logs (
    -- 主キー
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- タイムスタンプ（UTC・ナノ秒精度）
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- アクター情報
    user_id         UUID REFERENCES users(user_id),
    user_name       VARCHAR(255),
    user_role       VARCHAR(100),
    CONSTRAINT chk_audit_user_role CHECK (
        user_role IN (
            'SystemAdmin', 'ServiceManager', 'ProcessOwner',
            'ChangeManager', 'Operator', 'Auditor', 'Viewer', 'Agent'
        ) OR user_role IS NULL
    ),
    session_id      UUID,
    ip_address      INET,
    user_agent      TEXT,

    -- 操作情報
    action          VARCHAR(100) NOT NULL,
    -- 例: 'incident.create', 'change.approve', 'user.login', 'ai.decision'
    resource_type   VARCHAR(100) NOT NULL,
    CONSTRAINT chk_audit_resource_type CHECK (
        resource_type IN (
            'incident', 'change_request', 'problem', 'service_request',
            'release', 'user', 'team', 'configuration_item', 'sla',
            'audit_log', 'system', 'security'
        )
    ),
    resource_id     UUID,

    -- 変更内容
    old_value       JSONB,
    new_value       JSONB,
    diff_summary    TEXT,

    -- 操作結果
    result          VARCHAR(50) NOT NULL,
    CONSTRAINT chk_audit_result CHECK (
        result IN ('success', 'failure', 'denied', 'partial', 'timeout')
    ),
    error_code      VARCHAR(50),
    error_message   TEXT,

    -- リクエスト情報
    request_id      UUID,
    api_endpoint    VARCHAR(500),
    http_method     VARCHAR(10),
    CONSTRAINT chk_audit_http_method CHECK (
        http_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')
        OR http_method IS NULL
    ),
    http_status     INTEGER,

    -- 整合性チェーン（改ざん防止）
    prev_log_hash   VARCHAR(64),  -- 前レコードのSHA-256ハッシュ
    current_hash    VARCHAR(64) NOT NULL,  -- 自レコードのSHA-256ハッシュ

    -- メタデータ
    metadata        JSONB DEFAULT '{}'::jsonb,
    tags            TEXT[] DEFAULT ARRAY[]::TEXT[]
)
PARTITION BY RANGE (timestamp);

-- インデックス定義
CREATE INDEX idx_audit_logs_timestamp ON audit_logs (timestamp DESC);
CREATE INDEX idx_audit_logs_user_id ON audit_logs (user_id, timestamp DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs (resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs (action, timestamp DESC);
CREATE INDEX idx_audit_logs_result ON audit_logs (result, timestamp DESC);
CREATE INDEX idx_audit_logs_ip ON audit_logs (ip_address, timestamp DESC);
CREATE INDEX idx_audit_logs_metadata_gin ON audit_logs USING GIN (metadata);

-- 月次パーティション作成例（2026年）
CREATE TABLE audit_logs_2026_03 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE audit_logs_2026_06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
```

### 2.2 AI操作専用ログテーブル（ai_audit_logs）

```sql
-- AI操作監査ログテーブル
CREATE TABLE ai_audit_logs (
    -- 主キー（audit_logsと連携）
    ai_log_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_id              UUID REFERENCES audit_logs(log_id),

    -- AIエージェント情報
    agent_id            VARCHAR(255) NOT NULL,
    agent_type          VARCHAR(100) NOT NULL,
    -- 例: 'foundation-governance', 'security-reviewer', 'claude-lead'
    agent_version       VARCHAR(50),
    model_name          VARCHAR(100),
    model_version       VARCHAR(50),  -- 例: 'claude-opus-4-6', 'claude-sonnet-4-6'

    -- 入力コンテキスト
    input_context       JSONB NOT NULL,
    input_tokens        INTEGER,
    prompt_hash         VARCHAR(64),  -- プロンプトの一方向ハッシュ（プライバシー保護）
    context_window_used INTEGER,      -- 使用コンテキストウィンドウサイズ

    -- AI決定内容
    decision_type       VARCHAR(100) NOT NULL,
    -- 例: 'priority_assessment', 'risk_evaluation', 'repair_proposal', 'impact_analysis'
    decision            JSONB NOT NULL,
    confidence_score    DECIMAL(5, 4),  -- 0.0000 - 1.0000
    rationale           TEXT,
    alternatives        JSONB,          -- 検討した代替案（説明可能AI対応）

    -- 出力情報
    output_tokens       INTEGER,
    response_time_ms    INTEGER,
    cost_usd            DECIMAL(10, 6), -- API呼び出しコスト（USD）

    -- 自律度レベル
    autonomy_level      SMALLINT NOT NULL,
    -- L0: 人間判断のみ / L1: 推奨のみ / L2: 低リスク自動 / L3: 自動実行+報告
    CONSTRAINT chk_ai_autonomy_level CHECK (autonomy_level BETWEEN 0 AND 3),

    -- 人間承認情報（L0/L1のみ）
    requires_human_approval BOOLEAN NOT NULL DEFAULT TRUE,
    human_approved      BOOLEAN,
    approver_user_id    UUID REFERENCES users(user_id),
    approval_timestamp  TIMESTAMPTZ,
    approval_comment    TEXT,

    -- バイアス・ドリフト検知（v2.0追加）
    bias_flags          TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- 例: ['gender_bias', 'recency_bias', 'anchoring_bias']
    drift_score         DECIMAL(5, 4),   -- モデルドリフトスコア（0.0-1.0、高いほど逸脱）
    fairness_metrics    JSONB,           -- 公平性指標（グループ別誤差等）

    -- 実行結果
    was_executed        BOOLEAN,
    execution_outcome   VARCHAR(100),
    -- 例: 'accepted', 'rejected', 'modified', 'auto_executed', 'escalated'
    CONSTRAINT chk_ai_execution_outcome CHECK (
        execution_outcome IN (
            'accepted', 'rejected', 'modified', 'auto_executed', 'escalated', 'expired'
        ) OR execution_outcome IS NULL
    ),

    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
PARTITION BY RANGE (timestamp);

CREATE INDEX idx_ai_audit_logs_agent ON ai_audit_logs (agent_type, timestamp DESC);
CREATE INDEX idx_ai_audit_logs_decision ON ai_audit_logs (decision_type, timestamp DESC);
CREATE INDEX idx_ai_audit_logs_autonomy ON ai_audit_logs (autonomy_level, timestamp DESC);
CREATE INDEX idx_ai_audit_logs_confidence ON ai_audit_logs (confidence_score, timestamp DESC);
CREATE INDEX idx_ai_audit_logs_drift ON ai_audit_logs (drift_score DESC) WHERE drift_score IS NOT NULL;

-- AI監査ログ月次パーティション
CREATE TABLE ai_audit_logs_2026_03 PARTITION OF ai_audit_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE ai_audit_logs_2026_04 PARTITION OF ai_audit_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

### 2.3 ハッシュチェーン管理テーブル（audit_log_integrity）

```sql
-- 監査ログ整合性管理テーブル
CREATE TABLE audit_log_integrity (
    check_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    log_count       BIGINT NOT NULL,
    root_hash       VARCHAR(64) NOT NULL,  -- メルクルツリールートハッシュ
    chain_valid     BOOLEAN NOT NULL,
    broken_at_log   UUID,    -- チェーン破損箇所（NULLなら正常）
    broken_count    INTEGER DEFAULT 0,    -- 破損レコード数
    verified_by     UUID REFERENCES users(user_id),
    verification_method VARCHAR(50) DEFAULT 'sha256_chain',
    -- 例: 'sha256_chain', 'merkle_tree', 'external_notary'
    notes           TEXT
);

CREATE INDEX idx_integrity_period ON audit_log_integrity (period_start, period_end);
CREATE INDEX idx_integrity_valid ON audit_log_integrity (chain_valid, checked_at DESC);
```

---

## 3. パーティション自動管理（v2.0追加）

### 3.1 パーティション自動生成ストアド関数

```sql
-- 監査ログ月次パーティション自動作成
CREATE OR REPLACE FUNCTION create_audit_log_partitions(
    target_months_ahead INTEGER DEFAULT 3
)
RETURNS INTEGER AS $$
DECLARE
    partition_date  DATE;
    partition_name  TEXT;
    start_date      TEXT;
    end_date        TEXT;
    created_count   INTEGER := 0;
BEGIN
    FOR i IN 0..target_months_ahead LOOP
        partition_date := DATE_TRUNC('month', NOW()) + (i || ' months')::INTERVAL;
        partition_name := 'audit_logs_' || TO_CHAR(partition_date, 'YYYY_MM');
        start_date     := TO_CHAR(partition_date, 'YYYY-MM-DD');
        end_date       := TO_CHAR(partition_date + INTERVAL '1 month', 'YYYY-MM-DD');

        -- パーティションが未作成の場合のみ作成
        IF NOT EXISTS (
            SELECT 1 FROM pg_class
            WHERE relname = partition_name
        ) THEN
            EXECUTE FORMAT(
                'CREATE TABLE %I PARTITION OF audit_logs
                 FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );

            -- パーティション固有インデックス（ローカルインデックス）
            EXECUTE FORMAT(
                'CREATE INDEX %I ON %I (timestamp DESC)',
                'idx_' || partition_name || '_ts', partition_name
            );

            created_count := created_count + 1;
        END IF;
    END LOOP;

    RETURN created_count;
END;
$$ LANGUAGE plpgsql;

-- AI監査ログ用パーティション自動作成
CREATE OR REPLACE FUNCTION create_ai_audit_log_partitions(
    target_months_ahead INTEGER DEFAULT 3
)
RETURNS INTEGER AS $$
DECLARE
    partition_date  DATE;
    partition_name  TEXT;
    start_date      TEXT;
    end_date        TEXT;
    created_count   INTEGER := 0;
BEGIN
    FOR i IN 0..target_months_ahead LOOP
        partition_date := DATE_TRUNC('month', NOW()) + (i || ' months')::INTERVAL;
        partition_name := 'ai_audit_logs_' || TO_CHAR(partition_date, 'YYYY_MM');
        start_date     := TO_CHAR(partition_date, 'YYYY-MM-DD');
        end_date       := TO_CHAR(partition_date + INTERVAL '1 month', 'YYYY-MM-DD');

        IF NOT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = partition_name
        ) THEN
            EXECUTE FORMAT(
                'CREATE TABLE %I PARTITION OF ai_audit_logs
                 FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            created_count := created_count + 1;
        END IF;
    END LOOP;

    RETURN created_count;
END;
$$ LANGUAGE plpgsql;

-- 定期実行推奨（月次 cron / pg_cron）
-- SELECT cron.schedule('create-audit-partitions', '0 0 1 * *',
--     'SELECT create_audit_log_partitions(3); SELECT create_ai_audit_log_partitions(3);');
```

### 3.2 古いパーティションのアーカイブ移行クエリ

```sql
-- アーカイブ対象パーティションの特定（1年以上前）
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'audit_logs_____\__'
  AND TO_DATE(
        SUBSTRING(tablename FROM 'audit_logs_(\d{4}_\d{2})'),
        'YYYY_MM'
      ) < DATE_TRUNC('month', NOW() - INTERVAL '1 year')
ORDER BY tablename;

-- アーカイブフラグ付与（バッチ処理前の対象確認）
SELECT COUNT(*) AS archive_target_count
FROM audit_logs
WHERE timestamp < NOW() - INTERVAL '1 year'
  AND (metadata->>'archived_at') IS NULL;
```

---

## 4. アクション定義一覧

### 4.1 インシデント管理

| アクション名 | 説明 |
|------------|------|
| `incident.create` | インシデント作成 |
| `incident.update` | インシデント更新 |
| `incident.acknowledge` | インシデント受付 |
| `incident.escalate` | エスカレーション |
| `incident.reassign` | 担当者変更 |
| `incident.workaround_applied` | 暫定対処適用 |
| `incident.resolve` | インシデント解決 |
| `incident.close` | インシデントクローズ |
| `incident.reopen` | インシデント再オープン |
| `incident.sla_breach` | SLA 違反発生（システム記録） |

### 4.2 変更管理

| アクション名 | 説明 |
|------------|------|
| `change.create` | 変更リクエスト作成 |
| `change.submit` | 変更申請提出 |
| `change.cab_review` | CAB レビュー |
| `change.approve` | 変更承認 |
| `change.reject` | 変更拒否 |
| `change.schedule` | 変更スケジュール設定 |
| `change.deploy` | 変更デプロイ実行 |
| `change.rollback` | ロールバック実行 |
| `change.close` | 変更クローズ |
| `change.emergency_approve` | 緊急変更承認 |

### 4.3 問題管理

| アクション名 | 説明 |
|------------|------|
| `problem.create` | 問題記録作成 |
| `problem.update` | 問題記録更新 |
| `problem.link_incident` | インシデント関連付け |
| `problem.rca_updated` | 根本原因分析更新 |
| `problem.workaround_published` | 既知のエラー公開 |
| `problem.resolve` | 問題解決 |
| `problem.close` | 問題クローズ |

### 4.4 CMDB・資産管理

| アクション名 | 説明 |
|------------|------|
| `ci.create` | CI 登録 |
| `ci.update` | CI 更新 |
| `ci.retire` | CI 廃止 |
| `ci.relationship_add` | CI 関係追加 |
| `ci.relationship_remove` | CI 関係削除 |
| `ci.lifecycle_change` | ライフサイクル変更 |

### 4.5 SLA 管理

| アクション名 | 説明 |
|------------|------|
| `sla.breach_detected` | SLA 違反検知 |
| `sla.warning_triggered` | SLA 警告発報 |
| `sla.measurement_recorded` | SLA 計測記録 |
| `sla.report_generated` | SLA レポート生成 |

### 4.6 ユーザー・認証

| アクション名 | 説明 |
|------------|------|
| `user.login` | ログイン成功 |
| `user.logout` | ログアウト |
| `user.login_failed` | ログイン失敗 |
| `user.login_mfa_failed` | MFA 認証失敗 |
| `user.password_change` | パスワード変更 |
| `user.role_change` | ロール変更 |
| `user.account_locked` | アカウントロック |
| `user.account_unlocked` | アカウントロック解除 |
| `user.create` | ユーザー作成 |
| `user.deactivate` | ユーザー無効化 |

### 4.7 AI 操作

| アクション名 | 説明 |
|------------|------|
| `ai.decision` | AI 決定記録 |
| `ai.repair_proposed` | AI 修復提案 |
| `ai.repair_executed` | AI 自動修復実行 |
| `ai.repair_rejected` | AI 修復案拒否 |
| `ai.escalate` | AI によるエスカレーション |
| `ai.drift_detected` | モデルドリフト検知 |
| `ai.bias_flagged` | バイアスフラグ記録 |

### 4.8 システム・監査

| アクション名 | 説明 |
|------------|------|
| `system.config_change` | システム設定変更 |
| `system.backup` | バックアップ実行 |
| `system.maintenance_start` | メンテナンス開始 |
| `system.maintenance_end` | メンテナンス終了 |
| `audit.export` | 監査ログエクスポート |
| `audit.integrity_check` | 整合性検証実行 |
| `audit.archive` | 監査ログアーカイブ |
| `audit.dispose` | 監査ログ廃棄（保管期間満了） |

---

## 5. ハッシュチェーン実装方針

### 5.1 チェーン生成ロジック（Python）

```python
import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional


@dataclass
class AuditLogRecord:
    log_id: str
    timestamp: datetime
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    result: str


def compute_log_hash(log_record: AuditLogRecord, prev_hash: str) -> str:
    """
    監査ログのSHA-256ハッシュを計算する。
    prev_hashを含めることで改ざん検知チェーンを形成する。

    Args:
        log_record: 監査ログレコード
        prev_hash: 前レコードのハッシュ値（最初のレコードは'genesis'）
    Returns:
        SHA-256ハッシュ文字列（64文字の16進数）
    """
    chain_data = {
        "log_id": str(log_record.log_id),
        "timestamp": log_record.timestamp.astimezone(timezone.utc).isoformat(),
        "user_id": str(log_record.user_id) if log_record.user_id else None,
        "action": log_record.action,
        "resource_type": log_record.resource_type,
        "resource_id": str(log_record.resource_id) if log_record.resource_id else None,
        "result": log_record.result,
        "prev_hash": prev_hash
    }
    data_str = json.dumps(chain_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def verify_hash_chain(log_records: list[AuditLogRecord], stored_hashes: list[str]) -> dict:
    """
    監査ログのハッシュチェーンを検証する。

    Returns:
        {
            "valid": bool,
            "broken_at": Optional[str],  # 破損箇所のlog_id
            "broken_index": Optional[int],
            "verified_count": int
        }
    """
    if not log_records:
        return {"valid": True, "broken_at": None, "broken_index": None, "verified_count": 0}

    prev_hash = "genesis"
    for i, (record, stored_hash) in enumerate(zip(log_records, stored_hashes)):
        computed = compute_log_hash(record, prev_hash)
        if computed != stored_hash:
            return {
                "valid": False,
                "broken_at": record.log_id,
                "broken_index": i,
                "verified_count": i
            }
        prev_hash = stored_hash

    return {
        "valid": True,
        "broken_at": None,
        "broken_index": None,
        "verified_count": len(log_records)
    }
```

### 5.2 メルクルツリー検証（PostgreSQL 実装）

```sql
-- メルクルツリーのルートハッシュを計算するストアド関数
-- （PostgreSQL の pgcrypto 拡張が必要）
CREATE OR REPLACE FUNCTION compute_merkle_root(
    p_start TIMESTAMPTZ,
    p_end   TIMESTAMPTZ
)
RETURNS VARCHAR(64) AS $$
DECLARE
    v_hashes    TEXT[];
    v_level     TEXT[];
    v_n         INTEGER;
    v_i         INTEGER;
    v_combined  TEXT;
BEGIN
    -- 期間内のハッシュ値を収集
    SELECT ARRAY_AGG(current_hash ORDER BY timestamp, log_id)
    INTO v_hashes
    FROM audit_logs
    WHERE timestamp >= p_start AND timestamp < p_end;

    IF v_hashes IS NULL OR ARRAY_LENGTH(v_hashes, 1) = 0 THEN
        RETURN NULL;
    END IF;

    -- メルクルツリーの段階的計算
    WHILE ARRAY_LENGTH(v_hashes, 1) > 1 LOOP
        v_level := ARRAY[]::TEXT[];
        v_n     := ARRAY_LENGTH(v_hashes, 1);
        v_i     := 1;

        WHILE v_i <= v_n LOOP
            IF v_i + 1 <= v_n THEN
                v_combined := v_hashes[v_i] || v_hashes[v_i + 1];
            ELSE
                -- 奇数個の場合は末尾を複製
                v_combined := v_hashes[v_i] || v_hashes[v_i];
            END IF;
            v_level := ARRAY_APPEND(
                v_level,
                ENCODE(DIGEST(v_combined, 'sha256'), 'hex')
            );
            v_i := v_i + 2;
        END LOOP;

        v_hashes := v_level;
    END LOOP;

    RETURN v_hashes[1];
END;
$$ LANGUAGE plpgsql;
```

### 5.3 整合性検証スケジュール

| 検証頻度 | 対象 | 担当 | アラート条件 |
|---------|------|------|------------|
| 1時間毎 | 直近1時間のログ | 自動（GitHub Actions） | チェーン破損検知 |
| 日次 | 当日全ログ | 自動（夜間バッチ） | 未処理ログ件数異常 |
| 週次 | 7日分チェーン + メルクルツリー | Auditorロール確認 | root_hash 不一致 |
| 月次 | 月全体 + 整合性レポート | 内部監査担当 | 全破損件数レポート |

---

## 6. 監視・アラートクエリ（v2.0追加）

### 6.1 異常ログイン検知

```sql
-- 同一IPからの短時間連続ログイン失敗（ブルートフォース検知）
SELECT
    ip_address,
    COUNT(*) AS failure_count,
    MIN(timestamp) AS first_attempt,
    MAX(timestamp) AS last_attempt,
    ARRAY_AGG(DISTINCT user_name) AS targeted_users
FROM audit_logs
WHERE action = 'user.login_failed'
  AND timestamp > NOW() - INTERVAL '15 minutes'
GROUP BY ip_address
HAVING COUNT(*) >= 5
ORDER BY failure_count DESC;

-- 深夜時間帯（22:00-06:00 JST）の特権操作検知
SELECT
    log_id,
    timestamp AT TIME ZONE 'Asia/Tokyo' AS timestamp_jst,
    user_name,
    user_role,
    action,
    resource_type,
    resource_id,
    ip_address
FROM audit_logs
WHERE user_role IN ('SystemAdmin', 'ChangeManager')
  AND EXTRACT(HOUR FROM timestamp AT TIME ZONE 'Asia/Tokyo')
        BETWEEN 22 AND 23
     OR EXTRACT(HOUR FROM timestamp AT TIME ZONE 'Asia/Tokyo')
        BETWEEN 0 AND 6
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

### 6.2 AI 決定品質モニタリング

```sql
-- 低信頼度 AI 決定の集計（信頼度 0.7 未満）
SELECT
    agent_type,
    decision_type,
    COUNT(*) AS low_confidence_count,
    AVG(confidence_score) AS avg_confidence,
    MIN(confidence_score) AS min_confidence,
    COUNT(*) FILTER (WHERE was_executed = TRUE) AS executed_despite_low_confidence
FROM ai_audit_logs
WHERE confidence_score < 0.70
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY agent_type, decision_type
ORDER BY low_confidence_count DESC;

-- モデルドリフト傾向分析
SELECT
    DATE_TRUNC('day', timestamp) AS day,
    agent_type,
    AVG(drift_score) AS avg_drift,
    MAX(drift_score) AS max_drift,
    COUNT(*) FILTER (WHERE drift_score > 0.5) AS high_drift_count
FROM ai_audit_logs
WHERE drift_score IS NOT NULL
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', timestamp), agent_type
ORDER BY day, agent_type;

-- 人間承認待ちの AI 決定（24時間以上未承認）
SELECT
    ai_log_id,
    agent_type,
    decision_type,
    confidence_score,
    autonomy_level,
    timestamp,
    NOW() - timestamp AS waiting_duration
FROM ai_audit_logs
WHERE requires_human_approval = TRUE
  AND human_approved IS NULL
  AND was_executed IS NULL
  AND timestamp < NOW() - INTERVAL '24 hours'
ORDER BY timestamp ASC;
```

### 6.3 J-SOX 変更管理監査クエリ

```sql
-- 変更承認者と実行者の同一性チェック（SoD 違反検知）
WITH change_approve AS (
    SELECT resource_id, user_id AS approver_id, timestamp AS approved_at
    FROM audit_logs
    WHERE action = 'change.approve' AND result = 'success'
),
change_deploy AS (
    SELECT resource_id, user_id AS deployer_id, timestamp AS deployed_at
    FROM audit_logs
    WHERE action = 'change.deploy' AND result = 'success'
)
SELECT
    ca.resource_id AS change_id,
    ca.approver_id,
    cd.deployer_id,
    ca.approved_at,
    cd.deployed_at
FROM change_approve ca
JOIN change_deploy cd ON ca.resource_id = cd.resource_id
WHERE ca.approver_id = cd.deployer_id  -- SoD 違反（承認者と実行者が同一）
ORDER BY cd.deployed_at DESC;

-- 監査ログのチェーン完全性サマリー
SELECT
    TO_CHAR(DATE_TRUNC('month', period_start), 'YYYY-MM') AS month,
    SUM(log_count) AS total_logs,
    BOOL_AND(chain_valid) AS all_valid,
    SUM(broken_count) AS total_broken,
    MAX(checked_at) AS last_checked
FROM audit_log_integrity
GROUP BY DATE_TRUNC('month', period_start)
ORDER BY month DESC;
```

---

## 7. アクセス制御

| ロール | 参照 | 削除 | エクスポート | 整合性検証 |
|-------|------|------|-----------|-----------|
| SystemAdmin | 自己ログのみ | ❌ | ❌ | ❌ |
| ServiceManager | 配下チームのログ | ❌ | ❌ | ❌ |
| ProcessOwner | 担当プロセスのみ | ❌ | ❌ | ❌ |
| ChangeManager | 変更関連ログのみ | ❌ | ❌ | ❌ |
| Auditor | ✅ 全ログ | ❌ | ✅ | ✅ |
| AI Agent | 書き込みのみ | ❌ | ❌ | ❌ |
| Viewer | ❌ | ❌ | ❌ | ❌ |

> **注**: 監査ログはアクセス制御の最後の砦であり、いかなるロールも削除不可とする（保管期間満了後のシステム自動廃棄のみ許可、廃棄記録自体は永続保管）

---

## 8. J-SOX要件対応

| J-SOX要件 | 対応するスキーマ要素 |
|----------|-------------------|
| アクセス管理ログ | `user_id`, `action`, `result`, `ip_address` |
| 変更管理証跡 | `resource_type='change_request'`, `old_value`, `new_value` |
| 特権操作記録 | `user_role='SystemAdmin'`, `action` フィルタ |
| 職務分離（SoD） | 承認者・実行者の `user_id` 相互参照クエリ |
| ログ完全性 | `current_hash`, `prev_log_hash`, メルクルツリー検証 |
| AI 統治 | `ai_audit_logs.autonomy_level`, `rationale`, `approver_user_id` |
| 7年保管 | 月次パーティション + アーカイブポリシー |

---

## 9. 保管と廃棄

- **オンラインストレージ**: 1年（PostgreSQL 月次パーティション）
- **アーカイブストレージ**: 6年（コールドストレージ、AES-256 暗号化 gzip 圧縮）
- **合計保管期間**: 7年（J-SOX 要件）
- **廃棄**: 保管期間満了後、セキュア消去（NIST SP 800-88 準拠）
- **廃棄記録**: 廃棄実行ログ自体は永続保管（廃棄の証跡）

---

*最終更新: 2026-03-02*
*バージョン: 2.0.0*
*承認者: システム管理者 / コンプライアンス委員会*
