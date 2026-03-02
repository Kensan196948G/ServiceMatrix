# 監査ログスキーマ定義

AUDIT_LOG_SCHEMA.md
Version: 1.0
Category: Data Model
Compliance: J-SOX / ISO 20000 / ITIL 4

---

## 1. 目的

本ドキュメントは、ServiceMatrixにおける監査ログのデータスキーマを定義する。
すべてのユーザー操作・AI決定・システムイベントを改ざん不能な形式で記録し、
J-SOX内部統制・ISO 20000監査要件を満たすことを目的とする。

---

## 2. 監査ログテーブル定義

### 2.1 メイン監査ログテーブル（audit_logs）

```sql
-- 監査ログテーブル
CREATE TABLE audit_logs (
    -- 主キー
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- タイムスタンプ（UTC・ナノ秒精度）
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- アクター情報
    user_id         UUID REFERENCES users(user_id),
    user_name       VARCHAR(255),
    user_role       VARCHAR(100),
    session_id      UUID,
    ip_address      INET,
    user_agent      TEXT,

    -- 操作情報
    action          VARCHAR(100) NOT NULL,
    -- 例: 'incident.create', 'change.approve', 'user.login', 'ai.decision'
    resource_type   VARCHAR(100) NOT NULL,
    -- 例: 'incident', 'change_request', 'user', 'configuration_item'
    resource_id     UUID,

    -- 変更内容
    old_value       JSONB,
    new_value       JSONB,
    diff_summary    TEXT,

    -- 操作結果
    result          VARCHAR(50) NOT NULL,
    -- 例: 'success', 'failure', 'denied', 'partial'
    error_code      VARCHAR(50),
    error_message   TEXT,

    -- リクエスト情報
    request_id      UUID,
    api_endpoint    VARCHAR(500),
    http_method     VARCHAR(10),
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

-- 月次パーティション作成例（2026年）
CREATE TABLE audit_logs_2026_03 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

### 2.2 AI操作専用ログテーブル（ai_audit_logs）

```sql
-- AI操作監査ログテーブル
CREATE TABLE ai_audit_logs (
    -- 主キー（audit_logsと連携）
    ai_log_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_id          UUID REFERENCES audit_logs(log_id),

    -- AIエージェント情報
    agent_id        VARCHAR(255) NOT NULL,
    agent_type      VARCHAR(100) NOT NULL,
    -- 例: 'foundation-governance', 'security-reviewer', 'claude-lead'
    agent_version   VARCHAR(50),
    model_name      VARCHAR(100),

    -- 入力コンテキスト
    input_context   JSONB NOT NULL,
    input_tokens    INTEGER,
    prompt_hash     VARCHAR(64),  -- プロンプトの一方向ハッシュ（プライバシー保護）

    -- AI決定内容
    decision_type   VARCHAR(100) NOT NULL,
    -- 例: 'priority_assessment', 'risk_evaluation', 'repair_proposal'
    decision        JSONB NOT NULL,
    confidence_score DECIMAL(5, 4),  -- 0.0000 - 1.0000
    rationale       TEXT,

    -- 出力情報
    output_tokens   INTEGER,
    response_time_ms INTEGER,

    -- 自律度レベル
    autonomy_level  SMALLINT NOT NULL,
    -- L0: 人間判断のみ / L1: 推奨のみ / L2: 低リスク自動 / L3: 自動実行+報告

    -- 人間承認情報（L0/L1のみ）
    requires_human_approval BOOLEAN NOT NULL DEFAULT TRUE,
    human_approved  BOOLEAN,
    approver_user_id UUID REFERENCES users(user_id),
    approval_timestamp TIMESTAMPTZ,
    approval_comment TEXT,

    -- 実行結果
    was_executed    BOOLEAN,
    execution_outcome VARCHAR(100),
    -- 例: 'accepted', 'rejected', 'modified', 'auto_executed'

    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
PARTITION BY RANGE (timestamp);

CREATE INDEX idx_ai_audit_logs_agent ON ai_audit_logs (agent_type, timestamp DESC);
CREATE INDEX idx_ai_audit_logs_decision ON ai_audit_logs (decision_type, timestamp DESC);
CREATE INDEX idx_ai_audit_logs_autonomy ON ai_audit_logs (autonomy_level, timestamp DESC);
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
    broken_at_log   UUID,  -- チェーン破損箇所
    verified_by     UUID REFERENCES users(user_id)
);
```

---

## 3. アクション定義一覧

| カテゴリ | アクション名 | 説明 |
|---------|------------|------|
| インシデント | `incident.create` | インシデント作成 |
| インシデント | `incident.update` | インシデント更新 |
| インシデント | `incident.resolve` | インシデント解決 |
| インシデント | `incident.close` | インシデントクローズ |
| 変更管理 | `change.create` | 変更リクエスト作成 |
| 変更管理 | `change.approve` | 変更承認 |
| 変更管理 | `change.reject` | 変更拒否 |
| 変更管理 | `change.deploy` | 変更デプロイ |
| ユーザー | `user.login` | ログイン |
| ユーザー | `user.logout` | ログアウト |
| ユーザー | `user.login_failed` | ログイン失敗 |
| ユーザー | `user.role_change` | ロール変更 |
| AI | `ai.decision` | AI決定記録 |
| AI | `ai.repair_proposed` | AI修復提案 |
| AI | `ai.repair_executed` | AI自動修復実行 |
| システム | `system.config_change` | 設定変更 |
| システム | `system.backup` | バックアップ実行 |
| 監査 | `audit.export` | 監査ログエクスポート |

---

## 4. ハッシュチェーン実装方針

### 4.1 チェーン生成ロジック

```python
import hashlib
import json
from datetime import datetime

def compute_log_hash(log_record: dict, prev_hash: str) -> str:
    """
    監査ログのSHA-256ハッシュを計算する
    prev_hashを含めることで改ざん検知チェーンを形成
    """
    chain_data = {
        "log_id": str(log_record["log_id"]),
        "timestamp": log_record["timestamp"].isoformat(),
        "user_id": str(log_record["user_id"]),
        "action": log_record["action"],
        "resource_type": log_record["resource_type"],
        "resource_id": str(log_record["resource_id"]),
        "result": log_record["result"],
        "prev_hash": prev_hash
    }
    data_str = json.dumps(chain_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()
```

### 4.2 整合性検証スケジュール

| 検証頻度 | 対象 | 担当 |
|---------|------|------|
| 1時間毎 | 直近1時間のログ | 自動（CI/CD） |
| 日次 | 当日全ログ | 自動（夜間バッチ） |
| 週次 | 7日分チェーン | Auditorロール確認 |
| 月次 | 月全体 + 整合性レポート | 内部監査担当 |

---

## 5. アクセス制御

| ロール | 参照 | 削除 | エクスポート | 整合性検証 |
|-------|------|------|-----------|-----------|
| SystemAdmin | 自己ログのみ | ❌ | ❌ | ❌ |
| Auditor | ✅ 全ログ | ❌ | ✅ | ✅ |
| ProcessOwner | 担当プロセスのみ | ❌ | ❌ | ❌ |
| AI Agent | 書き込みのみ | ❌ | ❌ | ❌ |

> **注**: 監査ログはアクセス制御の最後の砦であり、いかなるロールも削除不可とする（保管期間満了後のシステム自動削除のみ許可）

---

## 6. J-SOX要件対応

| J-SOX要件 | 対応するスキーマ要素 |
|----------|-------------------|
| アクセス管理ログ | `user_id`, `action`, `result`, `ip_address` |
| 変更管理証跡 | `resource_type='change_request'`, `old_value`, `new_value` |
| 特権操作記録 | `user_role='SystemAdmin'`, `action`フィルタ |
| ログ完全性 | `current_hash`, `prev_log_hash`, ハッシュチェーン |
| 7年保管 | 月次パーティション + アーカイブポリシー |

---

## 7. 保管と廃棄

- **オンラインストレージ**: 1年（PostgreSQL月次パーティション）
- **アーカイブストレージ**: 6年（コールドストレージ）
- **合計保管期間**: 7年（J-SOX要件）
- **廃棄**: 保管期間満了後、セキュア消去（NIST SP 800-88準拠）

---

*最終更新: 2026-03-02*
*バージョン: 1.0.0*
*承認者: システム管理者*
