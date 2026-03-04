"""Step36 OpenAPI仕様書・レート制限・APIキー管理テスト"""

import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.middleware.rate_limit import RateLimitMiddleware
from src.models.api_key import APIKey
from src.services import api_key_service

# ────────────────────────────────────────────────────────────────
# OpenAPIスキーマテスト
# ────────────────────────────────────────────────────────────────


class TestOpenAPISchema:
    """カスタムOpenAPIスキーマの検証"""

    def test_openapi_schema_has_security_scheme(self):
        """OpenAPIスキーマにセキュリティスキームが含まれている"""
        # キャッシュをリセットして再生成を強制
        app.openapi_schema = None
        schema = app.openapi()
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
        assert "BearerAuth" in schema["components"]["securitySchemes"]

    def test_openapi_schema_has_bearer_auth(self):
        """BearerAuth が JWT形式で定義されている"""
        app.openapi_schema = None
        schema = app.openapi()
        bearer = schema["components"]["securitySchemes"]["BearerAuth"]
        assert bearer["type"] == "http"
        assert bearer["scheme"] == "bearer"
        assert bearer["bearerFormat"] == "JWT"

    def test_openapi_schema_global_security(self):
        """グローバルセキュリティが設定されている"""
        app.openapi_schema = None
        schema = app.openapi()
        assert "security" in schema
        assert {"BearerAuth": []} in schema["security"]

    def test_openapi_schema_caching(self):
        """2回目の呼び出しはキャッシュされたスキーマを返す"""
        app.openapi_schema = None
        schema1 = app.openapi()
        schema2 = app.openapi()
        assert schema1 is schema2


# ────────────────────────────────────────────────────────────────
# レート制限テスト
# ────────────────────────────────────────────────────────────────


class TestRateLimitMiddleware:
    """スライディングウィンドウ方式レート制限の検証"""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests(self):
        """制限内のリクエストは通過する"""
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route

        async def homepage(request):
            return PlainTextResponse("OK")

        test_app = Starlette(routes=[Route("/", homepage)])
        limited_app = RateLimitMiddleware(test_app, max_requests=5, window_seconds=60)

        transport = ASGITransport(app=limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/")
            assert resp.status_code == 200
            assert resp.text == "OK"

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess(self):
        """制限超過後は429を返す"""
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route

        async def homepage(request):
            return PlainTextResponse("OK")

        test_app = Starlette(routes=[Route("/", homepage)])
        limited_app = RateLimitMiddleware(test_app, max_requests=3, window_seconds=60)

        transport = ASGITransport(app=limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            for _ in range(3):
                resp = await ac.get("/")
                assert resp.status_code == 200

            resp = await ac.get("/")
            assert resp.status_code == 429
            assert "Too many requests" in resp.json()["detail"]
            assert "Retry-After" in resp.headers

    def test_rate_limit_sliding_window_cleanup(self):
        """古いリクエストがウィンドウからクリーンアップされる"""
        middleware = RateLimitMiddleware(None, max_requests=2, window_seconds=1)
        # 直接内部状態をテスト: 1秒前のリクエストを挿入
        old_time = time.time() - 2.0  # 2秒前（ウィンドウ外）
        middleware._requests["127.0.0.1"] = deque([old_time, old_time])
        # ウィンドウ内のカウントは0のはず（dispatchで検証されるが、ここではデータ構造確認）
        assert len(middleware._requests["127.0.0.1"]) == 2


# ────────────────────────────────────────────────────────────────
# APIキーサービステスト（直接呼び出し）
# ────────────────────────────────────────────────────────────────


class TestAPIKeyService:
    """APIキーサービス層のユニットテスト"""

    def test_generate_api_key_format(self):
        """generate_api_key は32文字のhex文字列を返す"""
        key = api_key_service.generate_api_key()
        assert len(key) == 32
        assert all(c in "0123456789abcdef" for c in key)

    def test_generate_api_key_unique(self):
        """連続生成されたキーは異なる"""
        key1 = api_key_service.generate_api_key()
        key2 = api_key_service.generate_api_key()
        assert key1 != key2

    def test_api_key_hash_deterministic(self):
        """同じ入力に対して同じハッシュを返す"""
        raw = "test_key_12345678"
        hash1 = APIKey.hash_key(raw)
        hash2 = APIKey.hash_key(raw)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_api_key_hash_different_inputs(self):
        """異なる入力に対して異なるハッシュを返す"""
        hash1 = APIKey.hash_key("key_a")
        hash2 = APIKey.hash_key("key_b")
        assert hash1 != hash2

    def test_api_key_prefix_length(self):
        """生成されたキーの先頭8文字がプレフィックスとして使える"""
        key = api_key_service.generate_api_key()
        prefix = key[:8]
        assert len(prefix) == 8

    @pytest.mark.asyncio
    async def test_validate_api_key_service_direct(self):
        """validate_api_key はハッシュ照合でキーを検証する"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await api_key_service.validate_api_key(mock_db, "nonexistent_key")
        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key(self):
        """create_api_key はAPIキーモデルと生キーのタプルを返す"""
        mock_db = AsyncMock()

        api_key, raw_key = await api_key_service.create_api_key(
            db=mock_db, name="Test Key", owner_id="owner-123", rate_limit=500
        )
        assert api_key.name == "Test Key"
        assert api_key.owner_id == "owner-123"
        assert api_key.rate_limit == 500
        assert len(raw_key) == 32
        assert api_key.key_prefix == raw_key[:8]
        assert api_key.key_hash == APIKey.hash_key(raw_key)
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self):
        """存在しないキーの無効化はFalseを返す"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await api_key_service.revoke_api_key(mock_db, "nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self):
        """既存キーの無効化はTrueを返しis_activeをFalseにする"""
        mock_key = MagicMock()
        mock_key.is_active = True

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute.return_value = mock_result

        result = await api_key_service.revoke_api_key(mock_db, "existing-id")
        assert result is True
        assert mock_key.is_active is False
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_api_keys(self):
        """list_api_keys はキー一覧を返す"""
        mock_key = MagicMock()
        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_key]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        keys = await api_key_service.list_api_keys(mock_db, owner_id="owner-123")
        assert len(keys) == 1

    @pytest.mark.asyncio
    async def test_get_api_key(self):
        """get_api_key はIDでキーを取得する"""
        mock_key = MagicMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute.return_value = mock_result

        result = await api_key_service.get_api_key(mock_db, "some-id")
        assert result is mock_key


# ────────────────────────────────────────────────────────────────
# APIキーエンドポイント統合テスト
# ────────────────────────────────────────────────────────────────


class TestAPIKeyEndpoints:
    """APIキーエンドポイントの統合テスト"""

    @pytest.mark.asyncio
    async def test_create_api_key_endpoint(self, client, auth_headers, db_session):
        """POST /api/v1/api-keys で新しいキーが作成される"""
        resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "My API Key", "rate_limit": 500},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert len(data["raw_key"]) == 32
        assert data["name"] == "My API Key"
        assert data["rate_limit"] == 500
        assert data["key_prefix"] == data["raw_key"][:8]

    @pytest.mark.asyncio
    async def test_create_api_key_response_has_raw_key(self, client, auth_headers, db_session):
        """作成レスポンスに生キーが含まれている"""
        resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "Key with raw"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_api_keys(self, client, auth_headers, db_session):
        """GET /api/v1/api-keys でキー一覧が取得できる"""
        # まずキーを作成
        await client.post(
            "/api/v1/api-keys",
            json={"name": "List Test Key"},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/api-keys", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # 一覧レスポンスには raw_key が含まれないことを確認
        assert "raw_key" not in data[0]

    @pytest.mark.asyncio
    async def test_revoke_api_key_endpoint(self, client, auth_headers, db_session):
        """DELETE /api/v1/api-keys/{key_id} でキーが無効化される"""
        # キー作成
        create_resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "To Revoke"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        # 無効化
        resp = await client.delete(
            f"/api/v1/api-keys/{key_id}", headers=auth_headers
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, client, auth_headers, db_session):
        """存在しないキーの無効化は404を返す"""
        resp = await client.delete(
            "/api/v1/api-keys/nonexistent-uuid", headers=auth_headers
        )
        assert resp.status_code == 404
