"""SSO プロバイダーモデル - Issue #76 SSO/SAML認証統合"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class SSOProvider(Base):
    """SSO プロバイダー設定モデル。

    Okta / Azure AD などの外部 IdP 設定を保存する。
    プロバイダータイプは "saml" または "oidc"。
    """

    __tablename__ = "sso_providers"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "saml" | "oidc"
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # OIDC 設定
    oidc_client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oidc_client_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oidc_discovery_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # SAML 設定
    saml_idp_metadata_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    saml_idp_entity_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    saml_idp_sso_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    saml_idp_certificate: Mapped[str | None] = mapped_column(Text, nullable=True)

    # グループ→ロールマッピング（JSON文字列）
    # 例: '{"Admins": "system_admin", "Operators": "operator"}'
    group_role_mapping_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
