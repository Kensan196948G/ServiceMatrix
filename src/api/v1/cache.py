"""キャッシュ管理 API エンドポイント"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from src.core.cache import cache_delete_pattern, get_redis
from src.core.cache_decorator import CACHE_PREFIX

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/cache", tags=["cache"])

# 許可されたキャッシュプレフィックス
ALLOWED_PREFIXES = {
    "incidents_list",
    "sla_dashboard",
    "cmdb_list",
    "health",
    "reports",
}


class CacheStatsResponse(BaseModel):
    prefix: str
    key_count: int
    pattern: str


class CacheDeleteResponse(BaseModel):
    prefix: str
    deleted: bool
    message: str


@router.get("/stats", response_model=list[CacheStatsResponse])
async def get_cache_stats():
    """キャッシュプレフィックスごとのエントリ数を返す"""
    try:
        client = get_redis()
        results = []
        for prefix in sorted(ALLOWED_PREFIXES):
            pattern = f"{CACHE_PREFIX}:{prefix}:*"
            count = 0
            async for _ in client.scan_iter(pattern, count=100):
                count += 1
            results.append(
                CacheStatsResponse(prefix=prefix, key_count=count, pattern=pattern)
            )
        return results
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis接続エラー: {exc}") from exc


@router.get("/stats/{prefix}", response_model=CacheStatsResponse)
async def get_cache_stats_by_prefix(
    prefix: str = Path(..., description="キャッシュプレフィックス"),
):
    """指定プレフィックスのキャッシュエントリ数を返す"""
    if prefix not in ALLOWED_PREFIXES:
        raise HTTPException(
            status_code=404,
            detail=(
                f"プレフィックス '{prefix}' は存在しません。"
                f"利用可能: {sorted(ALLOWED_PREFIXES)}"
            ),
        )
    try:
        client = get_redis()
        pattern = f"{CACHE_PREFIX}:{prefix}:*"
        count = 0
        async for _ in client.scan_iter(pattern, count=100):
            count += 1
        return CacheStatsResponse(prefix=prefix, key_count=count, pattern=pattern)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis接続エラー: {exc}") from exc


@router.delete("/{prefix}", response_model=CacheDeleteResponse)
async def delete_cache_by_prefix(
    prefix: str = Path(..., description="削除対象のキャッシュプレフィックス"),
):
    """指定プレフィックスのキャッシュを全削除する"""
    if prefix not in ALLOWED_PREFIXES:
        raise HTTPException(
            status_code=404,
            detail=(
                f"プレフィックス '{prefix}' は存在しません。"
                f"利用可能: {sorted(ALLOWED_PREFIXES)}"
            ),
        )
    try:
        pattern = f"{CACHE_PREFIX}:{prefix}:*"
        await cache_delete_pattern(pattern)
        logger.info("cache_manually_deleted", prefix=prefix)
        return CacheDeleteResponse(
            prefix=prefix,
            deleted=True,
            message=f"プレフィックス '{prefix}' のキャッシュを削除しました",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"キャッシュ削除エラー: {exc}") from exc
