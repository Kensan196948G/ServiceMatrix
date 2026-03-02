# バージョニングポリシー

VERSIONING_POLICY.md
Version: 1.0
Category: Data Model
Compliance: ITIL 4 / ISO 20000

---

## 1. 目的

本ドキュメントは、ServiceMatrixにおけるバージョニング戦略を定義する。
ソフトウェア・API・データスキーマ・ドキュメントの各バージョン管理を統一し、
後方互換性・移行管理・変更追跡を確実に行うことを目的とする。

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
```

### 2.2 バージョン番号変更ルール

| バージョン | 変更条件 | 例 |
|----------|---------|---|
| **MAJOR** | 後方互換性のない変更（破壊的変更）| APIエンドポイント削除・スキーマ変更 |
| **MINOR** | 後方互換な機能追加 | 新エンドポイント追加・新フィールド追加 |
| **PATCH** | 後方互換なバグ修正 | バグ修正・パフォーマンス改善 |

### 2.3 Conventional Commits との連携

```
# MAJOR バージョンアップ
feat!: APIレスポンス形式を変更
# フッターに BREAKING CHANGE を含む場合もMAJOR

# MINOR バージョンアップ
feat: インシデントフィルタリング機能を追加

# PATCH バージョンアップ
fix: SLA計算の日付ゾーン誤りを修正
perf: クエリ最適化でレスポンスタイム改善
docs: APIドキュメントを更新
```

---

## 3. APIバージョニング

### 3.1 URLパス方式

```
# バージョン管理方式: URLパスに埋め込む
/api/v1/incidents          # v1 API
/api/v2/incidents          # v2 API（破壊的変更後）

# ベースURL構成
https://{host}/api/v{major}/
```

### 3.2 バージョンライフサイクル

```
Current (現行) → Deprecated (廃止予告) → Sunset (終了)
                     ↑
              廃止予告期間: 最低3ヶ月
```

| バージョン状態 | 内容 |
|-------------|------|
| `current` | 現在推奨バージョン。フル機能・サポート対象 |
| `supported` | まだサポート中だが更新版あり |
| `deprecated` | 廃止予告済み（3ヶ月後に`sunset`） |
| `sunset` | サービス終了。404レスポンス返却 |

### 3.3 廃止予告（Deprecation Notice）

廃止予告時のレスポンスヘッダー:

```http
HTTP/1.1 200 OK
Deprecation: 2026-09-01
Sunset: 2026-12-01
Link: <https://api.servicematrix.example.com/api/v2/incidents>; rel="successor-version"
Warning: 299 - "This API version is deprecated. Migrate to v2 by 2026-12-01."
```

廃止予告時の通知方法:
- GitHub Releases でのアナウンス
- APIレスポンスヘッダーへの埋め込み
- ドキュメントへの明記

---

## 4. データスキーマバージョニング

### 4.1 Alembicによるマイグレーション管理

```
alembic/
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_incident_sla_fields.py
    ├── 003_add_ai_audit_logs.py
    └── ...
```

```python
# マイグレーションファイル例
"""Add SLA breach timestamp to incidents

Revision ID: 002_add_incident_sla_fields
Revises: 001_initial_schema
Create Date: 2026-04-01 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('incidents',
        sa.Column('sla_breach_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('incidents',
        sa.Column('sla_warning_at', sa.DateTime(timezone=True), nullable=True)
    )

def downgrade():
    op.drop_column('incidents', 'sla_breach_at')
    op.drop_column('incidents', 'sla_warning_at')
```

### 4.2 スキーマ変更方針

| 変更種別 | 後方互換性 | 手順 |
|---------|----------|------|
| カラム追加（nullable） | ✅ 互換 | 通常マイグレーション |
| カラム追加（NOT NULL） | ⚠️ 要注意 | デフォルト値設定必須 |
| カラム削除 | ❌ 非互換 | 廃止予告→アプリ更新→削除の3ステップ |
| テーブル名変更 | ❌ 非互換 | ビュー作成で移行期間設ける |
| データ型変更 | ❌ 非互換 | 新カラム追加→データ移行→旧カラム削除 |

---

## 5. ドキュメントバージョニング

### 5.1 ドキュメントヘッダー

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

### 5.2 ドキュメント改訂プロセス

```
Draft → Review → Approved → (必要に応じて改訂) → Deprecated
                    ↓
           バージョン番号更新
           REVISION_HISTORY.md 更新
           レビュー日付更新（6ヶ月サイクル）
```

---

## 6. GitHub タグとリリース管理

### 6.1 タグ命名規則

```bash
# 正式リリース
git tag v1.0.0 -m "feat: Phase 0完了 - ドキュメント体系確立"

# リリース候補
git tag v1.1.0-rc.1

# ベータ
git tag v2.0.0-beta.1
```

### 6.2 CHANGELOG管理

Keep a Changelog フォーマットに準拠:

```markdown
# Changelog

## [Unreleased]
### Added
- xxx

## [1.0.0] - 2026-03-15
### Added
- 全ドキュメント体系（18カテゴリ）の初版作成
- GitHub Actions CI/CD パイプライン
- PR統治ワークフロー
```

---

## 7. バージョン間互換性マトリックス

| APIバージョン | DB スキーマ | Python 最低バージョン | 備考 |
|-------------|-----------|-------------------|------|
| v1.x | 1.x.x | 3.12+ | 現行バージョン |
| v2.x | 2.x.x | 3.12+ | 計画中（2027年） |

---

*最終更新: 2026-03-02*
*バージョン: 1.0.0*
*承認者: アーキテクチャ委員会*
