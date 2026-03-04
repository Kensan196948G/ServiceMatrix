"""レポート/分析API - 月次KPI・MTTR・SLA達成率"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user
from src.models.change import Change
from src.models.incident import Incident
from src.models.user import User

router = APIRouter(prefix="/reports", tags=["レポート"])


@router.get("/stats", summary="月次KPI統計取得")
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    year: int = Query(default=None),
    month: int = Query(default=None),
) -> dict:
    """月次KPIサマリ（MTTR・MTBF・SLA達成率）を返す"""
    now = datetime.now(UTC)
    target_year = year or now.year
    target_month = month or now.month

    # 対象月の開始/終了
    from calendar import monthrange

    _, last_day = monthrange(target_year, target_month)
    period_start = datetime(target_year, target_month, 1, tzinfo=UTC)
    period_end = datetime(target_year, target_month, last_day, 23, 59, 59, tzinfo=UTC)

    # インシデント集計
    inc_q = select(Incident).where(
        Incident.created_at >= period_start,
        Incident.created_at <= period_end,
    )
    inc_result = await db.execute(inc_q)
    incidents = inc_result.scalars().all()

    total_inc = len(incidents)
    resolved = [i for i in incidents if i.resolved_at is not None]
    open_inc = [i for i in incidents if i.status not in ("Resolved", "Closed")]
    sla_breached = [i for i in incidents if i.sla_breached]

    # MTTR計算 (平均解決時間・時間単位)
    resolution_hours: list[float] = []
    for inc in resolved:
        if inc.resolved_at and inc.created_at:
            delta = inc.resolved_at - inc.created_at
            resolution_hours.append(delta.total_seconds() / 3600)
    mttr = round(sum(resolution_hours) / len(resolution_hours), 2) if resolution_hours else 0.0

    # MTBF推定 (月の時間数 / インシデント数)
    period_hours = last_day * 24.0
    mtbf = round(period_hours / total_inc, 2) if total_inc > 0 else period_hours

    # SLA達成率
    sla_compliance = round(1.0 - len(sla_breached) / total_inc, 4) if total_inc > 0 else 1.0

    # 影響サービス上位5件
    service_counts: dict[str, int] = {}
    for inc in incidents:
        svc = inc.affected_service or "不明"
        service_counts[svc] = service_counts.get(svc, 0) + 1
    top_services = [
        {"service": svc, "count": cnt}
        for svc, cnt in sorted(service_counts.items(), key=lambda x: -x[1])[:5]
    ]

    # 変更管理集計
    chg_q = select(Change).where(
        Change.created_at >= period_start,
        Change.created_at <= period_end,
    )
    chg_result = await db.execute(chg_q)
    changes = chg_result.scalars().all()

    total_chg = len(changes)
    completed_chg = sum(1 for c in changes if c.status == "Completed")
    failed_chg = sum(1 for c in changes if c.status == "Failed")

    return {
        "period": {"year": target_year, "month": target_month},
        "incidents": {
            "total": total_inc,
            "resolved": len(resolved),
            "open": len(open_inc),
            "avg_resolution_hours": mttr,
        },
        "mttr_hours": mttr,
        "mtbf_hours": mtbf,
        "sla_compliance_rate": sla_compliance,
        "changes": {
            "total": total_chg,
            "completed": completed_chg,
            "failed": failed_chg,
        },
        "top_affected_services": top_services,
    }


@router.get("/incident-resolution-distribution", summary="インシデント解決時間分布")
async def get_resolution_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    year: int = Query(default=None),
    month: int = Query(default=None),
) -> dict:
    """解決済みインシデントの解決時間分布をバケット別に返す"""
    now = datetime.now(UTC)
    target_year = year or now.year
    target_month = month or now.month

    from calendar import monthrange

    _, last_day = monthrange(target_year, target_month)
    period_start = datetime(target_year, target_month, 1, tzinfo=UTC)
    period_end = datetime(target_year, target_month, last_day, 23, 59, 59, tzinfo=UTC)

    inc_q = select(Incident).where(
        Incident.created_at >= period_start,
        Incident.created_at <= period_end,
        Incident.resolved_at.isnot(None),
    )
    result = await db.execute(inc_q)
    incidents = result.scalars().all()

    buckets: list[dict[str, int | str]] = [
        {"range": "0-1h", "count": 0},
        {"range": "1-4h", "count": 0},
        {"range": "4-8h", "count": 0},
        {"range": "8-24h", "count": 0},
        {"range": "24h+", "count": 0},
    ]

    for inc in incidents:
        if inc.resolved_at and inc.created_at:
            hours = (inc.resolved_at - inc.created_at).total_seconds() / 3600
            idx = 4
            if hours < 1:
                idx = 0
            elif hours < 4:
                idx = 1
            elif hours < 8:
                idx = 2
            elif hours < 24:
                idx = 3
            buckets[idx]["count"] = int(buckets[idx]["count"]) + 1

    return {"buckets": buckets, "period": {"year": target_year, "month": target_month}}


@router.get("/monthly-summary", summary="月次サマリ")
async def get_monthly_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    year: int = Query(default=None),
    month: int = Query(default=None),
) -> dict:
    """月次サマリ（stats + distribution の統合レスポンス）"""
    stats = await get_stats(db=db, current_user=current_user, year=year, month=month)
    dist = await get_resolution_distribution(
        db=db, current_user=current_user, year=year, month=month
    )
    return {**stats, "resolution_distribution": dist["buckets"]}
