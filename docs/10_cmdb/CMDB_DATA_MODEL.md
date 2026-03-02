# CMDBデータモデル定義

**ドキュメント番号**: SM-CMDB-001
**バージョン**: 2.0
**分類**: CMDB設計仕様 / データモデル
**作成日**: 2026-03-02
**最終更新日**: 2026-03-02
**準拠規格**: ITIL 4 / ISO/IEC 20000 / J-SOX
**ステータス**: 承認済み

---

## 1. 目的と範囲

### 1.1 目的

本ドキュメントは、ServiceMatrixにおけるCMDB（Configuration Management Database: 構成管理データベース）のデータモデルを定義する。CMDBはServiceMatrixの統治基盤の中核をなし、以下の機能を提供する：

- ITサービスを構成するすべての構成アイテム（CI）の登録・管理
- CI間の依存関係・関連性の可視化
- インシデント・変更・問題管理との統合による影響分析支援
- J-SOX対応に必要な構成変更履歴の完全記録

### 1.2 範囲

| 対象範囲 | 詳細 |
|---|---|
| 管理対象環境 | Production / Staging / Development / DR |
| CI種別 | Server / Application / Service / Database / Network / Software / その他 |
| 連携プロセス | インシデント管理、変更管理、問題管理、SLA管理 |
| 連携システム | GitHub Issues / PostgreSQL / ServiceMatrix API |

---

## 2. CI（構成アイテム）基本属性

### 2.1 CI共通必須属性

すべてのCIが持つ標準属性を以下に定義する。

| 属性名 | データ型 | 必須 | 説明 |
|---|---|---|---|
| `ci_id` | UUID | 必須 | CI一意識別子（UUID v4） |
| `ci_code` | VARCHAR(30) | 必須 | 人間可読CI識別子（例: CI-SRV-001） |
| `ci_name` | VARCHAR(255) | 必須 | CI名称（組織内で一意推奨） |
| `ci_type` | VARCHAR(50) | 必須 | CI種別（後述の種別分類参照） |
| `ci_status` | VARCHAR(30) | 必須 | CIステータス（後述の状態遷移参照） |
| `owner` | UUID | 必須 | CI所有者ユーザーID |
| `owner_team` | VARCHAR(100) | 推奨 | 所有チーム名 |
| `version` | VARCHAR(50) | 条件付き | バージョン情報（Application/Softwareは必須） |
| `criticality` | VARCHAR(20) | 必須 | 重要度（Critical/High/Medium/Low） |
| `environment` | VARCHAR(20) | 必須 | 環境（Production/Staging/Development/DR） |
| `description` | TEXT | 推奨 | CI説明・用途 |
| `location` | VARCHAR(255) | 条件付き | 物理/論理ロケーション（Serverは必須） |
| `tags` | TEXT[] | 任意 | 検索・分類用タグ |
| `github_issue_refs` | INTEGER[] | 任意 | 関連GitHubIssue番号 |
| `created_at` | TIMESTAMPTZ | 自動 | 作成日時（UTC） |
| `updated_at` | TIMESTAMPTZ | 自動 | 最終更新日時（UTC） |
| `retired_at` | TIMESTAMPTZ | 条件付き | 廃止日時（Retired状態時に設定） |
| `created_by` | UUID | 自動 | 作成者ユーザーID |
| `updated_by` | UUID | 自動 | 最終更新者ユーザーID |

### 2.2 CIステータス定義

| ステータス | 説明 | 遷移可能先 |
|---|---|---|
| `Planned` | 導入計画中 | Ordered、Cancelled |
| `Ordered` | 発注済み（未受領） | Received、Cancelled |
| `Received` | 受領済み（未稼働） | Active、Cancelled |
| `Active` | 稼働中（通常運用） | Maintenance、Retired |
| `Maintenance` | メンテナンス中 | Active、Retired |
| `Retired` | 廃止（運用停止済み） | Disposed |
| `Disposed` | 処分済み（最終状態） | なし |
| `Cancelled` | キャンセル（最終状態） | なし |

---

## 3. CI種別分類

### 3.1 CI種別一覧

| ci_type | 説明 | コード接頭辞 | 例 |
|---|---|---|---|
| `Server` | 物理・仮想サーバー | CI-SRV- | Web Server 01、DB Primary |
| `Application` | アプリケーション・マイクロサービス | CI-APP- | ServiceMatrix API、Auth Service |
| `Service` | ビジネスサービス・ITサービス定義 | CI-SVC- | メールサービス、CRMサービス |
| `Database` | データベースインスタンス | CI-DB- | PostgreSQL Main、Redis Cache |
| `Network` | ネットワーク機器・サービス | CI-NET- | Firewall 01、Load Balancer |
| `Software` | ソフトウェアライセンス・OS | CI-SW- | RHEL License、Python 3.12 |
| `Storage` | ストレージシステム | CI-STG- | NFS Volume、S3 Bucket |
| `Middleware` | ミドルウェア・プラットフォーム | CI-MWR- | Nginx、RabbitMQ |
| `Environment` | 実行環境定義 | CI-ENV- | Production Env、Staging Env |
| `Document` | 統治文書・手順書 | CI-DOC- | SLA定義書、運用手順書 |

### 3.2 CI種別別追加属性

**Server**:

| 属性名 | データ型 | 必須 |
|---|---|---|
| `ip_address` | VARCHAR(45) | 必須 |
| `os_type` | VARCHAR(50) | 必須 |
| `os_version` | VARCHAR(50) | 必須 |
| `cpu_cores` | INTEGER | 必須 |
| `memory_gb` | NUMERIC(6,2) | 必須 |
| `storage_gb` | NUMERIC(10,2) | 必須 |
| `is_virtual` | BOOLEAN | 必須 |
| `hypervisor` | VARCHAR(50) | 条件付き |
| `datacenter` | VARCHAR(100) | 推奨 |

**Application**:

| 属性名 | データ型 | 必須 |
|---|---|---|
| `app_type` | VARCHAR(30) | 必須（Web/API/Batch/Mobile） |
| `language` | VARCHAR(50) | 必須 |
| `framework` | VARCHAR(50) | 推奨 |
| `repository_url` | VARCHAR(500) | 推奨 |
| `port` | INTEGER | 推奨 |
| `health_check_url` | VARCHAR(500) | 推奨 |

**Database**:

| 属性名 | データ型 | 必須 |
|---|---|---|
| `db_engine` | VARCHAR(50) | 必須（PostgreSQL/MySQL/Redis等） |
| `db_version` | VARCHAR(30) | 必須 |
| `host` | VARCHAR(255) | 必須 |
| `port` | INTEGER | 必須 |
| `is_cluster` | BOOLEAN | 必須 |
| `replication_type` | VARCHAR(30) | 条件付き |

---

## 4. PostgreSQL テーブル定義

### 4.1 configuration_items テーブル

```sql
-- ==============================================================
-- configuration_items: CMDB 構成アイテムマスターテーブル
-- ==============================================================
CREATE TABLE configuration_items (
    ci_id               UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    ci_code             VARCHAR(30)     NOT NULL UNIQUE,
    ci_name             VARCHAR(255)    NOT NULL,
    ci_type             VARCHAR(50)     NOT NULL,
    ci_status           VARCHAR(30)     NOT NULL DEFAULT 'Planned',
    owner               UUID            NOT NULL REFERENCES users(user_id),
    owner_team          VARCHAR(100),
    version             VARCHAR(50),
    criticality         VARCHAR(20)     NOT NULL DEFAULT 'Medium',
    environment         VARCHAR(20)     NOT NULL,
    description         TEXT,
    location            VARCHAR(255),
    tags                TEXT[]          NOT NULL DEFAULT '{}',
    github_issue_refs   INTEGER[]       NOT NULL DEFAULT '{}',
    attributes          JSONB           NOT NULL DEFAULT '{}',
    -- ライフサイクル
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    retired_at          TIMESTAMPTZ,
    disposed_at         TIMESTAMPTZ,
    created_by          UUID            NOT NULL REFERENCES users(user_id),
    updated_by          UUID            NOT NULL REFERENCES users(user_id),
    -- 論理削除
    is_deleted          BOOLEAN         NOT NULL DEFAULT FALSE,
    deleted_at          TIMESTAMPTZ,
    deleted_by          UUID            REFERENCES users(user_id),

    CONSTRAINT ci_type_check CHECK (
        ci_type IN (
            'Server', 'Application', 'Service', 'Database',
            'Network', 'Software', 'Storage', 'Middleware',
            'Environment', 'Document'
        )
    ),
    CONSTRAINT ci_status_check CHECK (
        ci_status IN (
            'Planned', 'Ordered', 'Received', 'Active',
            'Maintenance', 'Retired', 'Disposed', 'Cancelled'
        )
    ),
    CONSTRAINT criticality_check CHECK (
        criticality IN ('Critical', 'High', 'Medium', 'Low')
    ),
    CONSTRAINT environment_check CHECK (
        environment IN ('Production', 'Staging', 'Development', 'DR')
    )
);

-- インデックス
CREATE INDEX idx_ci_code ON configuration_items(ci_code);
CREATE INDEX idx_ci_type ON configuration_items(ci_type);
CREATE INDEX idx_ci_status ON configuration_items(ci_status)
    WHERE is_deleted = FALSE;
CREATE INDEX idx_ci_owner ON configuration_items(owner);
CREATE INDEX idx_ci_environment ON configuration_items(environment);
CREATE INDEX idx_ci_criticality ON configuration_items(criticality);
CREATE INDEX idx_ci_tags ON configuration_items USING gin(tags);
CREATE INDEX idx_ci_attributes ON configuration_items USING gin(attributes);
CREATE INDEX idx_ci_github_refs ON configuration_items USING gin(github_issue_refs);
CREATE INDEX idx_ci_active ON configuration_items(ci_id)
    WHERE ci_status = 'Active' AND is_deleted = FALSE;

COMMENT ON TABLE configuration_items IS 'CMDB構成アイテムマスター';
COMMENT ON COLUMN configuration_items.ci_code IS '人間可読CI識別子（例: CI-SRV-001）';
COMMENT ON COLUMN configuration_items.attributes IS 'CI種別別追加属性（JSON形式）';
```

### 4.2 ci_relationships テーブル

```sql
-- ==============================================================
-- ci_relationships: CI間の関係性テーブル
-- ==============================================================
CREATE TABLE ci_relationships (
    relationship_id     UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    source_ci_id        UUID            NOT NULL REFERENCES configuration_items(ci_id),
    target_ci_id        UUID            NOT NULL REFERENCES configuration_items(ci_id),
    relationship_type   VARCHAR(50)     NOT NULL,
    description         TEXT,
    strength            VARCHAR(20)     NOT NULL DEFAULT 'medium',
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    created_by          UUID            NOT NULL REFERENCES users(user_id),

    CONSTRAINT no_self_relationship CHECK (source_ci_id != target_ci_id),
    CONSTRAINT relationship_type_check CHECK (
        relationship_type IN (
            'depends_on', 'used_by', 'hosted_on',
            'backed_up_by', 'redundant_with',
            'connects_to', 'runs_on', 'member_of'
        )
    ),
    CONSTRAINT strength_check CHECK (
        strength IN ('critical', 'high', 'medium', 'low')
    )
);

CREATE UNIQUE INDEX idx_ci_rel_unique
    ON ci_relationships(source_ci_id, target_ci_id, relationship_type)
    WHERE is_active = TRUE;

CREATE INDEX idx_ci_rel_source ON ci_relationships(source_ci_id);
CREATE INDEX idx_ci_rel_target ON ci_relationships(target_ci_id);
CREATE INDEX idx_ci_rel_type ON ci_relationships(relationship_type);
```

### 4.3 ci_history テーブル（変更管理との連携）

```sql
-- ==============================================================
-- ci_history: CI変更履歴テーブル（変更記録のCI履歴追跡）
-- ==============================================================
CREATE TABLE ci_history (
    history_id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    ci_id               UUID            NOT NULL REFERENCES configuration_items(ci_id),
    change_type         VARCHAR(30)     NOT NULL, -- created / updated / status_changed / retired
    field_name          VARCHAR(100),             -- 変更されたフィールド名（updated時）
    old_value           JSONB,                    -- 変更前の値
    new_value           JSONB,                    -- 変更後の値
    change_reason       TEXT,
    changed_by          UUID            NOT NULL REFERENCES users(user_id),
    changed_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    -- 変更管理との連携
    change_request_id   UUID            REFERENCES changes(change_id),
    -- AI操作フラグ
    is_ai_generated     BOOLEAN         NOT NULL DEFAULT FALSE,
    ai_agent_id         VARCHAR(100),
    ai_confidence_score NUMERIC(3,2)
) PARTITION BY RANGE (changed_at);

-- 月次パーティション（年単位で作成）
CREATE TABLE ci_history_2026_01
    PARTITION OF ci_history
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE ci_history_2026_02
    PARTITION OF ci_history
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE ci_history_2026_03
    PARTITION OF ci_history
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE INDEX idx_ci_history_ci_id ON ci_history(ci_id, changed_at DESC);
CREATE INDEX idx_ci_history_change_req ON ci_history(change_request_id)
    WHERE change_request_id IS NOT NULL;
CREATE INDEX idx_ci_history_changed_at ON ci_history(changed_at DESC);

COMMENT ON TABLE ci_history IS 'CI変更履歴（J-SOX対応・7年保管）';
```

---

## 5. 変更管理との連携（変更記録のCI履歴追跡）

### 5.1 変更管理との連携フロー

```
RFC作成時:
  → change_request.affected_ci_ids[] にCI IDを記録
  → 影響分析APIでCI依存関係を自動探索

変更承認時:
  → 変更対象CIのステータスを'Maintenance'に変更
  → ci_history に変更記録を作成（change_request_id付き）

変更実施完了時:
  → CI属性を変更後の値に更新
  → ci_history に更新記録を作成（change_request_id付き）
  → CIステータスを'Active'に戻す
  → PIR（事後レビュー）でCI整合性確認
```

### 5.2 CI-変更管理連携テーブル

```sql
-- changes テーブルとCI の中間テーブル
CREATE TABLE change_affected_cis (
    id                  BIGSERIAL       PRIMARY KEY,
    change_id           UUID            NOT NULL REFERENCES changes(change_id),
    ci_id               UUID            NOT NULL REFERENCES configuration_items(ci_id),
    impact_type         VARCHAR(30)     NOT NULL DEFAULT 'direct', -- direct / indirect
    impact_description  TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),

    UNIQUE (change_id, ci_id)
);

CREATE INDEX idx_change_affected_cis_change ON change_affected_cis(change_id);
CREATE INDEX idx_change_affected_cis_ci ON change_affected_cis(ci_id);
```

---

## 6. CMDBデータ整合性

### 6.1 自動整合性チェック（日次バッチ）

| チェック項目 | 検出SQL | 対応 |
|---|---|---|
| 孤立CI（関係性なし） | ci_relationships非参照のActive CI | 警告通知 + 棚卸リストへ追加 |
| 循環依存 | グラフトラバーサルで循環検出 | エラー通知 + 登録拒否 |
| 無効オーナー | usersに存在しないowner ID | 警告通知 + SystemAdminへ通知 |
| 必須属性欠損 | 種別必須フィールドがNULLのCI | 警告通知 |
| Active CI の Retired 依存 | Active CIがRetiredなCIに依存 | 警告通知 |

### 6.2 トリガーによる自動更新

```sql
-- updated_at の自動更新トリガー
CREATE OR REPLACE FUNCTION update_ci_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ci_updated_at
    BEFORE UPDATE ON configuration_items
    FOR EACH ROW
    EXECUTE FUNCTION update_ci_updated_at();

-- CI変更時の自動履歴記録トリガー
CREATE OR REPLACE FUNCTION record_ci_history()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        INSERT INTO ci_history (
            ci_id, change_type, field_name,
            old_value, new_value, changed_by
        )
        SELECT
            NEW.ci_id,
            'updated',
            key,
            to_jsonb(old_val),
            to_jsonb(new_val),
            NEW.updated_by
        FROM jsonb_each_text(to_jsonb(OLD)) AS old_rec(key, old_val)
        JOIN jsonb_each_text(to_jsonb(NEW)) AS new_rec(key, new_val) USING (key)
        WHERE old_val IS DISTINCT FROM new_val
          AND key NOT IN ('updated_at', 'updated_by');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ci_history
    AFTER UPDATE ON configuration_items
    FOR EACH ROW
    EXECUTE FUNCTION record_ci_history();
```

---

## 7. 改訂履歴

| バージョン | 日付 | 変更概要 | 変更者 |
|---|---|---|---|
| 1.0 | 2026-03-02 | 初版作成 | - |
| 2.0 | 2026-03-02 | PostgreSQL DDL追加、CI種別詳細化、変更管理連携テーブル追加、トリガー実装追加 | - |

---

*本ドキュメントはServiceMatrixプロジェクトの統治原則に基づき管理される。*
*変更はChange Issue → PR → CI検証 → 承認のフローに従うこと。*
