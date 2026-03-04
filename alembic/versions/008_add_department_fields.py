"""add department fields to incidents and configuration_items

Revision ID: 008
Revises: 007
Create Date: 2025-01-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("department", sa.String(100), nullable=True),
    )
    op.add_column(
        "configuration_items",
        sa.Column("department", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("incidents", "department")
    op.drop_column("configuration_items", "department")
