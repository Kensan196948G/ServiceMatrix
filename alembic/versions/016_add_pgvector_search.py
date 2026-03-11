"""Add pgvector extension and embedding columns

Revision ID: 016_add_pgvector_search
Revises: 014_add_performance_indexes
Create Date: 2026-03-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016_add_pgvector_search"
down_revision: str | None = "014_add_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector 拡張を有効化（PostgreSQL のみ）
    # SQLite では無視される
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.add_column(
            "incidents",
            sa.Column(
                "embedding",
                sa.Text,
                nullable=True,
                comment="pgvector embedding JSON",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_column("incidents", "embedding")
