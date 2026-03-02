"""SLA自動監視バックグラウンドエンジン"""
import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.incident import Incident
from src.services import audit_service

logger = get_logger(__name__)


class SLAMonitorService:
    def __init__(self):
        self.running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("sla_monitor_started")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("sla_monitor_stopped")

    async def _monitor_loop(self):
        from src.core.database import AsyncSessionLocal

        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    await self.check_sla_breaches(db)
                    await db.commit()
            except Exception as e:
                logger.error("sla_monitor_loop_error", error=str(e))
            await asyncio.sleep(60)

    async def check_sla_breaches(self, db: AsyncSession) -> int:
        now = datetime.now(UTC)
        result = await db.execute(
            select(Incident).where(
                Incident.status.notin_(["Closed", "Resolved"]),
                Incident.sla_resolution_due_at < now,
                Incident.sla_breached == False,  # noqa: E712
            )
        )
        incidents = result.scalars().all()

        for incident in incidents:
            incident.sla_breached = True
            incident.sla_breached_at = now
            try:
                await audit_service.record_audit_log(
                    db,
                    action="SLA_BREACH_DETECTED",
                    resource_type="Incident",
                    resource_id=str(incident.incident_id),
                    new_values={"sla_breached": True, "sla_breached_at": now.isoformat()},
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("audit_log_failed_in_sla_monitor", error=str(e))

        breach_count = len(incidents)
        if breach_count > 0:
            logger.warning("sla_breaches_detected", count=breach_count)
        return breach_count

    async def get_sla_summary(self, db: AsyncSession) -> dict:
        result = await db.execute(select(Incident))
        incidents = result.scalars().all()

        summary: dict[str, dict] = {}
        for incident in incidents:
            p = incident.priority
            if p not in summary:
                summary[p] = {"total": 0, "breached": 0, "compliance_rate": 100.0}
            summary[p]["total"] += 1
            if incident.sla_breached:
                summary[p]["breached"] += 1

        for data in summary.values():
            if data["total"] > 0:
                data["compliance_rate"] = round(
                    (data["total"] - data["breached"]) / data["total"] * 100, 1
                )

        return summary


sla_monitor = SLAMonitorService()
