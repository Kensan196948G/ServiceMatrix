"""APIパフォーマンステスト - Issue #49"""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio


async def test_ttl_cache_get_set():
    """TTLCache: 基本的な get/set 動作"""
    from src.core.cache import TTLCache
    cache = TTLCache(ttl=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


async def test_ttl_cache_expiry():
    """TTLCache: TTL 超過後は None を返す"""
    from src.core.cache import TTLCache
    cache = TTLCache(ttl=0)  # 即時期限切れ
    cache.set("key1", "value1")
    time.sleep(0.01)
    assert cache.get("key1") is None


async def test_ttl_cache_invalidate():
    """TTLCache: invalidate でキャッシュを削除"""
    from src.core.cache import TTLCache
    cache = TTLCache(ttl=60)
    cache.set("key1", "value1")
    cache.invalidate("key1")
    assert cache.get("key1") is None


async def test_ttl_cache_clear():
    """TTLCache: clear で全キャッシュを削除"""
    from src.core.cache import TTLCache
    cache = TTLCache(ttl=60)
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


async def test_ttl_cache_missing_key():
    """TTLCache: 存在しないキーは None を返す"""
    from src.core.cache import TTLCache
    cache = TTLCache(ttl=60)
    assert cache.get("nonexistent") is None
