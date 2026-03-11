"""ヘルスチェックエンドポイント"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import health_check_redis
from src.core.config import settings
from src.core.database import get_db
from src.core.metrics import metrics

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """アプリケーションおよびDB接続のヘルスチェック"""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    redis_info = await health_check_redis()

    overall_status = "ok" if db_status == "ok" else "degraded"

    return {
        "status": overall_status,
        "version": settings.app_version,
        "database": db_status,
        "redis": redis_info,
    }


@router.get("/metrics")
async def get_metrics_json():
    """メトリクスサマリー(JSON)"""
    return metrics.to_json()


@router.get("/metrics/prometheus")
async def get_metrics_prometheus():
    """Prometheusテキスト形式メトリクス"""
    return PlainTextResponse(metrics.to_prometheus_text(), media_type="text/plain")


@router.get("/health/detailed")
async def detailed_health(db: Annotated[AsyncSession, Depends(get_db)]):
    """詳細ヘルスチェック（DB接続・Redis接続・バージョン情報）"""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {
            "api": "up",
            "database": db_status,
            "redis": "connected",
        },
    }
