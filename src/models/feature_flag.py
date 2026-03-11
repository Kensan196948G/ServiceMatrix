"""Feature Flag モデル - Issue #90, Phase 9-DEPLOY-1"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class FeatureFlag(Base):
    """Feature Flag（機能フラグ）モデル。

    カナリアリリース・A/Bテスト・テナント限定有効化に使用する。

    Attributes:
        flag_id: 主キー（UUID）
        name: フラグ識別名（スラッグ形式、一意）
        description: フラグの説明
        is_enabled: グローバル有効フラグ（False なら全員無効）
        rollout_percentage: 有効にするユーザー割合（0.0〜100.0）
        tenant_id: 特定テナント限定の場合に設定（null = 全テナント）
        metadata_json: 追加設定（JSON文字列）
        created_at: 作成日時
        updated_at: 更新日時
    """

    __tablename__ = "feature_flags"

    flag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    rollout_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
        comment="有効にするユーザー割合 0.0〜100.0",
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
        comment="特定テナント限定。null は全テナント対象",
    )
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    # 監査用: 最後に変更したユーザーID
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<FeatureFlag name={self.name!r} "
            f"enabled={self.is_enabled} "
            f"rollout={self.rollout_percentage}%>"
        )
