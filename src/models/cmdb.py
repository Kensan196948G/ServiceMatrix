"""CMDB（構成管理データベース）モデル"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class ConfigurationItem(Base, TimestampMixin):
    """構成アイテム（CI）テーブル"""

    __tablename__ = "configuration_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Active','Inactive','Maintenance','Retired')", name="chk_ci_status"
        ),
    )

    ci_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ci_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    ci_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ci_class: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Active")
    version: Mapped[str | None] = mapped_column(String(50))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict | None] = mapped_column(JSON)

    owner: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[owner_id], lazy="select"
    )
    outgoing_relationships: Mapped[list["CIRelationship"]] = relationship(
        "CIRelationship", foreign_keys="CIRelationship.source_ci_id", lazy="select"
    )
    incoming_relationships: Mapped[list["CIRelationship"]] = relationship(
        "CIRelationship", foreign_keys="CIRelationship.target_ci_id", lazy="select"
    )


class CIRelationship(Base, TimestampMixin):
    """CI間の依存関係テーブル"""

    __tablename__ = "ci_relationships"

    relationship_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_ci_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("configuration_items.ci_id"), nullable=False
    )
    target_ci_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("configuration_items.ci_id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    source_ci: Mapped["ConfigurationItem"] = relationship(
        "ConfigurationItem",
        foreign_keys=[source_ci_id],
        lazy="select",
        overlaps="outgoing_relationships",
    )
    target_ci: Mapped["ConfigurationItem"] = relationship(
        "ConfigurationItem",
        foreign_keys=[target_ci_id],
        lazy="select",
        overlaps="incoming_relationships",
    )
