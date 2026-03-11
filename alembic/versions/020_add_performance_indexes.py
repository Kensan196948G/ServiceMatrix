"""パフォーマンス最適化インデックス追加

Revision ID: 020
Revises: 019
Create Date: 2026-03-11

よく使われるクエリパターンに対してインデックスを追加。
- incidents: status/priority/created_at/assigned_to
- changes: status/scheduled_at
- problems: status/priority
- audit_logs: entity_type+entity_id（監査ログ検索高速化）
"""

from __future__ import annotations

from alembic import op

# revision identifiers
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── incidents テーブル ────────────────────────────────────────────────────
    # ステータス+優先度フィルタ（一覧API最頻出クエリ）
    op.create_index(
        "idx_incidents_status_priority",
        "incidents",
        ["status", "priority"],
        postgresql_concurrently=False,
    )
    # 担当者ID+作成日時（担当者別インシデント一覧）
    op.create_index(
        "idx_incidents_assigned_created",
        "incidents",
        ["assigned_to", "created_at"],
        postgresql_concurrently=False,
    )
    # SLA超過フラグ（SLA違反一覧高速化）
    op.create_index(
        "idx_incidents_sla_breached",
        "incidents",
        ["sla_breached"],
        postgresql_where="sla_breached = TRUE",
        postgresql_concurrently=False,
    )

    # ── changes テーブル ──────────────────────────────────────────────────────
    # ステータス+スケジュール日時（変更管理カレンダー）
    op.create_index(
        "idx_changes_status_scheduled",
        "changes",
        ["status", "scheduled_at"],
        postgresql_concurrently=False,
    )

    # ── problems テーブル ─────────────────────────────────────────────────────
    # ステータス+優先度（問題一覧フィルタ）
    op.create_index(
        "idx_problems_status_priority",
        "problems",
        ["status", "priority"],
        postgresql_concurrently=False,
    )

    # ── audit_logs テーブル ───────────────────────────────────────────────────
    # エンティティ種別+ID（監査ログ検索: 特定インシデントの操作履歴）
    op.create_index(
        "idx_audit_logs_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
        postgresql_concurrently=False,
    )
    # 作成日時（監査ログの時系列検索）
    op.create_index(
        "idx_audit_logs_created_at",
        "audit_logs",
        ["created_at"],
        postgresql_concurrently=False,
    )


def downgrade() -> None:
    op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("idx_audit_logs_entity", table_name="audit_logs")
    op.drop_index("idx_problems_status_priority", table_name="problems")
    op.drop_index("idx_changes_status_scheduled", table_name="changes")
    op.drop_index("idx_incidents_sla_breached", table_name="incidents")
    op.drop_index("idx_incidents_assigned_created", table_name="incidents")
    op.drop_index("idx_incidents_status_priority", table_name="incidents")
