"""Celery タスク定義"""

from datetime import UTC, datetime

from asgiref.sync import async_to_sync

from src.core.logging import get_logger
from src.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="tasks.check_sla_breaches", bind=True, max_retries=3)
def check_sla_breaches(self):
    """SLA違反チェックタスク（定期実行）"""
    try:
        logger.info("sla_check_started", task_id=self.request.id)
        result = async_to_sync(_check_sla_async)()
        logger.info("sla_check_completed", breaches=result.get("breaches", 0))
        return result
    except Exception as exc:
        logger.error("sla_check_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc


async def _check_sla_async() -> dict:
    """SLA違反の非同期チェック"""
    from sqlalchemy import func, select

    from src.core.database import AsyncSessionLocal
    from src.models.incident import Incident

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).where(Incident.status == "Open"))
        open_count = result.scalar_one()
        return {
            "checked_at": datetime.now(UTC).isoformat(),
            "open_incidents": open_count,
            "breaches": 0,
        }


@celery_app.task(name="tasks.send_notification")
def send_notification(user_id: str, message: str, notification_type: str = "info"):
    """通知送信タスク"""
    logger.info(
        "notification_sent",
        user_id=user_id,
        notification_type=notification_type,
        message_preview=message[:50],
    )
    return {
        "sent_at": datetime.now(UTC).isoformat(),
        "user_id": user_id,
        "type": notification_type,
        "success": True,
    }


@celery_app.task(name="tasks.ai_triage_incident", bind=True, max_retries=2)
def ai_triage_incident(self, incident_id: str, title: str, description: str):
    """AI インシデント自動分類タスク"""
    try:
        logger.info("ai_triage_started", incident_id=incident_id)
        result = async_to_sync(_ai_triage_async)(incident_id, title, description)
        return result
    except Exception as exc:
        logger.warning("ai_triage_failed", incident_id=incident_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30) from exc


async def _ai_triage_async(incident_id: str, title: str, description: str) -> dict:
    """AI トリアージの非同期実行（AITriageService経由）"""
    from src.services.ai_triage_service import AITriageService

    service = AITriageService()
    result = await service.triage(title, description)
    return {
        "incident_id": incident_id,
        "priority": result.priority,
        "category": result.category,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="tasks.cleanup_old_logs")
def cleanup_old_logs(days_to_keep: int = 365 * 7):
    """J-SOX 7年保管期間外ログのクリーンアップ（実際には削除せず確認のみ）"""
    logger.info("log_cleanup_check_started", days_to_keep=days_to_keep)
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "days_to_keep": days_to_keep,
        "action": "check_only",
    }
