"""add Closed status to changes

Revision ID: 006
Revises: 005
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE changes DROP CONSTRAINT IF EXISTS chk_change_status")
    op.execute(
        "ALTER TABLE changes ADD CONSTRAINT chk_change_status "
        "CHECK (status IN ('Draft','Submitted','CAB_Review','Approved','Rejected',"
        "'Scheduled','In_Progress','Completed','Closed','Cancelled','Failed'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE changes DROP CONSTRAINT IF EXISTS chk_change_status")
    op.execute(
        "ALTER TABLE changes ADD CONSTRAINT chk_change_status "
        "CHECK (status IN ('Draft','Submitted','CAB_Review','Approved','Rejected',"
        "'Scheduled','In_Progress','Completed','Cancelled','Failed'))"
    )
