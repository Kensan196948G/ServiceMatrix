"""Web Push サブスクリプション モデル"""

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class PushSubscription(Base, TimestampMixin):
    """Web Push サブスクリプション

    ブラウザから受け取った Push エンドポイント情報を永続化する。
    VAPID 認証付き Web Push (RFC 8292) で利用する。
    """

    __tablename__ = "push_subscriptions"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    # ブラウザが発行する Push エンドポイント URL
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # ECDH 公開鍵 (base64url)
    p256dh: Mapped[str] = mapped_column(String(200), nullable=False)
    # 認証シークレット (base64url)
    auth: Mapped[str] = mapped_column(String(50), nullable=False)
    # デバイス識別用ラベル (任意)
    device_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
