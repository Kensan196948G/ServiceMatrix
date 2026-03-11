"""カスタムダッシュボード・ウィジェット モデル"""

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class WidgetType(enum.StrEnum):
    INCIDENT_COUNT = "incident_count"
    MTTR_TREND = "mttr_trend"
    SLA_GAUGE = "sla_gauge"
    CMDB_MAP = "cmdb_map"
    AI_ANOMALY_HEATMAP = "ai_anomaly_heatmap"
    ACTIVITY_TIMELINE = "activity_timeline"
    CHANGE_COUNT = "change_count"
    KPI_CARD = "kpi_card"


class Dashboard(Base, TimestampMixin):
    """カスタムダッシュボード"""

    __tablename__ = "dashboards"

    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    # react-grid-layout 形式のレイアウト JSON [{i, x, y, w, h}, ...]
    layout_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    widgets: Mapped[list["DashboardWidget"]] = relationship(
        "DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan"
    )


class DashboardWidget(Base, TimestampMixin):
    """ダッシュボードウィジェット"""

    __tablename__ = "dashboard_widgets"

    widget_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dashboards.dashboard_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # ウィジェット固有設定 JSON （フィルタ・表示期間・閾値など）
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # グリッド位置 {"x": 0, "y": 0, "w": 4, "h": 3}
    position_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="widgets")
