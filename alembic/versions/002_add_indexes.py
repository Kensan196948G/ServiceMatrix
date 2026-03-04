"""Add performance indexes for PostgreSQL

Revision ID: 002
Revises: 001
Create Date: 2026-03-04
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 監査ログ: actionインデックス（検索・フィルタ用）
    # ※ sequence_number, created_at は001で作成済み
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # 問題管理: ステータス・優先度インデックス
    op.create_index("ix_problems_status", "problems", ["status"])
    op.create_index("ix_problems_priority", "problems", ["priority"])

    # 変更管理: change_type インデックス
    op.create_index("ix_changes_change_type", "changes", ["change_type"])

    # サービスリクエスト: ステータスインデックス
    op.create_index("ix_service_requests_status", "service_requests", ["status"])

    # CMDB: ci_type インデックス
    op.create_index("ix_ci_type", "configuration_items", ["ci_type"])


def downgrade() -> None:
    op.drop_index("ix_ci_type", "configuration_items")
    op.drop_index("ix_service_requests_status", "service_requests")
    op.drop_index("ix_changes_change_type", "changes")
    op.drop_index("ix_problems_priority", "problems")
    op.drop_index("ix_problems_status", "problems")
    op.drop_index("ix_audit_logs_action", "audit_logs")
