"""add sso_providers table - Issue #76 SSO/SAML認証統合

Revision ID: 019
Revises: 018
Create Date: 2026-03-11 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sso_providers",
        sa.Column("provider_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("oidc_client_id", sa.String(255), nullable=True),
        sa.Column("oidc_client_secret", sa.String(512), nullable=True),
        sa.Column("oidc_discovery_url", sa.String(1024), nullable=True),
        sa.Column("saml_idp_metadata_url", sa.String(1024), nullable=True),
        sa.Column("saml_idp_entity_id", sa.String(1024), nullable=True),
        sa.Column("saml_idp_sso_url", sa.String(1024), nullable=True),
        sa.Column("saml_idp_certificate", sa.Text, nullable=True),
        sa.Column("group_role_mapping_json", sa.Text, nullable=True),
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
    )
    op.create_index("ix_sso_providers_name", "sso_providers", ["name"])
    op.create_index("ix_sso_providers_type", "sso_providers", ["provider_type"])


def downgrade() -> None:
    op.drop_index("ix_sso_providers_type", table_name="sso_providers")
    op.drop_index("ix_sso_providers_name", table_name="sso_providers")
    op.drop_table("sso_providers")
