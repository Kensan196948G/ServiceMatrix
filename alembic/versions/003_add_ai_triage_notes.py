"""Add ai_triage_notes to incidents

Revision ID: 003
Revises: 002
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("ai_triage_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "ai_triage_notes")
