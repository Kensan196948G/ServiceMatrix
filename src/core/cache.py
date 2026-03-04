"""Redis キャッシュユーティリティ"""

import redis.asyncio as aioredis  # type: ignore[import-untyped]
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Redisクライアントを取得（シングルトン）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> str | None:
    """キャッシュ取得。失敗時はNoneを返す（graceful degradation）"""
    try:
        client = get_redis()
        return await client.get(key)
    except Exception as e:
        logger.warning("cache_get_failed", key=key, error=str(e))
        return None


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    """キャッシュ保存（デフォルトTTL: 5分）。失敗時はwarnログのみ"""
    try:
        client = get_redis()
        await client.set(key, value, ex=ttl)
    except Exception as e:
        logger.warning("cache_set_failed", key=key, error=str(e))


async def cache_delete(key: str) -> None:
    """キャッシュ削除。失敗時はwarnログのみ"""
    try:
        client = get_redis()
        await client.delete(key)
    except Exception as e:
        logger.warning("cache_delete_failed", key=key, error=str(e))


async def cache_delete_pattern(pattern: str) -> None:
    """パターンに一致するキャッシュを全削除（scan_iter使用）"""
    try:
        client = get_redis()
        async for key in client.scan_iter(pattern):
            await client.delete(key)
    except Exception as e:
        logger.warning("cache_delete_pattern_failed", pattern=pattern, error=str(e))


async def add_token_to_blacklist(token: str, expire_seconds: int = 3600) -> None:
    """JWTトークンをブラックリストに追加"""
    try:
        client = get_redis()
        bl_key = f"blacklist:{token}"
        await client.set(bl_key, "1", ex=expire_seconds)
    except Exception as e:
        logger.warning("add_token_to_blacklist_failed", error=str(e))


async def is_token_blacklisted(token: str) -> bool:
    """トークンがブラックリストに含まれるか確認。失敗時はFalseを返す（graceful degradation）"""
    try:
        client = get_redis()
        bl_key = f"blacklist:{token}"
        result = await client.exists(bl_key)
        return bool(result)
    except Exception as e:
        logger.warning("is_token_blacklisted_failed", error=str(e))
        return False
