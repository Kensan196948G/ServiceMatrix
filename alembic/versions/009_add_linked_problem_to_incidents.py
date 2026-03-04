"""add linked_problem_id to incidents

Revision ID: 008
Revises: 007
Create Date: 2025-01-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("linked_problem_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_incidents_linked_problem",
        "incidents",
        "problems",
        ["linked_problem_id"],
        ["problem_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_incidents_linked_problem", "incidents", type_="foreignkey")
    op.drop_column("incidents", "linked_problem_id")
