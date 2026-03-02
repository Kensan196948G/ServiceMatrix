"""監査ログモデル（J-SOX SHA-256ハッシュチェーン対応）"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class AuditLog(Base):
    """監査ログテーブル - J-SOX準拠SHA-256ハッシュチェーン"""
    __tablename__ = "audit_logs"
    __table_args__ = (
        # 月次パーティション設定
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # アクター情報
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    username: Mapped[str | None] = mapped_column(String(50))  # 削除時の参照保持
    user_role: Mapped[str | None] = mapped_column(String(50))

    # アクション
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100))

    # リクエスト情報
    http_method: Mapped[str | None] = mapped_column(String(10))
    request_path: Mapped[str | None] = mapped_column(String(500))
    request_body: Mapped[dict | None] = mapped_column(JSONB)
    response_status: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))

    # 変更差分
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)

    # J-SOX SHA-256ハッシュチェーン
    prev_log_hash: Mapped[str | None] = mapped_column(String(64))
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    actor: Mapped["User | None"] = relationship(
        "User", foreign_keys=[user_id], lazy="select"
    )


class AIAuditLog(Base):
    """AI判断ログテーブル - AI自律行動の完全トレーサビリティ"""
    __tablename__ = "ai_audit_logs"
    __table_args__ = (
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    ai_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # AIエージェント情報
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str | None] = mapped_column(String(50))
    autonomy_level: Mapped[str | None] = mapped_column(String(5))  # L0-L3

    # 判断内容
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False)
    decision_input: Mapped[dict | None] = mapped_column(JSONB)
    decision_output: Mapped[dict | None] = mapped_column(JSONB)
    confidence_score: Mapped[float | None] = mapped_column()

    # 人間承認
    human_approved: Mapped[bool | None] = mapped_column()
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    approval_notes: Mapped[str | None] = mapped_column(Text)

    # 整合性ハッシュ
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class AuditLogIntegrity(Base):
    """監査ログ整合性検証テーブル - ハッシュチェーン検証記録"""
    __tablename__ = "audit_log_integrity"

    integrity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    start_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    end_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    is_valid: Mapped[bool] = mapped_column(nullable=False)
    broken_at_sequence: Mapped[int | None] = mapped_column(Integer)
    verification_notes: Mapped[str | None] = mapped_column(Text)
