"""add notification_settings table

Revision ID: 005
Revises: 004
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column(
            "settings_id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "settings_json",
            sa.Text,
            nullable=False,
            server_default=(
                '{"email":true,"sla_breach":true,"incident_created":true,'
                '"change_approved":false,"sr_completed":false}'
            ),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_notification_settings_user_id",
        "notification_settings",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_settings_user_id", table_name="notification_settings")
    op.drop_table("notification_settings")
