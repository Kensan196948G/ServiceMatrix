"""SLA監視API - サマリー・違反一覧・手動チェック"""

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import cache_get, cache_set
from src.core.database import get_db
from src.models.incident import Incident
from src.services.sla_monitor_service import sla_monitor

router = APIRouter(prefix="/sla", tags=["sla"])

_SLA_SUMMARY_CACHE_KEY = "sla:summary"
_SLA_SUMMARY_TTL = 60


@router.get("/summary")
async def get_sla_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """SLA達成率サマリー（優先度別）- Redisキャッシュ付き（TTL: 60秒）"""
    cached = await cache_get(_SLA_SUMMARY_CACHE_KEY)
    if cached is not None:
        return json.loads(cached)

    result = await sla_monitor.get_sla_summary(db)
    await cache_set(_SLA_SUMMARY_CACHE_KEY, json.dumps(result), ttl=_SLA_SUMMARY_TTL)
    return result


@router.get("/breaches")
async def list_sla_breaches(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """SLA違反インシデント一覧（sla_breached_at降順、最新50件）"""
    result = await db.execute(
        select(Incident)
        .where(Incident.sla_breached == True)  # noqa: E712
        .order_by(Incident.sla_breached_at.desc())
        .offset(skip)
        .limit(limit)
    )
    incidents = result.scalars().all()
    return incidents


@router.post("/check")
async def manual_sla_check(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """手動SLAチェック実行（管理者用）"""
    await sla_monitor.check_sla_breaches(db)
    return {"checked": True, "timestamp": datetime.now(UTC).isoformat()}
