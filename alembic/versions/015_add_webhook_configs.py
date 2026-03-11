"""add webhook_configs table for Slack/Teams outgoing notification webhooks

Revision ID: 015_add_webhook_configs
Revises: 014_add_performance_indexes
Create Date: 2026-03-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015_add_webhook_configs"
down_revision: str | None = "014_add_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "webhook_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("webhook_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("event_filters", sa.JSON(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_configs_webhook_type", "webhook_configs", ["webhook_type"])
    op.create_index("ix_webhook_configs_is_active", "webhook_configs", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_webhook_configs_is_active", table_name="webhook_configs")
    op.drop_index("ix_webhook_configs_webhook_type", table_name="webhook_configs")
    op.drop_table("webhook_configs")
