"""セキュリティ機能テスト"""
import time

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.main import app
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware


# ─── レート制限ミドルウェアテスト ──────────────────────────────────────────


class TestRateLimitMiddleware:
    def test_rate_limit_middleware_instantiation(self):
        """RateLimitMiddlewareが正しく初期化される"""
        from fastapi import FastAPI

        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app, calls=10, period=60)
        assert mw._calls == 10
        assert mw._period == 60

    def test_rate_limit_default_values(self):
        """デフォルト値が正しく設定される"""
        from fastapi import FastAPI

        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app)
        assert mw._calls == 200
        assert mw._period == 60

    def test_rate_limit_client_tracking(self):
        """クライアントIPのリクエスト追跡が機能する"""
        from fastapi import FastAPI

        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app, calls=5, period=60)
        now = time.time()
        mw._clients["127.0.0.1"] = [now - 1, now - 2, now - 3]
        assert len(mw._clients["127.0.0.1"]) == 3

    def test_rate_limit_old_requests_pruned(self):
        """期間外の古いリクエストが削除される"""
        from fastapi import FastAPI

        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app, calls=5, period=10)
        now = time.time()
        # 期間外のリクエストを追加
        mw._clients["10.0.0.1"] = [now - 20, now - 15, now - 1]
        window_start = now - mw._period
        pruned = [t for t in mw._clients["10.0.0.1"] if t > window_start]
        assert len(pruned) == 1  # now-1 だけ残る


# ─── セキュリティヘッダーミドルウェアテスト ──────────────────────────────


class TestSecurityHeadersMiddleware:
    def test_security_headers_middleware_instantiation(self):
        """SecurityHeadersMiddlewareが正しく初期化される"""
        from fastapi import FastAPI

        dummy_app = FastAPI()
        mw = SecurityHeadersMiddleware(dummy_app)
        assert mw is not None

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        """セキュリティヘッダーがレスポンスに含まれる"""
        response = await client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert response.headers.get("Permissions-Policy") is not None

    @pytest.mark.asyncio
    async def test_x_content_type_options(self, client: AsyncClient):
        """X-Content-Type-Options が nosniff である"""
        response = await client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options(self, client: AsyncClient):
        """X-Frame-Options が DENY である"""
        response = await client.get("/api/v1/health")
        assert response.headers.get("X-Frame-Options") == "DENY"


# ─── CORS設定テスト ───────────────────────────────────────────────────────


class TestCORSSettings:
    def test_allowed_origins_configured(self):
        """CORS allowed_originsが設定されている"""
        assert isinstance(settings.allowed_origins, list)
        assert len(settings.allowed_origins) > 0

    def test_rate_limit_settings(self):
        """レート制限設定が正しく読み込まれる"""
        assert settings.rate_limit_per_minute == 200
        assert settings.rate_limit_enabled is True

    def test_security_headers_settings(self):
        """セキュリティヘッダー設定が正しく読み込まれる"""
        assert settings.security_headers_enabled is True

    def test_allowed_hosts_configured(self):
        """allowed_hostsが設定されている"""
        assert isinstance(settings.allowed_hosts, list)
        assert "localhost" in settings.allowed_hosts


# ─── 詳細ヘルスチェックテスト ─────────────────────────────────────────────


class TestDetailedHealthCheck:
    @pytest.mark.asyncio
    async def test_detailed_health_returns_200(self, client: AsyncClient):
        """詳細ヘルスチェックが200を返す"""
        response = await client.get("/api/v1/health/detailed")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_detailed_health_response_structure(self, client: AsyncClient):
        """詳細ヘルスチェックのレスポンス構造が正しい"""
        response = await client.get("/api/v1/health/detailed")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data

    @pytest.mark.asyncio
    async def test_detailed_health_services_keys(self, client: AsyncClient):
        """詳細ヘルスチェックのservicesに必要なキーが存在する"""
        response = await client.get("/api/v1/health/detailed")
        services = response.json()["services"]
        assert "api" in services
        assert "database" in services
        assert "redis" in services

    @pytest.mark.asyncio
    async def test_detailed_health_version(self, client: AsyncClient):
        """詳細ヘルスチェックにバージョン情報が含まれる"""
        response = await client.get("/api/v1/health/detailed")
        data = response.json()
        assert data["version"] == settings.app_version

    @pytest.mark.asyncio
    async def test_detailed_health_environment(self, client: AsyncClient):
        """詳細ヘルスチェックに環境情報が含まれる"""
        response = await client.get("/api/v1/health/detailed")
        data = response.json()
        assert data["environment"] == settings.environment
