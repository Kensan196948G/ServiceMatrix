"""外部統合設定モデル（Jira/ServiceNow/カスタム）"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class IntegrationConfig(Base, TimestampMixin):
    """外部統合設定テーブル"""

    __tablename__ = "integration_configs"

    config_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    integration_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "jira", "servicenow", "custom"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500))
    api_key: Mapped[str | None] = mapped_column(String(500))
    username: Mapped[str | None] = mapped_column(String(200))
    webhook_secret: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config_json: Mapped[str | None] = mapped_column(Text)  # JSON形式の追加設定
