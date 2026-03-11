"""Feature Flag テーブル追加

Revision ID: 021
Revises: 020
Create Date: 2026-03-11

新機能フラグ管理テーブルを追加。
カナリアリリース・A/Bテスト・テナント別機能制御に使用。
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("flag_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "rollout_percentage",
            sa.Float(),
            nullable=False,
            default=100.0,
            comment="有効にするユーザー割合 0.0〜100.0",
        ),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            nullable=True,
            comment="特定テナント限定。null は全テナント対象",
        ),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by", sa.String(255), nullable=True),
    )
    op.create_index("idx_feature_flags_name", "feature_flags", ["name"])
    op.create_index("idx_feature_flags_tenant_id", "feature_flags", ["tenant_id"])
    op.create_index(
        "idx_feature_flags_enabled",
        "feature_flags",
        ["is_enabled"],
    )


def downgrade() -> None:
    op.drop_index("idx_feature_flags_enabled", table_name="feature_flags")
    op.drop_index("idx_feature_flags_tenant_id", table_name="feature_flags")
    op.drop_index("idx_feature_flags_name", table_name="feature_flags")
    op.drop_table("feature_flags")
