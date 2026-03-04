"""インシデント管理ビジネスロジック - SLAタイマー・優先度・ステータス遷移"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.metrics import metrics
from src.models.incident import Incident

logger = get_logger(__name__)

# SLAタイマー定義（分単位）
SLA_CONFIG: dict[str, dict[str, int]] = {
    "P1": {"response_minutes": 15, "resolution_minutes": 60},
    "P2": {"response_minutes": 30, "resolution_minutes": 240},
    "P3": {"response_minutes": 120, "resolution_minutes": 1440},
    "P4": {"response_minutes": 480, "resolution_minutes": 4320},
}

# 有効なステータス遷移定義
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "New": {"Acknowledged", "In_Progress"},
    "Acknowledged": {"In_Progress", "Pending"},
    "In_Progress": {"Pending", "Workaround_Applied", "Resolved"},
    "Pending": {"In_Progress", "Workaround_Applied"},
    "Workaround_Applied": {"Resolved", "In_Progress"},
    "Resolved": {"Closed", "In_Progress"},
    "Closed": set(),
}

YEAR_SEQUENCE_PATTERN = re.compile(r"INC-(\d{4})-(\d+)")


async def _get_next_incident_number(db: AsyncSession) -> str:
    """INC-YYYY-NNNNNN形式のインシデント番号を生成"""
    year = datetime.now(UTC).year
    result = await db.execute(select(func.nextval("incident_seq")))
    seq = result.scalar_one()
    return f"INC-{year}-{seq:06d}"


def _calculate_sla_deadlines(priority: str, created_at: datetime) -> dict[str, datetime]:
    """SLA期限を計算する"""
    config = SLA_CONFIG.get(priority, SLA_CONFIG["P4"])
    return {
        "sla_response_due_at": created_at + timedelta(minutes=config["response_minutes"]),
        "sla_resolution_due_at": created_at + timedelta(minutes=config["resolution_minutes"]),
    }


async def create_incident(db: AsyncSession, data: dict[str, Any]) -> Incident:
    """インシデントを作成し、SLAタイマーを設定する"""
    created_at = datetime.now(UTC)
    incident_number = await _get_next_incident_number(db)
    sla_deadlines = _calculate_sla_deadlines(data.get("priority", "P4"), created_at)

    incident = Incident(
        incident_number=incident_number,
        created_at=created_at,
        **{k: v for k, v in data.items() if k not in ("created_at",)},
        **sla_deadlines,
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)
    logger.info("incident_created", incident_number=incident_number, priority=incident.priority)
    metrics.incidents_created_total += 1

    from src.services.notification_manager import manager  # noqa: PLC0415
    await manager.broadcast_incident_update(
        str(incident.incident_id),
        "created",
        {"incident_number": incident.incident_number, "priority": incident.priority, "status": incident.status},
    )
    return incident


async def transition_status(
    db: AsyncSession, incident: Incident, new_status: str, user_id: str | None = None
) -> Incident:
    """インシデントのステータスを遷移させる（遷移ルール検証付き）"""
    allowed = VALID_STATUS_TRANSITIONS.get(incident.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"ステータス '{incident.status}' から '{new_status}' への遷移は許可されていません。"
            f"許可される遷移: {', '.join(allowed) or 'なし'}"
        )

    now = datetime.now(UTC)
    incident.status = new_status

    def _aware(dt: datetime | None) -> datetime | None:
        """SQLiteでtimezone情報が失われた場合にUTCとして補完する"""
        if dt is not None and dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    if new_status == "Acknowledged" and incident.acknowledged_at is None:
        incident.acknowledged_at = now
        sla_due = _aware(incident.sla_response_due_at)
        if sla_due and now > sla_due:
            incident.sla_breached = True
            logger.warning("sla_response_breached", incident_number=incident.incident_number)

    elif new_status == "Resolved":
        incident.resolved_at = now
        sla_due = _aware(incident.sla_resolution_due_at)
        if sla_due and now > sla_due:
            incident.sla_breached = True
            logger.warning("sla_resolution_breached", incident_number=incident.incident_number)

    elif new_status == "Closed":
        incident.closed_at = now

    await db.flush()
    await db.refresh(incident)

    from src.services.notification_manager import manager  # noqa: PLC0415
    action = "closed" if new_status == "Closed" else "updated"
    await manager.broadcast_incident_update(
        str(incident.incident_id),
        action,
        {"incident_number": incident.incident_number, "status": incident.status},
    )
    return incident
