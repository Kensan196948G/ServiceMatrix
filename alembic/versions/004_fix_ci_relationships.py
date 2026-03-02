"""Fix CIRelationship overlaps - no schema change needed

Revision ID: 004
Revises: 003
Create Date: 2026-03-02
"""
# このマイグレーションはSQLAlchemyのoverlaps警告対応のため、
# スキーマ変更なし（alembicのリビジョンチェーンを維持するためのプレースホルダ）

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass  # スキーマ変更なし - SQLAlchemy relationship設定のみの変更


def downgrade() -> None:
    pass
