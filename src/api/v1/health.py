"""ヘルスチェックエンドポイント"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """アプリケーションおよびDB接続のヘルスチェック"""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
    }
