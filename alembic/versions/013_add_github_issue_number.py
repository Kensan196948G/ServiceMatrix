"""add github_issue_number to incidents

Revision ID: 013
Revises: 012
Create Date: 2026-03-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("github_issue_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "github_issue_number")
