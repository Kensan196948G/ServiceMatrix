"""Celery タスク定義 - SLAチェック・エスカレーション通知"""

import asyncio
from datetime import UTC, datetime

from src.core.logging import get_logger
from src.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="tasks.check_sla_breaches")
def check_sla_breaches() -> dict:
    """定期SLA違反チェックタスク - 残時間30%以下のインシデントにエスカレーション通知"""
    return asyncio.run(_async_check_sla_breaches())


async def _async_check_sla_breaches() -> dict:
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.models.incident import Incident

    async with AsyncSessionLocal() as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(Incident).where(
                Incident.sla_breached == False,  # noqa: E712
                Incident.sla_resolution_due_at.isnot(None),
                Incident.status.notin_(["Resolved", "Closed"]),
            )
        )
        incidents = result.scalars().all()

        escalated = 0
        for incident in incidents:
            due = incident.sla_resolution_due_at
            created = incident.created_at
            if due is None:
                continue
            if due.tzinfo is None:
                due = due.replace(tzinfo=UTC)
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)

            total = (due - created).total_seconds()
            if total <= 0:
                continue

            remaining = (due - now).total_seconds()
            remaining_pct = (remaining / total) * 100

            if remaining_pct <= 30:
                send_escalation_notification.delay(
                    str(incident.incident_id), round(remaining_pct, 2)
                )
                escalated += 1

        logger.info("SLA breach check completed", checked=len(incidents), escalated=escalated)
        return {"checked": len(incidents), "escalated": escalated}


@celery_app.task(name="tasks.send_escalation_notification")
def send_escalation_notification(incident_id: str, sla_remaining_percent: float) -> dict:
    """SLA残時間が30%以下になったインシデントへのエスカレーション通知"""
    logger.warning(
        "SLA escalation notification triggered",
        incident_id=incident_id,
        sla_remaining_percent=sla_remaining_percent,
    )
    # Slack/Teams通知はwebhook URLが設定されていれば送信（現状はログのみ）
    return {
        "incident_id": incident_id,
        "sla_remaining_percent": sla_remaining_percent,
        "notified": True,
    }
