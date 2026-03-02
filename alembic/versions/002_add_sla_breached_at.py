"""SLA違反日時カラム追加

Revision ID: 002
Revises: 001
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # incidents テーブルに sla_breached_at カラム追加
    op.add_column('incidents', sa.Column('sla_breached_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('incidents', 'sla_breached_at')
