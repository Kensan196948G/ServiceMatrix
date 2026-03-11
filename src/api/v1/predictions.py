"""予測的インシデント分析API - Issue #58"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.incident import Incident
from src.models.user import User, UserRole
from src.services.predictive_analytics_service import predictive_analytics_service

router = APIRouter(prefix="/analytics", tags=["予測分析"])


@router.get("/predictions", summary="インシデント発生予測")
async def get_predictions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.INCIDENT_MANAGER, UserRole.SERVICE_MANAGER, UserRole.SYSTEM_ADMIN, UserRole.CHANGE_MANAGER))],
    days: int = Query(default=7, ge=1, le=30, description="予測日数"),
) -> dict:
    """過去30日のインシデントデータから今後N日間の発生件数を予測する"""
    # 過去30日のデータを取得
    now = datetime.now(UTC)
    since = now - timedelta(days=30)

    result = await db.execute(
        select(
            func.date(Incident.created_at).label("date"),
            func.count(Incident.incident_id).label("count"),
        )
        .where(Incident.created_at >= since)
        .group_by(func.date(Incident.created_at))
        .order_by(func.date(Incident.created_at))
    )
    rows = result.all()

    historical_data = [{"date": str(row.date), "count": row.count} for row in rows]

    forecast = predictive_analytics_service.predict_weekly_incidents(
        historical_data, forecast_days=days
    )

    return {
        "predictions": forecast["predictions"],
        "model": forecast["model"],
        "generated_at": now.isoformat(),
    }


@router.get("/predictions/summary", summary="今週の予測サマリー")
async def get_predictions_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.INCIDENT_MANAGER, UserRole.SERVICE_MANAGER, UserRole.SYSTEM_ADMIN, UserRole.CHANGE_MANAGER))],
) -> dict:
    """今後7日間の予測サマリー（合計件数・トレンド・信頼度）を返す"""
    now = datetime.now(UTC)
    since = now - timedelta(days=30)

    result = await db.execute(
        select(
            func.date(Incident.created_at).label("date"),
            func.count(Incident.incident_id).label("count"),
        )
        .where(Incident.created_at >= since)
        .group_by(func.date(Incident.created_at))
        .order_by(func.date(Incident.created_at))
    )
    rows = result.all()

    historical_data = [{"date": str(row.date), "count": row.count} for row in rows]

    forecast = predictive_analytics_service.predict_weekly_incidents(
        historical_data, forecast_days=7
    )

    predictions = forecast["predictions"]
    model = forecast["model"]

    # 合計
    next_7_days_total = sum(p["predicted_count"] for p in predictions)

    # トレンド判定
    trend = "stable"
    if len(predictions) >= 2:
        first_half = sum(p["predicted_count"] for p in predictions[:3])
        second_half = sum(p["predicted_count"] for p in predictions[4:])
        if second_half > first_half * 1.1:
            trend = "increasing"
        elif second_half < first_half * 0.9:
            trend = "decreasing"

    # 信頼度: データ量に基づく
    data_count = len(historical_data)
    if model == "insufficient_data" or data_count < 3:
        confidence = "low"
    elif model == "prophet" or data_count >= 14:
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "next_7_days_total": next_7_days_total,
        "trend": trend,
        "confidence": confidence,
    }
