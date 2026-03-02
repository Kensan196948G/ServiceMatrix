"""変更管理モデル（月次パーティション対応）"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class ChangeType(enum.StrEnum):
    STANDARD = "Standard"
    NORMAL = "Normal"
    EMERGENCY = "Emergency"
    MAJOR = "Major"


class ChangeStatus(enum.StrEnum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    CAB_REVIEW = "CAB_Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In_Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"


class Change(Base, TimestampMixin):
    """変更管理テーブル - CAB承認フロー対応"""
    __tablename__ = "changes"
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('Standard','Normal','Emergency','Major')",
            name="chk_change_type"
        ),
        CheckConstraint(
            "status IN ('Draft','Submitted','CAB_Review','Approved','Rejected',"
            "'Scheduled','In_Progress','Completed','Cancelled','Failed')",
            name="chk_change_status"
        ),
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="chk_change_risk_score"
        ),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    change_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    change_number: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False, default="Normal")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Draft")

    # リスク評価
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str | None] = mapped_column(String(20))  # Low/Medium/High/Critical
    impact_level: Mapped[str | None] = mapped_column(String(20))  # Low/Medium/High
    urgency_level: Mapped[str | None] = mapped_column(String(20))  # Low/Medium/High

    # 担当者
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    cab_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )

    # スケジュール
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cab_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 実施内容
    implementation_plan: Mapped[str | None] = mapped_column(Text)
    rollback_plan: Mapped[str | None] = mapped_column(Text)
    test_plan: Mapped[str | None] = mapped_column(Text)
    cab_notes: Mapped[str | None] = mapped_column(Text)

    # リレーション
    requester: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[requested_by], lazy="select"
    )
    assignee: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[assigned_to], lazy="select"
    )
    cab_approver: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[cab_approved_by], lazy="select"
    )
