"""Redis HA (Sentinel / Cluster / Single) テスト
Issue #59: Redis Cluster HA構成対応
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── graceful degradation テスト ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_get_with_connection_failure():
    """Redis接続失敗時に cache_get は None を返す（graceful degradation）"""
    from src.core import cache as cache_module

    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("Redis unavailable")

    with patch.object(cache_module, "get_redis", return_value=mock_client):
        result = await cache_module.cache_get("test_key")

    assert result is None


@pytest.mark.asyncio
async def test_cache_set_with_connection_failure():
    """Redis接続失敗時も cache_set は例外を投げない（graceful degradation）"""
    from src.core import cache as cache_module

    mock_client = AsyncMock()
    mock_client.set.side_effect = ConnectionError("Redis unavailable")

    with patch.object(cache_module, "get_redis", return_value=mock_client):
        # 例外が発生しないことを確認
        await cache_module.cache_set("test_key", "test_value")


# ─── ヘルスチェック テスト ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_redis_ok():
    """Redis正常時のヘルスチェックは status=ok を返す"""
    from src.core import cache as cache_module

    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    with patch.object(cache_module, "get_redis_client", new=AsyncMock(return_value=mock_client)):
        result = await cache_module.health_check_redis()

    assert result["status"] == "ok"
    assert result["mode"] in ("single", "sentinel", "cluster")
    assert isinstance(result["latency_ms"], float)


@pytest.mark.asyncio
async def test_health_check_redis_unavailable():
    """Redis障害時のヘルスチェックは status=unavailable を返す"""
    from src.core import cache as cache_module

    mock_client = AsyncMock()
    mock_client.ping.side_effect = ConnectionError("Redis down")

    with patch.object(cache_module, "get_redis_client", new=AsyncMock(return_value=mock_client)):
        result = await cache_module.health_check_redis()

    assert result["status"] == "unavailable"
    assert result["latency_ms"] is None


@pytest.mark.asyncio
async def test_health_endpoint_includes_redis(client):
    """/api/v1/health レスポンスにRedis情報が含まれる"""
    from src.core import cache as cache_module

    mock_redis_info = {
        "status": "ok",
        "mode": "single",
        "latency_ms": 0.5,
    }

    with patch("src.api.v1.health.health_check_redis", new=AsyncMock(return_value=mock_redis_info)):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert "redis" in data
    assert data["redis"]["status"] == "ok"
    assert data["redis"]["mode"] == "single"


# ─── Sentinel モード テスト ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_redis_client_sentinel_mode():
    """Sentinel モード有効時は Sentinel クライアントを返す"""
    from src.core import cache as cache_module
    from src.core.config import settings

    # キャッシュされたクライアントをリセット
    original_sentinel = cache_module._redis_sentinel
    cache_module._redis_sentinel = None

    mock_sentinel_instance = MagicMock()
    mock_master = AsyncMock()
    mock_sentinel_instance.master_for.return_value = mock_master

    try:
        with patch.object(settings, "redis_sentinel_enabled", True), \
             patch.object(settings, "redis_sentinel_hosts", "localhost:26379"), \
             patch.object(settings, "redis_sentinel_master", "mymaster"), \
             patch("redis.asyncio.Sentinel", return_value=mock_sentinel_instance):
            client = await cache_module.get_redis_client()

        assert client is mock_master
        mock_sentinel_instance.master_for.assert_called_once_with(
            "mymaster", socket_timeout=0.5
        )
    finally:
        cache_module._redis_sentinel = original_sentinel


@pytest.mark.asyncio
async def test_get_redis_client_single_mode():
    """デフォルト（Single）モードで get_redis が呼ばれる"""
    from src.core import cache as cache_module
    from src.core.config import settings

    mock_client = MagicMock()

    with patch.object(settings, "redis_sentinel_enabled", False), \
         patch.object(settings, "redis_cluster_enabled", False), \
         patch.object(cache_module, "get_redis", return_value=mock_client):
        client = await cache_module.get_redis_client()

    assert client is mock_client
