"""サービスリクエスト管理モデル"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class ServiceRequest(Base, TimestampMixin):
    """サービスリクエストテーブル"""

    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'New','Pending_Approval','Approved','In_Progress','Fulfilled','Rejected','Cancelled'"
            ")",
            name="chk_sr_status",
        ),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="New")
    request_type: Mapped[str | None] = mapped_column(String(100))

    # 担当者
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )

    # スケジュール
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
