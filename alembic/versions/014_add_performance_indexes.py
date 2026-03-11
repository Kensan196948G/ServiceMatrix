"""add performance indexes for incidents, changes, problems

Revision ID: 014_add_performance_indexes
Revises: 013
Create Date: 2026-03-11

"""

from collections.abc import Sequence

from alembic import op

revision: str = "014_add_performance_indexes"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # incidents テーブル: 単一カラムインデックス
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_priority", "incidents", ["priority"])
    op.create_index(
        "ix_incidents_created_at_desc",
        "incidents",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    # incidents テーブル: 複合インデックス
    op.create_index("ix_incidents_status_priority", "incidents", ["status", "priority"])

    # changes テーブル
    op.create_index("ix_changes_status", "changes", ["status"])
    op.create_index("ix_changes_change_type", "changes", ["change_type"])
    op.create_index(
        "ix_changes_created_at_desc",
        "changes",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    # problems テーブル
    op.create_index("ix_problems_status", "problems", ["status"])
    op.create_index("ix_problems_priority", "problems", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_problems_priority", table_name="problems")
    op.drop_index("ix_problems_status", table_name="problems")

    op.drop_index("ix_changes_created_at_desc", table_name="changes")
    op.drop_index("ix_changes_change_type", table_name="changes")
    op.drop_index("ix_changes_status", table_name="changes")

    op.drop_index("ix_incidents_status_priority", table_name="incidents")
    op.drop_index("ix_incidents_created_at_desc", table_name="incidents")
    op.drop_index("ix_incidents_priority", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
