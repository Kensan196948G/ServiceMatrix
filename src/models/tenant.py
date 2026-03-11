"""テナントモデル - Issue #75 マルチテナント基盤"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class TenantPlan(StrEnum):
    FREE = "free"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"


class Tenant(Base):
    """テナント（組織）モデル。

    SaaS型マルチテナント基盤のルートエンティティ。
    各テナントは独立した組織を表し、データは tenant_id で分離される。
    """

    __tablename__ = "tenants"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default=TenantPlan.FREE)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
