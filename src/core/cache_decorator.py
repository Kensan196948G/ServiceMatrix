"""Cache-Aside パターン実装 - APIレスポンスキャッシュデコレータ"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable
from typing import Any

import structlog

from src.core.cache import cache_delete_pattern, cache_get, cache_set

logger = structlog.get_logger(__name__)

# ── キャッシュTTL推奨値 ────────────────────────────────────────────────────────

TTL_HEALTH = 10          # ヘルスチェック: 10秒
TTL_INCIDENTS = 30       # インシデント一覧: 30秒
TTL_SLA_DASHBOARD = 60  # SLAダッシュボード: 60秒
TTL_CMDB = 120           # CMDB一覧: 120秒
TTL_REPORTS = 300        # レポート: 5分
TTL_DEFAULT = 60         # デフォルト: 60秒

# ── キャッシュキープレフィックス ────────────────────────────────────────────────

CACHE_PREFIX = "sm:cache"


def _build_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """キャッシュキーを生成する。

    引数とキーワード引数をハッシュ化して一意のキーを作成する。
    """
    key_data = {"args": list(args), "kwargs": kwargs}
    key_hash = hashlib.sha256(
        json.dumps(key_data, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f"{CACHE_PREFIX}:{prefix}:{key_hash}"


def cache_response(
    key_prefix: str,
    ttl: int = TTL_DEFAULT,
    *,
    skip_cache_if: Callable[..., bool] | None = None,
) -> Callable:
    """APIレスポンスをRedisにキャッシュするデコレータ。

    Args:
        key_prefix: キャッシュキープレフィックス (例: "incidents_list")
        ttl: TTL秒数
        skip_cache_if: Trueを返す場合にキャッシュをスキップする述語関数

    Usage:
        @router.get("/incidents")
        @cache_response("incidents_list", ttl=TTL_INCIDENTS)
        async def list_incidents(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # キャッシュスキップ判定
            if skip_cache_if is not None and skip_cache_if(*args, **kwargs):
                return await func(*args, **kwargs)

            cache_key = _build_cache_key(key_prefix, *args, **kwargs)

            # キャッシュ読み取り（Cache-Aside: Read）
            cached = await cache_get(cache_key)
            if cached is not None:
                try:
                    result = json.loads(cached)
                    logger.debug("cache_hit", key=cache_key, prefix=key_prefix)
                    return result
                except json.JSONDecodeError:
                    logger.warning("cache_decode_error", key=cache_key)

            # キャッシュミス → 関数実行
            logger.debug("cache_miss", key=cache_key, prefix=key_prefix)
            result = await func(*args, **kwargs)

            # キャッシュ書き込み（Cache-Aside: Write）
            try:
                serialized = json.dumps(result, default=str)
                await cache_set(cache_key, serialized, ttl=ttl)
            except (TypeError, ValueError) as e:
                logger.warning("cache_serialize_error", key=cache_key, error=str(e))

            return result

        # キャッシュ無効化メソッドをデコレートした関数に付与
        async def invalidate(*args: Any, **kwargs: Any) -> None:
            cache_key = _build_cache_key(key_prefix, *args, **kwargs)
            await cache_delete_pattern(cache_key)

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        wrapper.cache_prefix = key_prefix  # type: ignore[attr-defined]
        wrapper.cache_ttl = ttl  # type: ignore[attr-defined]

        return wrapper

    return decorator


async def invalidate_by_prefix(prefix: str) -> None:
    """指定プレフィックスのキャッシュを全削除する。

    書き込み系操作（CREATE/UPDATE/DELETE）後に呼び出す。
    """
    pattern = f"{CACHE_PREFIX}:{prefix}:*"
    await cache_delete_pattern(pattern)
    logger.info("cache_invalidated", prefix=prefix, pattern=pattern)
