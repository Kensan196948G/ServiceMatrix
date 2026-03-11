"""SLAアナリティクス / トレンド分析API - Issue #57"""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.user import User, UserRole
from src.services.sla_analytics_service import (
    get_change_success_trends,
    get_incident_sla_trends,
    get_summary_metrics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sla-trends", summary="インシデントSLAトレンド取得")
async def sla_trends(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365, description="集計対象日数"),
    department: str | None = Query(default=None, description="部署フィルター"),
) -> dict:
    """過去N日間のインシデントSLAコンプライアンストレンドを返す。

    全ロール読み取り可能。
    """
    return await get_incident_sla_trends(db, days=days, department=department)


@router.get("/change-trends", summary="変更管理成功率トレンド取得")
async def change_trends(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365, description="集計対象日数"),
) -> dict:
    """過去N日間の変更管理成功率トレンドを返す。

    全ロール読み取り可能。
    """
    return await get_change_success_trends(db, days=days)


@router.get("/summary", summary="ダッシュボードサマリーメトリクス取得")
async def summary_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """ダッシュボード用のサマリーメトリクスを返す。

    全ロール読み取り可能。
    """
    return await get_summary_metrics(db)


@router.get("/export/csv", summary="SLAトレンドCSVエクスポート")
async def export_csv(
    current_user: Annotated[User, Depends(require_role(
        UserRole.SERVICE_MANAGER,
        UserRole.CHANGE_MANAGER,
        UserRole.SYSTEM_ADMIN,
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365, description="集計対象日数"),
) -> StreamingResponse:
    """SLAトレンドデータをCSVとしてエクスポートする。

    manager 以上のロールが必要。
    """
    data = await get_incident_sla_trends(db, days=days)

    output = io.StringIO()
    writer = csv.writer(output)

    # ヘッダー行
    writer.writerow(["date", "count", "breaches", "compliance_rate"])

    # 日別データ
    total = data["total_incidents"]
    breaches_total = data["sla_breaches"]
    for row in data["daily_trends"]:
        row_total = row["count"]
        row_breaches = row["breaches"]
        row_compliance = (
            round((row_total - row_breaches) / row_total * 100, 1)
            if row_total > 0
            else 100.0
        )
        writer.writerow([row["date"], row_total, row_breaches, row_compliance])

    # サマリー行
    writer.writerow([])
    writer.writerow(["summary", "total_incidents", "sla_breaches", "compliance_rate"])
    writer.writerow([
        f"last_{days}_days",
        total,
        breaches_total,
        data["sla_compliance_rate"],
    ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=sla_trends_{days}days.csv"
        },
    )
