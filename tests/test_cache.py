"""Redisキャッシュユーティリティのテスト"""
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCacheModuleExists:
    def test_cache_module_exists(self):
        """cache.pyが存在し、主要関数がimport可能であること"""
        from src.core import cache
        assert hasattr(cache, "get_redis")
        assert hasattr(cache, "cache_get")
        assert hasattr(cache, "cache_set")
        assert hasattr(cache, "cache_delete")
        assert hasattr(cache, "cache_delete_pattern")
        assert hasattr(cache, "add_token_to_blacklist")
        assert hasattr(cache, "is_token_blacklisted")

    def test_get_redis_returns_client(self):
        """get_redis()がredis.asyncio.Redisクライアントを返すこと"""
        import redis.asyncio as aioredis
        from src.core.cache import get_redis
        client = get_redis()
        assert isinstance(client, aioredis.Redis)


@pytest.mark.asyncio
class TestCacheSetAndGet:
    async def test_cache_set_and_get(self):
        """cache_set後にcache_getで同じ値が返ること"""
        from src.core.cache import cache_get, cache_set

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value="hello")
        mock_client.set = AsyncMock(return_value=True)

        with patch("src.core.cache.get_redis", return_value=mock_client):
            await cache_set("mykey", "hello", ttl=60)
            result = await cache_get("mykey")

        mock_client.set.assert_awaited_once_with("mykey", "hello", ex=60)
        mock_client.get.assert_awaited_once_with("mykey")
        assert result == "hello"

    async def test_cache_delete(self):
        """cache_delete後にcache_getがNoneを返すこと"""
        from src.core.cache import cache_delete, cache_get

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=1)
        mock_client.get = AsyncMock(return_value=None)

        with patch("src.core.cache.get_redis", return_value=mock_client):
            await cache_delete("mykey")
            result = await cache_get("mykey")

        mock_client.delete.assert_awaited_once_with("mykey")
        assert result is None


@pytest.mark.asyncio
class TestTokenBlacklist:
    async def test_token_blacklist_add_and_check(self):
        """add_token_to_blacklist後にis_token_blacklisted=Trueであること"""
        from src.core.cache import add_token_to_blacklist, is_token_blacklisted

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        mock_client.exists = AsyncMock(return_value=1)

        token = "test.jwt.token"
        with patch("src.core.cache.get_redis", return_value=mock_client):
            await add_token_to_blacklist(token, expire_seconds=3600)
            result = await is_token_blacklisted(token)

        mock_client.set.assert_awaited_once_with(f"blacklist:{token}", "1", ex=3600)
        mock_client.exists.assert_awaited_once_with(f"blacklist:{token}")
        assert result is True

    async def test_token_not_blacklisted(self):
        """追加していないトークンはis_token_blacklisted=Falseであること"""
        from src.core.cache import is_token_blacklisted

        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(return_value=0)

        with patch("src.core.cache.get_redis", return_value=mock_client):
            result = await is_token_blacklisted("unknown.token")

        assert result is False


@pytest.mark.asyncio
class TestRedisFallback:
    async def test_redis_failure_graceful(self):
        """Redis接続失敗時にNone/Falseを返し、例外を投げないこと"""
        from src.core.cache import cache_get, is_token_blacklisted

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_client.exists = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch("src.core.cache.get_redis", return_value=mock_client):
            cache_result = await cache_get("some_key")
            blacklist_result = await is_token_blacklisted("some_token")

        assert cache_result is None
        assert blacklist_result is False
