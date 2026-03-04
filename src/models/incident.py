"""インシデント管理モデル（月次パーティション対応）"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class IncidentPriority(enum.StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentStatus(enum.StrEnum):
    NEW = "New"
    ACKNOWLEDGED = "Acknowledged"
    IN_PROGRESS = "In_Progress"
    PENDING = "Pending"
    WORKAROUND_APPLIED = "Workaround_Applied"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class Incident(Base, TimestampMixin):
    """インシデントテーブル - PostgreSQL月次パーティションにより大量データに対応"""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("priority IN ('P1','P2','P3','P4')", name="chk_incident_priority"),
        CheckConstraint(
            "status IN ('New','Acknowledged','In_Progress','Pending',"
            "'Workaround_Applied','Resolved','Closed')",
            name="chk_incident_status",
        ),
        CheckConstraint(
            "acknowledged_at IS NULL OR acknowledged_at >= created_at",
            name="chk_incident_acknowledged_at",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR closed_at IS NULL OR closed_at >= resolved_at",
            name="chk_incident_closed_at",
        ),
        # 月次パーティション設定（PostgreSQL PARTITION BY RANGE）
        # 実際のパーティション作成はAlembicマイグレーションで行う
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incident_number: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(5), nullable=False, default="P3")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="New")

    # 担当者・チーム
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.team_id"), nullable=True
    )
    reported_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )

    # SLAタイムスタンプ
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_resolution_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(default=False, nullable=False)
    sla_breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # カテゴリー・タグ
    category: Mapped[str | None] = mapped_column(String(100))
    subcategory: Mapped[str | None] = mapped_column(String(100))
    affected_service: Mapped[str | None] = mapped_column(String(200))
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    ai_triage_notes: Mapped[str | None] = mapped_column(Text)

    # リレーション
    assignee: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[assigned_to], lazy="select"
    )
    assigned_team: Mapped["Team | None"] = relationship(  # noqa: F821
        "Team", foreign_keys=[assigned_team_id], lazy="select"
    )
    reporter: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[reported_by], lazy="select"
    )
