"""SLA自動監視バックグラウンドエンジン（APScheduler統合）

機能:
- APSchedulerによる定期SLAチェック
- レスポンスSLA・解決SLAの両方を監視
- 70%/90%到達時の事前警告通知
- SLA違反の自動検知と監査ログ記録
"""

import asyncio
import uuid as uuid_mod
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.models.incident import Incident
from src.services import audit_service
from src.services.notification_service import notification_service

logger = get_logger(__name__)


class SLAWarningLevel(StrEnum):
    """SLA警告レベル"""

    NORMAL = "normal"
    WARNING_70 = "warning_70"
    WARNING_90 = "warning_90"
    BREACHED = "breached"


def calculate_sla_progress(created_at: datetime, deadline: datetime) -> float:
    """SLA期限までの経過率を計算する（0.0 ~ 1.0+）

    Args:
        created_at: インシデント作成日時
        deadline: SLA期限日時

    Returns:
        経過率。1.0で期限到達、1.0超は超過
    """
    now = datetime.now(UTC)

    # timezone-naive対応（SQLite等）
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)

    total_duration = (deadline - created_at).total_seconds()
    if total_duration <= 0:
        return 1.0

    elapsed = (now - created_at).total_seconds()
    return elapsed / total_duration


def get_warning_level(progress: float) -> SLAWarningLevel:
    """経過率からSLA警告レベルを判定する"""
    if progress >= 1.0:
        return SLAWarningLevel.BREACHED
    if progress >= settings.sla_warning_threshold_90:
        return SLAWarningLevel.WARNING_90
    if progress >= settings.sla_warning_threshold_70:
        return SLAWarningLevel.WARNING_70
    return SLAWarningLevel.NORMAL


class SLAMonitorService:
    """APScheduler統合SLA監視エンジン"""

    def __init__(self) -> None:
        self.running = False
        self._task: asyncio.Task | None = None
        self._scheduler = None

    async def start(self) -> None:
        """APSchedulerを起動しSLA監視ジョブを登録"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.interval import IntervalTrigger

            self._scheduler = AsyncIOScheduler()
            self._scheduler.add_job(
                self._scheduled_check,
                trigger=IntervalTrigger(seconds=settings.sla_check_interval_seconds),
                id="sla_monitor_job",
                name="SLA Breach/Warning Monitor",
                replace_existing=True,
            )
            self._scheduler.start()
            self.running = True
            logger.info(
                "sla_monitor_started_apscheduler",
                interval_seconds=settings.sla_check_interval_seconds,
            )
        except ImportError:
            # APSchedulerが利用不可の場合はasyncioフォールバック
            self.running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("sla_monitor_started_asyncio_fallback")

    async def stop(self) -> None:
        """SLA監視を停止"""
        self.running = False
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            logger.info("sla_monitor_stopped_apscheduler")
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("sla_monitor_stopped_asyncio")

    async def _scheduled_check(self) -> None:
        """APSchedulerから呼び出されるチェック実行"""
        from src.core.database import AsyncSessionLocal

        try:
            async with AsyncSessionLocal() as db:
                await self.check_sla_breaches(db)
                await self.check_sla_warnings(db)
                await db.commit()
        except Exception as e:
            logger.error("sla_scheduled_check_error", error=str(e))

    async def _monitor_loop(self) -> None:
        """asyncioフォールバック用の監視ループ"""
        from src.core.database import AsyncSessionLocal

        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    await self.check_sla_breaches(db)
                    await self.check_sla_warnings(db)
                    await db.commit()
            except Exception as e:
                logger.error("sla_monitor_loop_error", error=str(e))
            await asyncio.sleep(settings.sla_check_interval_seconds)

    async def check_sla_breaches(self, db: AsyncSession) -> int:
        """SLA違反（レスポンス・解決の両方）を検出してフラグを設定する

        Returns:
            違反検出件数
        """
        now = datetime.now(UTC)

        # 解決SLA違反の検出
        resolution_result = await db.execute(
            select(Incident).where(
                Incident.status.notin_(["Closed", "Resolved"]),
                Incident.sla_resolution_due_at < now,
                Incident.sla_breached == False,  # noqa: E712
            )
        )
        resolution_breaches = resolution_result.scalars().all()

        # レスポンスSLA違反の検出（未応答のインシデントのみ）
        response_result = await db.execute(
            select(Incident).where(
                Incident.status == "New",
                Incident.acknowledged_at.is_(None),
                Incident.sla_response_due_at < now,
                Incident.sla_breached == False,  # noqa: E712
            )
        )
        response_breaches = response_result.scalars().all()

        breach_count = 0

        for incident in resolution_breaches:
            incident.sla_breached = True
            incident.sla_breached_at = now
            breach_count += 1
            await self._record_breach_audit(db, incident, "resolution")
            await self._notify_breach(incident, "resolution")

        for incident in response_breaches:
            # 解決SLAで既にマーク済みの場合はスキップ
            if incident.sla_breached:
                continue
            incident.sla_breached = True
            incident.sla_breached_at = now
            breach_count += 1
            await self._record_breach_audit(db, incident, "response")
            await self._notify_breach(incident, "response")

        if breach_count > 0:
            logger.warning("sla_breaches_detected", count=breach_count)
        return breach_count

    async def check_sla_warnings(self, db: AsyncSession) -> list[dict]:
        """70%/90%到達の事前警告対象を検出して通知する

        Returns:
            警告対象のインシデント情報リスト
        """
        now = datetime.now(UTC)
        warnings: list[dict] = []

        # 未解決・未違反のインシデントを取得
        result = await db.execute(
            select(Incident).where(
                Incident.status.notin_(["Closed", "Resolved"]),
                Incident.sla_breached == False,  # noqa: E712
                Incident.sla_resolution_due_at.isnot(None),
                Incident.sla_resolution_due_at > now,
            )
        )
        active_incidents = result.scalars().all()

        for incident in active_incidents:
            created_at = incident.created_at
            if created_at is None:
                continue

            # 解決SLA経過率
            resolution_progress = calculate_sla_progress(
                created_at, incident.sla_resolution_due_at
            )
            resolution_level = get_warning_level(resolution_progress)

            if resolution_level in (SLAWarningLevel.WARNING_70, SLAWarningLevel.WARNING_90):
                warning_info = {
                    "incident_id": str(incident.incident_id),
                    "incident_number": incident.incident_number,
                    "title": incident.title,
                    "priority": incident.priority,
                    "sla_type": "resolution",
                    "warning_level": resolution_level.value,
                    "progress_percent": round(resolution_progress * 100, 1),
                    "deadline": incident.sla_resolution_due_at.isoformat()
                    if incident.sla_resolution_due_at
                    else None,
                }
                warnings.append(warning_info)

                await self._notify_warning(incident, resolution_level, resolution_progress)

            # レスポンスSLA経過率（未応答の場合のみ）
            if (
                incident.acknowledged_at is None
                and incident.sla_response_due_at is not None
                and incident.sla_response_due_at > now
            ):
                response_progress = calculate_sla_progress(
                    created_at, incident.sla_response_due_at
                )
                response_level = get_warning_level(response_progress)

                if response_level in (SLAWarningLevel.WARNING_70, SLAWarningLevel.WARNING_90):
                    warning_info = {
                        "incident_id": str(incident.incident_id),
                        "incident_number": incident.incident_number,
                        "title": incident.title,
                        "priority": incident.priority,
                        "sla_type": "response",
                        "warning_level": response_level.value,
                        "progress_percent": round(response_progress * 100, 1),
                        "deadline": incident.sla_response_due_at.isoformat()
                        if incident.sla_response_due_at
                        else None,
                    }
                    warnings.append(warning_info)

        if warnings:
            logger.info("sla_warnings_detected", count=len(warnings))

        return warnings

    async def get_sla_status(self, db: AsyncSession, incident_id: str) -> dict | None:
        """個別インシデントのSLAステータスを取得する"""
        try:
            uid = uuid_mod.UUID(incident_id)
        except (ValueError, AttributeError):
            return None
        result = await db.execute(
            select(Incident).where(Incident.incident_id == uid)
        )
        incident = result.scalar_one_or_none()
        if incident is None:
            return None

        created_at = incident.created_at
        if created_at is None:
            return None

        status: dict = {
            "incident_id": str(incident.incident_id),
            "incident_number": incident.incident_number,
            "priority": incident.priority,
            "status": incident.status,
            "sla_breached": incident.sla_breached,
            "sla_breached_at": incident.sla_breached_at.isoformat()
            if incident.sla_breached_at
            else None,
        }

        # レスポンスSLA
        if incident.sla_response_due_at is not None:
            if incident.acknowledged_at is not None:
                status["response_sla"] = {
                    "deadline": incident.sla_response_due_at.isoformat(),
                    "met": True,
                    "acknowledged_at": incident.acknowledged_at.isoformat(),
                    "warning_level": SLAWarningLevel.NORMAL.value,
                    "progress_percent": 100.0,
                }
            else:
                progress = calculate_sla_progress(created_at, incident.sla_response_due_at)
                level = get_warning_level(progress)
                status["response_sla"] = {
                    "deadline": incident.sla_response_due_at.isoformat(),
                    "met": False,
                    "acknowledged_at": None,
                    "warning_level": level.value,
                    "progress_percent": round(min(progress * 100, 100.0), 1),
                }

        # 解決SLA
        if incident.sla_resolution_due_at is not None:
            if incident.resolved_at is not None:
                status["resolution_sla"] = {
                    "deadline": incident.sla_resolution_due_at.isoformat(),
                    "met": True,
                    "resolved_at": incident.resolved_at.isoformat(),
                    "warning_level": SLAWarningLevel.NORMAL.value,
                    "progress_percent": 100.0,
                }
            else:
                progress = calculate_sla_progress(created_at, incident.sla_resolution_due_at)
                level = get_warning_level(progress)
                status["resolution_sla"] = {
                    "deadline": incident.sla_resolution_due_at.isoformat(),
                    "met": False,
                    "resolved_at": None,
                    "warning_level": level.value,
                    "progress_percent": round(min(progress * 100, 100.0), 1),
                }

        return status

    async def get_sla_summary(self, db: AsyncSession) -> dict:
        """優先度別SLA達成率サマリーを生成する"""
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

    async def get_active_warnings(self, db: AsyncSession) -> list[dict]:
        """現在アクティブな警告対象インシデント一覧を取得する

        check_sla_warnings と異なり通知は送信せず、照会のみ行う
        """
        now = datetime.now(UTC)
        warnings: list[dict] = []

        result = await db.execute(
            select(Incident).where(
                Incident.status.notin_(["Closed", "Resolved"]),
                Incident.sla_breached == False,  # noqa: E712
                Incident.sla_resolution_due_at.isnot(None),
                Incident.sla_resolution_due_at > now,
            )
        )
        active_incidents = result.scalars().all()

        for incident in active_incidents:
            created_at = incident.created_at
            if created_at is None:
                continue

            resolution_progress = calculate_sla_progress(
                created_at, incident.sla_resolution_due_at
            )
            resolution_level = get_warning_level(resolution_progress)

            if resolution_level in (SLAWarningLevel.WARNING_70, SLAWarningLevel.WARNING_90):
                warnings.append({
                    "incident_id": str(incident.incident_id),
                    "incident_number": incident.incident_number,
                    "title": incident.title,
                    "priority": incident.priority,
                    "sla_type": "resolution",
                    "warning_level": resolution_level.value,
                    "progress_percent": round(resolution_progress * 100, 1),
                    "deadline": incident.sla_resolution_due_at.isoformat()
                    if incident.sla_resolution_due_at
                    else None,
                })

            # レスポンスSLA警告（未応答のみ）
            if (
                incident.acknowledged_at is None
                and incident.sla_response_due_at is not None
                and incident.sla_response_due_at > now
            ):
                response_progress = calculate_sla_progress(
                    created_at, incident.sla_response_due_at
                )
                response_level = get_warning_level(response_progress)

                if response_level in (SLAWarningLevel.WARNING_70, SLAWarningLevel.WARNING_90):
                    warnings.append({
                        "incident_id": str(incident.incident_id),
                        "incident_number": incident.incident_number,
                        "title": incident.title,
                        "priority": incident.priority,
                        "sla_type": "response",
                        "warning_level": response_level.value,
                        "progress_percent": round(response_progress * 100, 1),
                        "deadline": incident.sla_response_due_at.isoformat()
                        if incident.sla_response_due_at
                        else None,
                    })

        return warnings

    # --- 内部ヘルパー ---

    async def _record_breach_audit(
        self, db: AsyncSession, incident: Incident, breach_type: str
    ) -> None:
        """SLA違反を監査ログに記録"""
        try:
            await audit_service.record_audit_log(
                db,
                action="SLA_BREACH_DETECTED",
                resource_type="Incident",
                resource_id=str(incident.incident_id),
                new_values={
                    "sla_breached": True,
                    "sla_breached_at": incident.sla_breached_at.isoformat()
                    if incident.sla_breached_at
                    else None,
                    "breach_type": breach_type,
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("audit_log_failed_in_sla_monitor", error=str(e))

    async def _notify_breach(self, incident: Incident, breach_type: str) -> None:
        """SLA違反通知を送信"""
        try:
            await notification_service.notify_sla_breach(
                incident_number=incident.incident_number,
                incident_title=incident.title,
                priority=incident.priority,
                breach_type=breach_type,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("notification_failed_in_sla_monitor", error=str(e))

    async def _notify_warning(
        self,
        incident: Incident,
        level: SLAWarningLevel,
        progress: float,
    ) -> None:
        """SLA事前警告通知を送信"""
        try:
            await notification_service.notify_sla_warning(
                incident_number=incident.incident_number,
                incident_title=incident.title,
                priority=incident.priority,
                warning_level=level.value,
                progress_percent=round(progress * 100, 1),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("sla_warning_notification_failed", error=str(e))


sla_monitor = SLAMonitorService()
