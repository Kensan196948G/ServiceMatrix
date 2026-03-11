"""Redis キャッシュユーティリティ + インメモリTTLキャッシュ"""

import time
from typing import Any

import redis.asyncio as aioredis  # type: ignore[import-untyped]
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)


class TTLCache:
    """スレッドセーフなTTLキャッシュ（インメモリ）"""

    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        if key in self._store:
            value, expires_at = self._store[key]
            if time.time() < expires_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.time() + self.ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# アプリケーション全体で共有するキャッシュインスタンス
incident_cache = TTLCache(ttl=60)
change_cache = TTLCache(ttl=60)

_redis_client: aioredis.Redis | None = None
_redis_sentinel: Any | None = None
_redis_cluster_client: Any | None = None


def get_redis() -> aioredis.Redis:
    """Redisクライアントを取得（シングルトン・後方互換）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def get_redis_client() -> aioredis.Redis | Any:
    """Redis接続クライアントを返す（Sentinel / Cluster / Single を自動選択）"""
    global _redis_client, _redis_sentinel, _redis_cluster_client

    if settings.redis_sentinel_enabled:
        # Sentinel モード
        if _redis_sentinel is None:
            sentinel_hosts = []
            for host_port in settings.redis_sentinel_hosts.split(","):
                host_port = host_port.strip()
                if not host_port:
                    continue
                if ":" in host_port:
                    host, port_str = host_port.rsplit(":", 1)
                    sentinel_hosts.append((host, int(port_str)))
                else:
                    sentinel_hosts.append((host_port, 26379))
            if not sentinel_hosts:
                sentinel_hosts = [("localhost", 26379)]
            _redis_sentinel = aioredis.Sentinel(
                sentinel_hosts,
                socket_timeout=0.5,
                decode_responses=True,
            )
        return _redis_sentinel.master_for(
            settings.redis_sentinel_master,
            socket_timeout=0.5,
        )

    if settings.redis_cluster_enabled:
        # Cluster モード
        if _redis_cluster_client is None:
            from redis.asyncio.cluster import RedisCluster  # type: ignore[import-untyped]

            _redis_cluster_client = RedisCluster.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        return _redis_cluster_client

    # Single モード（既存）
    return get_redis()


async def health_check_redis() -> dict:
    """Redis ヘルスチェック情報を返す"""
    if settings.redis_sentinel_enabled:
        mode = "sentinel"
    elif settings.redis_cluster_enabled:
        mode = "cluster"
    else:
        mode = "single"

    try:
        client = await get_redis_client()
        start = time.monotonic()
        await client.ping()
        latency_ms = (time.monotonic() - start) * 1000
        return {
            "status": "ok",
            "mode": mode,
            "latency_ms": round(latency_ms, 3),
        }
    except Exception as e:
        logger.warning("redis_health_check_failed", error=str(e))
        return {
            "status": "unavailable",
            "mode": mode,
            "latency_ms": None,
        }


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
