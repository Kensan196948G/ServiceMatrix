"""サービスリクエスト管理モデル"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class ServiceRequest(Base, TimestampMixin):
    """サービスリクエストテーブル"""

    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'New','Pending_Approval','Approved','In_Progress','In_Fulfillment',"
            "'Fulfilled','Failed','Rejected','Cancelled','Closed'"
            ")",
            name="chk_sr_status",
        ),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="New")
    request_type: Mapped[str | None] = mapped_column(String(100))

    # 担当者
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )

    # スケジュール
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # サービスカタログ参照
    catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_catalog.catalog_id"), nullable=True
    )

    # リレーション
    requester: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[requested_by], lazy="select"
    )
    assignee: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[assigned_to], lazy="select"
    )
    approver: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[approved_by], lazy="select"
    )
