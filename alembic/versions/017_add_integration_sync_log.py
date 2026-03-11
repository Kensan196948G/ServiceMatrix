"""add integration sync log

Revision ID: 017
Revises: 016
Create Date: 2026-03-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: str | None = "014_add_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """同期ログテーブルを追加"""
    op.create_table(
        "integration_sync_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("config_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("incident_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("direction", sa.String(20), nullable=True),  # 'inbound' | 'outbound'
        sa.Column("status", sa.String(20), nullable=True),    # 'success' | 'failed' | 'pending'
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_integration_sync_logs_config_id",
        "integration_sync_logs",
        ["config_id"],
    )
    op.create_index(
        "ix_integration_sync_logs_incident_id",
        "integration_sync_logs",
        ["incident_id"],
    )
    op.create_index(
        "ix_integration_sync_logs_status",
        "integration_sync_logs",
        ["status"],
    )


def downgrade() -> None:
    """同期ログテーブルを削除"""
    op.drop_index("ix_integration_sync_logs_status", table_name="integration_sync_logs")
    op.drop_index("ix_integration_sync_logs_incident_id", table_name="integration_sync_logs")
    op.drop_index("ix_integration_sync_logs_config_id", table_name="integration_sync_logs")
    op.drop_table("integration_sync_logs")
