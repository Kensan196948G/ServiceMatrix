"""通知設定モデル"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if True:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from src.models.user import User


class NotificationSettings(Base):
    """ユーザーごとの通知設定"""

    __tablename__ = "notification_settings"

    settings_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # JSON文字列として格納（例: {"email": true, "sla_breach": true, ...}）
    settings_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='{"email":true,"sla_breach":true,"incident_created":true,"change_approved":false,"sr_completed":false}',
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user: Mapped["User"] = relationship("User")
