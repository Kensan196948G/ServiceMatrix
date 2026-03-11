"""Slack/Teams Webhook設定モデル"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class WebhookConfig(Base):
    """Slack/Teams 送信Webhook設定テーブル"""

    __tablename__ = "webhook_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    webhook_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "slack" | "teams"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    event_filters: Mapped[dict] = mapped_column(
        JSON, default=dict
    )  # {"priorities": ["P1", "P2"], "events": ["create", "update"]}
    retry_count: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
