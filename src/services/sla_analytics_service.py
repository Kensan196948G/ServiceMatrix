"""SLAトレンド分析サービス"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.change import Change
from src.models.incident import Incident

logger = structlog.get_logger(__name__)


async def get_incident_sla_trends(
    db: AsyncSession,
    days: int = 30,
    department: str | None = None,
) -> dict[str, Any]:
    """過去N日間のインシデントSLAトレンドを返す"""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    # 基本クエリ構築
    stmt = select(Incident).where(Incident.created_at >= since)
    if department:
        stmt = stmt.where(Incident.department == department)

    result = await db.execute(stmt)
    incidents = result.scalars().all()

    # Python集計
    total = len(incidents)
    breaches = sum(1 for i in incidents if i.sla_breached)
    compliance_rate = round((total - breaches) / total * 100, 1) if total > 0 else 100.0

    # 日別トレンド
    daily: dict[str, dict[str, int]] = {}
    for inc in incidents:
        created = inc.created_at
        if created is not None:
            # timezone-aware/naive の両方を考慮
            if hasattr(created, "date"):
                date_str = created.strftime("%Y-%m-%d")
            else:
                date_str = str(created)[:10]
            if date_str not in daily:
                daily[date_str] = {"count": 0, "breaches": 0}
            daily[date_str]["count"] += 1
            if inc.sla_breached:
                daily[date_str]["breaches"] += 1

    daily_trends = [
        {"date": d, "count": v["count"], "breaches": v["breaches"]}
        for d, v in sorted(daily.items())
    ]

    # 優先度別集計
    by_priority: dict[str, dict[str, int]] = {}
    for inc in incidents:
        p = inc.priority or "Unknown"
        if p not in by_priority:
            by_priority[p] = {"count": 0, "breaches": 0}
        by_priority[p]["count"] += 1
        if inc.sla_breached:
            by_priority[p]["breaches"] += 1

    logger.info(
        "sla_trends_fetched",
        days=days,
        department=department,
        total=total,
        breaches=breaches,
    )

    return {
        "period_days": days,
        "total_incidents": total,
        "sla_breaches": breaches,
        "sla_compliance_rate": compliance_rate,
        "daily_trends": daily_trends,
        "by_priority": by_priority,
    }


async def get_change_success_trends(
    db: AsyncSession,
    days: int = 30,
) -> dict[str, Any]:
    """過去N日間の変更管理成功率トレンドを返す"""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    stmt = select(Change).where(Change.created_at >= since)
    result = await db.execute(stmt)
    changes = result.scalars().all()

    total = len(changes)
    completed = sum(1 for c in changes if c.status == "Completed")
    failed = sum(1 for c in changes if c.status == "Failed")
    cancelled = sum(1 for c in changes if c.status == "Cancelled")
    in_progress = sum(1 for c in changes if c.status == "In_Progress")
    pending_approval = sum(1 for c in changes if c.status in ("Submitted", "CAB_Review"))

    success_rate = round(completed / total * 100, 1) if total > 0 else 0.0

    # 日別トレンド
    daily: dict[str, dict[str, int]] = {}
    for chg in changes:
        created = chg.created_at
        if created is not None:
            date_str = created.strftime("%Y-%m-%d")
            if date_str not in daily:
                daily[date_str] = {"count": 0, "completed": 0, "failed": 0}
            daily[date_str]["count"] += 1
            if chg.status == "Completed":
                daily[date_str]["completed"] += 1
            elif chg.status == "Failed":
                daily[date_str]["failed"] += 1

    daily_trends = [
        {
            "date": d,
            "count": v["count"],
            "completed": v["completed"],
            "failed": v["failed"],
        }
        for d, v in sorted(daily.items())
    ]

    # 変更タイプ別集計
    by_type: dict[str, dict[str, int]] = {}
    for chg in changes:
        t = chg.change_type or "Unknown"
        if t not in by_type:
            by_type[t] = {"count": 0, "completed": 0, "failed": 0}
        by_type[t]["count"] += 1
        if chg.status == "Completed":
            by_type[t]["completed"] += 1
        elif chg.status == "Failed":
            by_type[t]["failed"] += 1

    logger.info(
        "change_trends_fetched",
        days=days,
        total=total,
        completed=completed,
        failed=failed,
    )

    return {
        "period_days": days,
        "total_changes": total,
        "completed": completed,
        "failed": failed,
        "cancelled": cancelled,
        "in_progress": in_progress,
        "pending_approval": pending_approval,
        "success_rate": success_rate,
        "daily_trends": daily_trends,
        "by_type": by_type,
    }


async def get_summary_metrics(
    db: AsyncSession,
) -> dict[str, Any]:
    """ダッシュボード用サマリーメトリクスを返す"""
    # オープンインシデント数
    inc_open_stmt = (
        select(func.count())
        .select_from(Incident)
        .where(
            Incident.status.in_(
                ["New", "Acknowledged", "In_Progress", "Pending", "Workaround_Applied"]
            )
        )
    )
    inc_open_result = await db.execute(inc_open_stmt)
    open_incidents = inc_open_result.scalar() or 0

    # SLA違反インシデント数（未解決）
    sla_breach_stmt = (
        select(func.count())
        .select_from(Incident)
        .where(
            and_(
                Incident.sla_breached.is_(True),
                Incident.status.notin_(["Resolved", "Closed"]),
            )
        )
    )
    sla_breach_result = await db.execute(sla_breach_stmt)
    active_sla_breaches = sla_breach_result.scalar() or 0

    # 変更承認待ち数
    chg_pending_stmt = (
        select(func.count())
        .select_from(Change)
        .where(Change.status.in_(["Submitted", "CAB_Review"]))
    )
    chg_pending_result = await db.execute(chg_pending_stmt)
    pending_changes = chg_pending_result.scalar() or 0

    # 直近24時間のインシデント数
    last_24h = datetime.now(UTC) - timedelta(hours=24)
    inc_24h_stmt = select(func.count()).select_from(Incident).where(Incident.created_at >= last_24h)
    inc_24h_result = await db.execute(inc_24h_stmt)
    incidents_last_24h = inc_24h_result.scalar() or 0

    # P1インシデント数（オープン）
    p1_stmt = (
        select(func.count())
        .select_from(Incident)
        .where(
            and_(
                Incident.priority == "P1",
                Incident.status.in_(["New", "Acknowledged", "In_Progress"]),
            )
        )
    )
    p1_result = await db.execute(p1_stmt)
    open_p1_incidents = p1_result.scalar() or 0

    # 進行中の変更数
    chg_active_stmt = select(func.count()).select_from(Change).where(Change.status == "In_Progress")
    chg_active_result = await db.execute(chg_active_stmt)
    active_changes = chg_active_result.scalar() or 0

    logger.info(
        "summary_metrics_fetched",
        open_incidents=open_incidents,
        active_sla_breaches=active_sla_breaches,
        pending_changes=pending_changes,
    )

    return {
        "open_incidents": open_incidents,
        "active_sla_breaches": active_sla_breaches,
        "pending_changes": pending_changes,
        "incidents_last_24h": incidents_last_24h,
        "open_p1_incidents": open_p1_incidents,
        "active_changes": active_changes,
        "generated_at": datetime.now(UTC).isoformat(),
    }
