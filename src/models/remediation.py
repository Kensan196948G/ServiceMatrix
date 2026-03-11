"""AI自動リメディエーション モデル"""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class RemediationStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"
    DRY_RUN = "dry_run"


class RemediationActionType(enum.StrEnum):
    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    FAILOVER = "failover"
    CLEAR_CACHE = "clear_cache"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    NOTIFY_ONCALL = "notify_oncall"
    RUN_PLAYBOOK = "run_playbook"
    CUSTOM = "custom"


class RemediationRule(Base, TimestampMixin):
    """リメディエーションルール - 条件マッチング定義"""

    __tablename__ = "remediation_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # マッチング条件
    match_priority: Mapped[str | None] = mapped_column(String(10), nullable=True)  # P1,P2 etc
    match_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    match_keyword: Mapped[str | None] = mapped_column(String(200), nullable=True)  # titleキーワード
    min_anomaly_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # アクション定義
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    playbook_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 安全設定
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_executions_per_hour: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class RemediationLog(Base, TimestampMixin):
    """リメディエーション実行ログ - 監査証跡"""

    __tablename__ = "remediation_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # 関連エンティティ
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.incident_id", ondelete="SET NULL"),
        nullable=True,
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("remediation_rules.rule_id", ondelete="SET NULL"),
        nullable=True,
    )

    # 実行内容
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(
        String(30), default=RemediationStatus.PENDING, nullable=False
    )
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 実行結果
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    result_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # タイムスタンプ
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 承認フロー
    approved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rollback_log_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
