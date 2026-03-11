"""Cache-Aside デコレータ テストスイート"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

# ── cache_decorator ユニットテスト ─────────────────────────────────────────────


class TestCacheKey:
    def test_build_cache_key_format(self):
        """キャッシュキーが正しいプレフィックスを持つ"""
        from src.core.cache_decorator import CACHE_PREFIX, _build_cache_key

        key = _build_cache_key("incidents_list", "arg1", limit=10)
        assert key.startswith(f"{CACHE_PREFIX}:incidents_list:")

    def test_build_cache_key_deterministic(self):
        """同一引数は同一キーを生成する"""
        from src.core.cache_decorator import _build_cache_key

        key1 = _build_cache_key("test", 1, 2, a="b")
        key2 = _build_cache_key("test", 1, 2, a="b")
        assert key1 == key2

    def test_build_cache_key_different_args(self):
        """異なる引数は異なるキーを生成する"""
        from src.core.cache_decorator import _build_cache_key

        key1 = _build_cache_key("test", page=1)
        key2 = _build_cache_key("test", page=2)
        assert key1 != key2

    def test_build_cache_key_different_prefix(self):
        """異なるプレフィックスは異なるキーを生成する"""
        from src.core.cache_decorator import _build_cache_key

        key1 = _build_cache_key("incidents_list")
        key2 = _build_cache_key("cmdb_list")
        assert key1 != key2


class TestCacheResponseDecorator:
    """@cache_response デコレータのテスト"""

    def _make_cached_func(self, ttl: int = 30):
        from src.core.cache_decorator import cache_response

        call_count = {"n": 0}

        @cache_response("test_prefix", ttl=ttl)
        async def my_func(x: int):
            call_count["n"] += 1
            return {"value": x * 2}

        return my_func, call_count

    import pytest

    @pytest.mark.asyncio
    async def test_cache_miss_calls_function(self):
        """キャッシュミス時に関数を呼び出す"""
        func, call_count = self._make_cached_func()
        with (
            patch("src.core.cache_decorator.cache_get", new=AsyncMock(return_value=None)),
            patch("src.core.cache_decorator.cache_set", new=AsyncMock()),
        ):
            result = await func(5)
        assert result == {"value": 10}
        assert call_count["n"] == 1

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self):
        """キャッシュヒット時にキャッシュから返す"""
        func, call_count = self._make_cached_func()
        cached_data = json.dumps({"value": 42})
        with (
            patch("src.core.cache_decorator.cache_get", new=AsyncMock(return_value=cached_data)),
            patch("src.core.cache_decorator.cache_set", new=AsyncMock()),
        ):
            result = await func(21)
        assert result == {"value": 42}
        assert call_count["n"] == 0  # 関数は呼ばれない

    @pytest.mark.asyncio
    async def test_cache_set_called_on_miss(self):
        """キャッシュミス後に cache_set が呼ばれる"""
        func, _ = self._make_cached_func(ttl=60)
        mock_set = AsyncMock()
        with (
            patch("src.core.cache_decorator.cache_get", new=AsyncMock(return_value=None)),
            patch("src.core.cache_decorator.cache_set", new=mock_set),
        ):
            await func(3)
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        assert call_args[1]["ttl"] == 60

    @pytest.mark.asyncio
    async def test_cache_not_called_when_skip(self):
        """skip_cache_if が True の場合はキャッシュをスキップする"""
        from src.core.cache_decorator import cache_response

        call_count = {"n": 0}

        @cache_response("skip_test", ttl=30, skip_cache_if=lambda x: x > 10)
        async def my_func(x: int):
            call_count["n"] += 1
            return {"x": x}

        mock_get = AsyncMock(return_value=None)
        mock_set = AsyncMock()
        with (
            patch("src.core.cache_decorator.cache_get", new=mock_get),
            patch("src.core.cache_decorator.cache_set", new=mock_set),
        ):
            await my_func(999)  # skip_cache_if → True
        # キャッシュを試みずに関数を実行
        mock_get.assert_not_called()
        assert call_count["n"] == 1

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_name(self):
        """デコレータが関数名を保持する（functools.wraps）"""
        from src.core.cache_decorator import cache_response

        @cache_response("test", ttl=10)
        async def my_original_func():
            return {}

        assert my_original_func.__name__ == "my_original_func"

    def test_decorator_attaches_metadata(self):
        """デコレータがメタデータを付与する"""
        from src.core.cache_decorator import cache_response

        @cache_response("meta_test", ttl=120)
        async def my_func():
            return {}

        assert my_func.cache_prefix == "meta_test"
        assert my_func.cache_ttl == 120
        assert hasattr(my_func, "invalidate")

    @pytest.mark.asyncio
    async def test_invalidate_calls_delete_pattern(self):
        """invalidate メソッドがキャッシュを削除する"""
        from src.core.cache_decorator import cache_response

        @cache_response("inv_test", ttl=30)
        async def my_func(x: int):
            return {"x": x}

        mock_delete = AsyncMock()
        with patch("src.core.cache_decorator.cache_delete_pattern", new=mock_delete):
            await my_func.invalidate(5)
        mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_decode_error_falls_through(self):
        """不正なキャッシュデータは関数を再実行する"""
        func, call_count = self._make_cached_func()
        with (
            patch(
                "src.core.cache_decorator.cache_get",
                new=AsyncMock(return_value="INVALID_JSON{{"),
            ),
            patch("src.core.cache_decorator.cache_set", new=AsyncMock()),
        ):
            result = await func(7)
        assert result == {"value": 14}
        assert call_count["n"] == 1


class TestInvalidateByPrefix:
    import pytest

    @pytest.mark.asyncio
    async def test_invalidate_by_prefix(self):
        """invalidate_by_prefix がパターンで削除する"""
        from src.core.cache_decorator import invalidate_by_prefix

        mock_delete = AsyncMock()
        with patch("src.core.cache_decorator.cache_delete_pattern", new=mock_delete):
            await invalidate_by_prefix("incidents_list")
        mock_delete.assert_called_once_with("sm:cache:incidents_list:*")


class TestTTLConstants:
    def test_ttl_values(self):
        """TTL定数が正しい値を持つ"""
        from src.core.cache_decorator import (
            TTL_CMDB,
            TTL_DEFAULT,
            TTL_HEALTH,
            TTL_INCIDENTS,
            TTL_REPORTS,
            TTL_SLA_DASHBOARD,
        )

        assert TTL_HEALTH < TTL_INCIDENTS < TTL_SLA_DASHBOARD < TTL_CMDB < TTL_REPORTS
        assert TTL_DEFAULT == 60


# ── キャッシュ管理API テスト ──────────────────────────────────────────────────


class TestCacheAPI:
    def setup_method(self):
        from fastapi.testclient import TestClient

        from src.main import app

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_get_cache_stats_returns_200(self):
        """/api/v1/cache/stats が200を返す"""
        mock_redis = AsyncMock()
        mock_redis.scan_iter = AsyncMock(return_value=iter([]))

        async def mock_scan_iter(pattern, count=100):
            return
            yield  # noqa: unreachable - async generator

        mock_redis.scan_iter = mock_scan_iter
        with patch("src.api.v1.cache.get_redis", return_value=mock_redis):
            resp = self.client.get("/api/v1/cache/stats")
        assert resp.status_code == 200

    def test_get_cache_stats_returns_list(self):
        """/api/v1/cache/stats がリスト形式を返す"""
        mock_redis = AsyncMock()

        async def mock_scan_iter(pattern, count=100):
            return
            yield  # noqa: unreachable

        mock_redis.scan_iter = mock_scan_iter
        with patch("src.api.v1.cache.get_redis", return_value=mock_redis):
            resp = self.client.get("/api/v1/cache/stats")
        data = resp.json()
        assert isinstance(data, list)

    def test_get_cache_stats_by_prefix_valid(self):
        """/api/v1/cache/stats/{prefix} が有効なプレフィックスで200を返す"""
        mock_redis = AsyncMock()

        async def mock_scan_iter(pattern, count=100):
            return
            yield  # noqa: unreachable

        mock_redis.scan_iter = mock_scan_iter
        with patch("src.api.v1.cache.get_redis", return_value=mock_redis):
            resp = self.client.get("/api/v1/cache/stats/incidents_list")
        assert resp.status_code == 200

    def test_get_cache_stats_by_prefix_invalid(self):
        """/api/v1/cache/stats/{prefix} が無効なプレフィックスで404を返す"""
        resp = self.client.get("/api/v1/cache/stats/unknown_prefix")
        assert resp.status_code == 404

    def test_delete_cache_by_prefix_valid(self):
        """/api/v1/cache/{prefix} DELETE が有効なプレフィックスで200を返す"""
        with patch("src.api.v1.cache.cache_delete_pattern", new=AsyncMock()):
            resp = self.client.delete("/api/v1/cache/incidents_list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert "incidents_list" in data["message"]

    def test_delete_cache_by_prefix_invalid(self):
        """/api/v1/cache/{prefix} DELETE が無効なプレフィックスで404を返す"""
        resp = self.client.delete("/api/v1/cache/unknown_prefix")
        assert resp.status_code == 404
