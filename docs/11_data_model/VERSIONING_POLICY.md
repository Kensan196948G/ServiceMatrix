# バージョニングポリシー

VERSIONING_POLICY.md
Version: 2.0
Category: Data Model
Compliance: ITIL 4 / ISO 20000

---

## 1. 目的

本ドキュメントは、ServiceMatrixにおけるバージョニング戦略を定義する。
ソフトウェア・API・データスキーマ・ドキュメントの各バージョン管理を統一し、
後方互換性・移行管理・変更追跡を確実に行うことを目的とする。

**v2.0 強化内容:**

- TypeScript / Pydantic インターフェースバージョニング追加
- Alembic マイグレーション高度パターン（ゼロダウンタイム移行・依存関係制御）追加
- マイグレーション健全性チェッククエリ追加
- ロールバック戦略・非常停止手順追加
- バージョン互換性マトリックス拡充

---

## 2. Semantic Versioning（SemVer 2.0.0）

### 2.1 バージョン番号体系

```
MAJOR.MINOR.PATCH[-prerelease][+build]

例:
  1.0.0        - 初回リリース
  1.1.0        - 機能追加
  1.1.1        - バグ修正
  2.0.0        - 破壊的変更
  1.2.0-rc.1   - リリース候補
  1.2.0-beta.3 - ベータ版
  1.2.0+sha.abc123 - ビルドメタデータ付き
```

### 2.2 バージョン番号変更ルール

| バージョン | 変更条件 | 例 |
|----------|---------|---|
| **MAJOR** | 後方互換性のない変更（破壊的変更） | APIエンドポイント削除・レスポンス構造変更・スキーマ非互換変更 |
| **MINOR** | 後方互換な機能追加 | 新エンドポイント追加・新フィールド追加（nullable）・新しい列挙値 |
| **PATCH** | 後方互換なバグ修正 | バグ修正・パフォーマンス改善・ドキュメント修正 |

### 2.3 Conventional Commits との連携

```
# MAJOR バージョンアップ（破壊的変更）
feat!: APIレスポンス形式を変更

BREAKING CHANGE: incidents.severity フィールドを
数値型 (1-5) から文字列型 ('critical', 'high', ...) に変更。
マイグレーションガイド: docs/migration/v1-to-v2.md

# MINOR バージョンアップ（機能追加）
feat: インシデントフィルタリング機能を追加

# PATCH バージョンアップ（バグ修正・改善）
fix: SLA計算の日付ゾーン誤りを修正
perf: 監査ログクエリにインデックスヒント追加
docs: APIリファレンスを更新
refactor: 影響分析アルゴリズムを最適化
```

### 2.4 自動バージョン算出フロー

```yaml
# .github/workflows/release.yml（抜粋）
- name: Determine version bump
  run: |
    # Conventional Commits のフッターを解析
    if git log --format='%B' HEAD~1..HEAD | grep -q 'BREAKING CHANGE'; then
      echo "VERSION_BUMP=major" >> $GITHUB_ENV
    elif git log --format='%s' HEAD~1..HEAD | grep -q '^feat'; then
      echo "VERSION_BUMP=minor" >> $GITHUB_ENV
    else
      echo "VERSION_BUMP=patch" >> $GITHUB_ENV
    fi
```

---

## 3. APIバージョニング

### 3.1 URLパス方式

```
# バージョン管理方式: URLパスに埋め込む（MAJOR バージョンのみ）
/api/v1/incidents          # v1 API（現行）
/api/v2/incidents          # v2 API（破壊的変更後）

# ベースURL構成
https://{host}/api/v{major}/

# MINOR/PATCH は同一 URL、ヘッダーで識別
GET /api/v1/incidents
Accept: application/vnd.servicematrix.v1.2+json
```

### 3.2 バージョンライフサイクル

```
Current (現行) → Deprecated (廃止予告) → Sunset (終了)
                     ↑
              廃止予告期間: 最低3ヶ月
              通知: GitHub Releases + API ヘッダー + Email
```

| バージョン状態 | 内容 |
|-------------|------|
| `current` | 現在推奨バージョン。フル機能・サポート対象 |
| `supported` | まだサポート中だが更新版あり |
| `deprecated` | 廃止予告済み（3ヶ月後に`sunset`） |
| `sunset` | サービス終了。HTTP 410 Gone レスポンス返却 |

### 3.3 廃止予告（Deprecation Notice）

廃止予告時のレスポンスヘッダー:

```http
HTTP/1.1 200 OK
Content-Type: application/json
Deprecation: 2026-09-01
Sunset: 2026-12-01
Link: <https://api.servicematrix.example.com/api/v2/incidents>; rel="successor-version"
Warning: 299 - "This API version is deprecated. Migrate to v2 by 2026-12-01."
X-API-Version: 1.3.2
```

廃止予告時の通知方法:

- GitHub Releases でのアナウンス（Issue 作成）
- API レスポンスヘッダーへの埋め込み
- ドキュメントサイトへの明記
- 登録済みメールアドレスへの通知

### 3.4 API バージョン情報エンドポイント

```
GET /api/version

{
  "current": "v1",
  "versions": {
    "v1": {
      "status": "current",
      "released": "2026-03-15",
      "deprecated_at": null,
      "sunset_at": null
    },
    "v2": {
      "status": "beta",
      "released": null,
      "planned_release": "2027-01-01"
    }
  }
}
```

---

## 4. データスキーマバージョニング

### 4.1 Alembicによるマイグレーション管理

```
alembic/
├── env.py               # 環境設定（DB接続・マルチテナント対応）
├── script.py.mako       # マイグレーションファイルテンプレート
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_incident_sla_fields.py
    ├── 003_add_ai_audit_logs.py
    ├── 004_add_cmdb_relationships.py
    ├── 005_add_impact_analysis.py
    └── README.md        # マイグレーション命名規則・手順
```

### 4.2 標準マイグレーションファイル（基本パターン）

```python
"""Add SLA breach timestamp to incidents

Revision ID: 002_add_incident_sla_fields
Revises: 001_initial_schema
Create Date: 2026-04-01 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_add_incident_sla_fields'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SLA 関連フィールド追加（nullable → 後から NOT NULL 制約可能）
    op.add_column('incidents',
        sa.Column(
            'sla_breach_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='SLA違反発生時刻（UTC）'
        )
    )
    op.add_column('incidents',
        sa.Column(
            'sla_warning_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='SLA警告閾値到達時刻（UTC）'
        )
    )
    # インデックス追加
    op.create_index(
        'idx_incidents_sla_breach',
        'incidents',
        ['sla_breach_at'],
        postgresql_where=sa.text('sla_breach_at IS NOT NULL')
    )


def downgrade() -> None:
    op.drop_index('idx_incidents_sla_breach', table_name='incidents')
    op.drop_column('incidents', 'sla_warning_at')
    op.drop_column('incidents', 'sla_breach_at')
```

### 4.3 ゼロダウンタイムマイグレーション（v2.0追加）

```python
"""Rename column with zero downtime (3-step approach)

Revision ID: 006_rename_severity_to_impact
Revises: 005_add_impact_analysis
Create Date: 2026-05-01 09:00:00.000000

Note: カラムリネームはゼロダウンタイムのため3ステップで実施
  Step 1: 新カラム追加 + トリガーで双方向同期
  Step 2: アプリケーション側を新カラムに切り替え（別デプロイ）
  Step 3: 旧カラム・トリガー削除（別マイグレーション）
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Step 1: 新カラム追加
    op.add_column('incidents',
        sa.Column('impact', sa.VARCHAR(20), nullable=True)
    )

    # 既存データを新カラムに移行
    op.execute("""
        UPDATE incidents
        SET impact = severity
        WHERE impact IS NULL AND severity IS NOT NULL
    """)

    # 双方向同期トリガー（移行期間中のデータ整合性確保）
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_severity_impact()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
                IF NEW.severity IS DISTINCT FROM NEW.impact THEN
                    NEW.impact := NEW.severity;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_sync_severity_impact
        BEFORE INSERT OR UPDATE ON incidents
        FOR EACH ROW EXECUTE FUNCTION sync_severity_impact();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_sync_severity_impact ON incidents")
    op.execute("DROP FUNCTION IF EXISTS sync_severity_impact()")
    op.drop_column('incidents', 'impact')
```

### 4.4 パーティションテーブルのマイグレーション（v2.0追加）

```python
"""Add new partition for incidents (monthly partition management)

Revision ID: 007_add_incidents_2026_q2_partitions
Revises: 006_rename_severity_to_impact
Create Date: 2026-04-01 00:00:00.000000
"""
from alembic import op


def upgrade() -> None:
    # Q2 2026 月次パーティション作成
    for month_start, month_end in [
        ('2026-04-01', '2026-05-01'),
        ('2026-05-01', '2026-06-01'),
        ('2026-06-01', '2026-07-01'),
    ]:
        year_month = month_start[:7].replace('-', '_')
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS incidents_{year_month}
            PARTITION OF incidents
            FOR VALUES FROM ('{month_start}') TO ('{month_end}')
        """)


def downgrade() -> None:
    for year_month in ['2026_06', '2026_05', '2026_04']:
        op.execute(f"DROP TABLE IF EXISTS incidents_{year_month}")
```

### 4.5 スキーマ変更方針

| 変更種別 | 後方互換性 | 手順 |
|---------|----------|------|
| カラム追加（nullable） | ✅ 互換 | 通常マイグレーション（1ステップ） |
| カラム追加（NOT NULL） | ⚠️ 要注意 | DEFAULT 値設定後、NOT NULL 制約追加（2ステップ） |
| カラム名変更 | ❌ 非互換 | 新カラム追加 → 同期トリガー → アプリ更新 → 旧カラム削除（3ステップ） |
| カラム削除 | ❌ 非互換 | 廃止予告 → アプリ更新 → 削除（3ステップ） |
| テーブル名変更 | ❌ 非互換 | ビュー作成で移行期間設け、段階的移行 |
| データ型変更 | ❌ 非互換 | 新カラム追加 → データ移行 → 旧カラム削除（3ステップ） |
| インデックス追加 | ✅ 互換 | `CREATE INDEX CONCURRENTLY`（本番での排他ロック回避） |
| CHECK 制約追加 | ⚠️ 要注意 | `NOT VALID` → `VALIDATE CONSTRAINT`（2ステップ） |

---

## 5. TypeScript / Pydantic インターフェースバージョニング（v2.0追加）

### 5.1 Pydantic スキーマバージョニング（Python / FastAPI）

```python
# app/schemas/incident/v1.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class IncidentResponseV1(BaseModel):
    """インシデント APIレスポンス スキーマ v1"""
    incident_id: UUID
    incident_number: str
    title: str
    priority: str  # 'P1', 'P2', 'P3', 'P4'
    status: str
    severity: str  # v1: 'critical', 'high', 'medium', 'low'
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# app/schemas/incident/v2.py
class IncidentResponseV2(BaseModel):
    """インシデント APIレスポンス スキーマ v2（severity → impact に変更）"""
    incident_id: UUID
    incident_number: str
    title: str
    priority: str  # 'P1', 'P2', 'P3', 'P4'
    status: str
    impact: str      # v2: severity を impact に変更（破壊的変更）
    affected_cis: list[str] = Field(default_factory=list)  # v2: 新フィールド
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# app/api/v1/incidents.py（v1 エンドポイント）
# app/api/v2/incidents.py（v2 エンドポイント）
```

### 5.2 TypeScript インターフェースバージョニング（Next.js フロントエンド）

```typescript
// types/api/v1/incident.ts
export interface IncidentV1 {
  incident_id: string;
  incident_number: string;
  title: string;
  priority: 'P1' | 'P2' | 'P3' | 'P4';
  status: 'New' | 'Acknowledged' | 'In_Progress' | 'Pending' | 'Resolved' | 'Closed';
  severity: 'critical' | 'high' | 'medium' | 'low';  // v1
  created_at: string;  // ISO 8601
  resolved_at: string | null;
}

// types/api/v2/incident.ts
export interface IncidentV2 {
  incident_id: string;
  incident_number: string;
  title: string;
  priority: 'P1' | 'P2' | 'P3' | 'P4';
  status: 'New' | 'Acknowledged' | 'In_Progress' | 'Pending' | 'Resolved' | 'Closed';
  impact: 'critical' | 'high' | 'medium' | 'low';  // v2: severity → impact
  affected_cis: string[];  // v2: 新フィールド
  created_at: string;
  resolved_at: string | null;
}

// types/api/index.ts - バージョンアダプター
export function adaptV1toV2(v1: IncidentV1): IncidentV2 {
  const { severity, ...rest } = v1;
  return {
    ...rest,
    impact: severity,
    affected_cis: [],
  };
}

// lib/api/client.ts - バージョン対応 API クライアント
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION ?? 'v1';

export async function fetchIncident(id: string): Promise<IncidentV1 | IncidentV2> {
  const res = await fetch(`/api/${API_VERSION}/incidents/${id}`, {
    headers: {
      'Accept': `application/vnd.servicematrix.${API_VERSION}+json`,
    },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

---

## 6. ドキュメントバージョニング

### 6.1 ドキュメントヘッダー

全ドキュメントに以下のヘッダーを記載:

```markdown
# ドキュメントタイトル

Document ID: DOC-XXX
Version: 1.2.0
Status: Draft | Review | Approved | Deprecated
Last Updated: 2026-03-02
Author: 担当者名
Reviewer: レビュア名
Next Review: 2026-09-02
```

### 6.2 ドキュメント改訂プロセス

```
Draft → Review → Approved → (必要に応じて改訂) → Deprecated
                    ↓
           バージョン番号更新
           REVISION_HISTORY.md 更新
           レビュー日付更新（6ヶ月サイクル）
```

---

## 7. GitHub タグとリリース管理

### 7.1 タグ命名規則

```bash
# 正式リリース
git tag v1.0.0 -m "feat: Phase 0完了 - ドキュメント体系確立"
git push origin v1.0.0

# リリース候補
git tag v1.1.0-rc.1 -m "rc: Phase 1 リリース候補1"

# ベータ
git tag v2.0.0-beta.1 -m "beta: API v2 ベータ版"
```

### 7.2 CHANGELOG管理

Keep a Changelog フォーマットに準拠:

```markdown
# Changelog

## [Unreleased]
### Added
- CMDB CI関係管理強化
- AI バイアス検知機能

## [1.1.0] - 2026-06-01
### Added
- SLA 違反リアルタイム通知
- インシデント影響分析 API

### Fixed
- P1 インシデント SLA 計算の夏時間考慮漏れ修正

## [1.0.0] - 2026-03-15
### Added
- 全ドキュメント体系（18カテゴリ）の初版作成
- GitHub Actions CI/CD パイプライン
- PR 統治ワークフロー
```

---

## 8. マイグレーション健全性チェック（v2.0追加）

### 8.1 未適用マイグレーション確認クエリ

```sql
-- alembic_version テーブルで現在の DB バージョンを確認
SELECT version_num AS current_db_revision
FROM alembic_version;

-- マイグレーション履歴の連続性チェック（適用済みリビジョン確認）
-- ※ このクエリは alembic history コマンドと合わせて確認する
SELECT
    version_num,
    'applied' AS status
FROM alembic_version;
```

```bash
# CI/CD での自動チェックコマンド
# 未適用マイグレーションがある場合は exit 1

# 現在の DB リビジョン確認
alembic current

# 未適用マイグレーション一覧
alembic heads --verbose

# マイグレーション履歴ツリー表示
alembic history --verbose

# マイグレーション健全性チェックスクリプト
python -c "
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
import sys

config = Config('alembic.ini')
script = ScriptDirectory.from_config(config)
engine = create_engine(config.get_main_option('sqlalchemy.url'))

with engine.connect() as conn:
    context = MigrationContext.configure(conn)
    current_heads = set(context.get_current_heads())
    expected_heads = set(script.get_heads())

    if current_heads != expected_heads:
        print(f'ERROR: DB heads {current_heads} != expected {expected_heads}', file=sys.stderr)
        sys.exit(1)
    else:
        print(f'OK: DB is up to date at {current_heads}')
"
```

### 8.2 ロールバック手順（緊急時）

```bash
# 直前のリビジョンへロールバック
alembic downgrade -1

# 特定リビジョンへロールバック
alembic downgrade 002_add_incident_sla_fields

# ロールバック前の確認（dry-run SQL 出力）
alembic downgrade -1 --sql > rollback_plan.sql
cat rollback_plan.sql
# 確認後に実行
alembic downgrade -1
```

```python
# ロールバック後の整合性確認スクリプト
# scripts/check_schema_integrity.py

import sqlalchemy as sa
from sqlalchemy import inspect

EXPECTED_COLUMNS = {
    'incidents': [
        'incident_id', 'incident_number', 'title', 'description',
        'priority', 'status', 'severity', 'category',
        'created_by', 'assigned_to', 'team_id',
        'created_at', 'updated_at', 'resolved_at', 'closed_at',
        'sla_breach_at', 'sla_warning_at',
    ],
    'changes': [
        'change_id', 'change_number', 'title', 'description',
        'change_type', 'status', 'priority', 'risk_level',
        'created_by', 'approved_by', 'assigned_to',
        'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end',
        'created_at', 'updated_at',
    ],
}


def check_schema(engine_url: str) -> bool:
    engine = sa.create_engine(engine_url)
    inspector = inspect(engine)
    all_valid = True

    for table_name, expected_cols in EXPECTED_COLUMNS.items():
        actual_cols = {col['name'] for col in inspector.get_columns(table_name)}
        missing = set(expected_cols) - actual_cols
        if missing:
            print(f"ERROR: Table '{table_name}' missing columns: {missing}")
            all_valid = False
        else:
            print(f"OK: Table '{table_name}' schema is valid")

    return all_valid
```

---

## 9. バージョン間互換性マトリックス

| APIバージョン | DB スキーマ | Python 最低バージョン | Next.js | 備考 |
|-------------|-----------|-------------------|---------|------|
| v1.x | 1.x.x | 3.12+ | 15+ | 現行バージョン（2026年） |
| v2.x | 2.x.x | 3.12+ | 16+ | 計画中（2027年Q1予定） |

### 9.1 非互換変更一覧（v1 → v2 予定）

| 変更項目 | v1 の挙動 | v2 の挙動 | 移行手順 |
|---------|----------|----------|---------|
| `incidents.severity` | `VARCHAR(20)` | 廃止→`impact` に統合 | アダプター関数 `adaptV1toV2` 使用 |
| タイムスタンプ形式 | ISO 8601（UTC） | ISO 8601（UTC+JST 明示） | フロントエンド TZ ライブラリ更新 |
| エラーレスポンス | `{"error": "message"}` | `{"code": "...", "message": "...", "details": [...]}` | エラーハンドラー更新 |

---

*最終更新: 2026-03-02*
*バージョン: 2.0.0*
*承認者: アーキテクチャ委員会*
