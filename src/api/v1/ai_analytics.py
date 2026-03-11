"""AI異常検知APIエンドポイント - IsolationForest ベース"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.middleware.rbac import get_current_user, require_role
from src.models.incident import Incident
from src.models.user import User, UserRole
from src.services.anomaly_detection_service import anomaly_service

router = APIRouter(prefix="/ai/anomaly", tags=["ai-anomaly"])


class BulkAnomalyRequest(BaseModel):
    """一括異常スコア取得リクエスト"""

    incidents: list[dict]


class TrainRequest(BaseModel):
    """モデル再学習リクエスト"""

    use_recent_days: int = 30


@router.get(
    "/status",
    summary="異常検知モデルのステータス確認",
)
async def anomaly_status(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """異常検知モデルのトレーニング状態を返す"""
    return {
        "is_trained": anomaly_service.is_trained,
        "model_type": "IsolationForest",
        "features": ["hour", "priority_score", "day_of_week"],
        "status": "ready" if anomaly_service.is_trained else "not_trained",
    }


@router.get(
    "/score",
    summary="特定インシデントの異常スコア取得",
)
async def get_anomaly_score(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    incident_id: str = Query(..., description="インシデントID"),
) -> dict:
    """指定インシデントの異常スコアを返す"""
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"無効なUUID形式です: {incident_id}",
        )
    result = await db.execute(select(Incident).where(Incident.incident_id == incident_uuid))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"インシデントが見つかりません: {incident_id}",
        )

    created_at = incident.created_at
    incident_data = {
        "hour": created_at.hour if created_at else 12,
        "priority": incident.priority,
        "day_of_week": created_at.weekday() if created_at else 0,
    }

    score = anomaly_service.predict_anomaly_score(incident_data)
    is_anomaly = anomaly_service.is_anomaly(incident_data)

    return {
        "incident_id": incident_id,
        "incident_number": incident.incident_number,
        "anomaly_score": score,
        "is_anomaly": is_anomaly,
        "threshold": 0.6,
        "model_trained": anomaly_service.is_trained,
        "features_used": incident_data,
    }


@router.post(
    "/score/bulk",
    summary="複数インシデントのスコア一括取得",
    status_code=status.HTTP_200_OK,
)
async def bulk_anomaly_score(
    request: BulkAnomalyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """複数インシデントデータの異常スコアを一括取得する"""
    results = []
    for i, incident_data in enumerate(request.incidents):
        score = anomaly_service.predict_anomaly_score(incident_data)
        is_anomaly = anomaly_service.is_anomaly(incident_data)
        results.append(
            {
                "index": i,
                "input": incident_data,
                "anomaly_score": score,
                "is_anomaly": is_anomaly,
            }
        )

    return {
        "total": len(results),
        "anomaly_count": sum(1 for r in results if r["is_anomaly"]),
        "model_trained": anomaly_service.is_trained,
        "results": results,
    }


@router.post(
    "/train",
    summary="異常検知モデル再学習（admin のみ）",
    status_code=status.HTTP_200_OK,
)
async def train_anomaly_model(
    request: TrainRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> dict:
    """最近のインシデントデータを使って異常検知モデルを再学習する"""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=request.use_recent_days)
    result = await db.execute(
        select(Incident).where(Incident.created_at >= cutoff).limit(1000)
    )
    incidents = result.scalars().all()

    training_data = []
    for inc in incidents:
        created_at = inc.created_at
        training_data.append(
            {
                "hour": created_at.hour if created_at else 12,
                "priority": inc.priority,
                "day_of_week": created_at.weekday() if created_at else 0,
            }
        )

    success = anomaly_service.train(training_data)

    return {
        "success": success,
        "training_samples": len(training_data),
        "model_trained": anomaly_service.is_trained,
        "message": (
            f"{len(training_data)} 件のインシデントで学習しました"
            if success
            else "学習に失敗しました（データ不足またはエラー）"
        ),
    }
