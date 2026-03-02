"""問題管理モデル"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Problem(Base, TimestampMixin):
    """問題管理テーブル - Known Error DB対応"""
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint(
            "status IN ('New','Under_Investigation','Known_Error','Resolved','Closed')",
            name="chk_problem_status"
        ),
    )

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_number: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="New")
    priority: Mapped[str] = mapped_column(String(5), nullable=False, default="P3")

    # Known Error DB
    known_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    workaround: Mapped[str | None] = mapped_column(Text)  # known_error=trueなら必須（アプリ層で検証）

    # 担当者
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )

    # タイムスタンプ
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignee: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_to], lazy="select"
    )
