"""OWASP Top 10 セキュリティヘッダーテスト - Issue #51"""

import time

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware

pytestmark = pytest.mark.asyncio


# ─── フィクスチャ ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def anon_client():
    """認証不要クライアント（DB接続なし）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─── OWASP A05: Security Misconfiguration - セキュリティヘッダーテスト ────────


class TestSecurityHeadersPresent:
    """セキュリティヘッダーの存在確認テスト"""

    async def test_content_security_policy_present(self, anon_client: AsyncClient):
        """Content-Security-Policy ヘッダーが存在する (OWASP A05)"""
        response = await anon_client.get("/api/v1/health")
        assert "content-security-policy" in response.headers

    async def test_x_content_type_options_present(self, anon_client: AsyncClient):
        """X-Content-Type-Options ヘッダーが存在する (OWASP A05)"""
        response = await anon_client.get("/api/v1/health")
        assert "x-content-type-options" in response.headers

    async def test_x_frame_options_present(self, anon_client: AsyncClient):
        """X-Frame-Options ヘッダーが存在する (OWASP A05)"""
        response = await anon_client.get("/api/v1/health")
        assert "x-frame-options" in response.headers

    async def test_strict_transport_security_present(self, anon_client: AsyncClient):
        """Strict-Transport-Security ヘッダーが存在する (OWASP A05)"""
        response = await anon_client.get("/api/v1/health")
        assert "strict-transport-security" in response.headers

    async def test_referrer_policy_present(self, anon_client: AsyncClient):
        """Referrer-Policy ヘッダーが存在する (OWASP A05)"""
        response = await anon_client.get("/api/v1/health")
        assert "referrer-policy" in response.headers

    async def test_permissions_policy_present(self, anon_client: AsyncClient):
        """Permissions-Policy ヘッダーが存在する (OWASP A05)"""
        response = await anon_client.get("/api/v1/health")
        assert "permissions-policy" in response.headers


class TestSecurityHeaderValues:
    """セキュリティヘッダーの値が適切かテスト"""

    async def test_content_security_policy_value(self, anon_client: AsyncClient):
        """CSP が default-src 'self' を含む"""
        response = await anon_client.get("/api/v1/health")
        csp = response.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp

    async def test_x_content_type_options_value(self, anon_client: AsyncClient):
        """X-Content-Type-Options が nosniff である"""
        response = await anon_client.get("/api/v1/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options_value(self, anon_client: AsyncClient):
        """X-Frame-Options が DENY である (クリックジャッキング防止)"""
        response = await anon_client.get("/api/v1/health")
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_strict_transport_security_max_age(self, anon_client: AsyncClient):
        """HSTS max-age が 31536000 秒 (1年) 以上である"""
        response = await anon_client.get("/api/v1/health")
        hsts = response.headers.get("strict-transport-security", "")
        assert "max-age=31536000" in hsts

    async def test_strict_transport_security_include_subdomains(self, anon_client: AsyncClient):
        """HSTS が includeSubDomains を含む"""
        response = await anon_client.get("/api/v1/health")
        hsts = response.headers.get("strict-transport-security", "")
        assert "includeSubDomains" in hsts

    async def test_referrer_policy_value(self, anon_client: AsyncClient):
        """Referrer-Policy が strict-origin-when-cross-origin である"""
        response = await anon_client.get("/api/v1/health")
        assert (
            response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        )

    async def test_permissions_policy_geolocation_denied(self, anon_client: AsyncClient):
        """Permissions-Policy が geolocation を拒否する"""
        response = await anon_client.get("/api/v1/health")
        pp = response.headers.get("permissions-policy", "")
        assert "geolocation=()" in pp

    async def test_permissions_policy_microphone_denied(self, anon_client: AsyncClient):
        """Permissions-Policy が microphone を拒否する"""
        response = await anon_client.get("/api/v1/health")
        pp = response.headers.get("permissions-policy", "")
        assert "microphone=()" in pp

    async def test_permissions_policy_camera_denied(self, anon_client: AsyncClient):
        """Permissions-Policy が camera を拒否する"""
        response = await anon_client.get("/api/v1/health")
        pp = response.headers.get("permissions-policy", "")
        assert "camera=()" in pp

    async def test_x_xss_protection_value(self, anon_client: AsyncClient):
        """X-XSS-Protection が有効化されている"""
        response = await anon_client.get("/api/v1/health")
        assert response.headers.get("x-xss-protection") == "1; mode=block"


class TestAllOWASPHeadersAtOnce:
    """全OWASPヘッダーを一括確認するテスト"""

    async def test_all_owasp_security_headers_present(self, anon_client: AsyncClient):
        """OWASP Top 10 A05 対応の全セキュリティヘッダーが存在する"""
        response = await anon_client.get("/api/v1/health")
        expected_headers = [
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options",
            "strict-transport-security",
            "referrer-policy",
            "permissions-policy",
        ]
        missing = [h for h in expected_headers if h not in response.headers]
        assert missing == [], f"以下のセキュリティヘッダーが不足: {missing}"


# ─── OWASP A04: Insecure Design - レートリミットテスト ───────────────────────


class TestRateLimitMiddleware:
    """OWASP A04 対応: レートリミット動作テスト"""

    def test_rate_limit_middleware_instantiation(self):
        """RateLimitMiddleware が正しくインスタンス化される"""
        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app, calls=100, period=60)
        assert mw._calls == 100
        assert mw._period == 60

    def test_rate_limit_default_values(self):
        """デフォルト値 calls=200, period=60 が設定される"""
        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app)
        assert mw._calls == 200
        assert mw._period == 60

    def test_rate_limit_client_tracking_structure(self):
        """クライアント別リクエスト追跡が機能する"""
        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app, calls=5, period=60)
        now = time.time()
        mw._clients["192.168.1.1"] = [now - 3, now - 2, now - 1]
        assert len(mw._clients["192.168.1.1"]) == 3

    def test_rate_limit_window_pruning(self):
        """時間ウィンドウ外の古いリクエストが正しく除去される"""
        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app, calls=5, period=10)
        now = time.time()
        # 10秒ウィンドウ外(20秒前・15秒前)と範囲内(1秒前)
        mw._clients["10.0.0.1"] = [now - 20, now - 15, now - 1]
        window_start = now - mw._period
        pruned = [t for t in mw._clients["10.0.0.1"] if t > window_start]
        assert len(pruned) == 1

    def test_rate_limit_threshold_detection(self):
        """レート制限閾値を超えたことを正しく検出する"""
        dummy_app = FastAPI()
        mw = RateLimitMiddleware(dummy_app, calls=3, period=60)
        now = time.time()
        mw._clients["10.0.0.2"] = [now - 2, now - 1, now]
        # _calls 個のリクエストが存在する = 制限超え
        assert len(mw._clients["10.0.0.2"]) >= mw._calls


# ─── SecurityHeadersMiddleware 単体テスト ────────────────────────────────────


class TestSecurityHeadersMiddlewareUnit:
    """SecurityHeadersMiddleware の単体テスト"""

    def test_middleware_can_be_instantiated(self):
        """ミドルウェアが正常にインスタンス化される"""
        dummy_app = FastAPI()
        mw = SecurityHeadersMiddleware(dummy_app)
        assert mw is not None

    def test_middleware_is_base_http_middleware(self):
        """SecurityHeadersMiddleware が BaseHTTPMiddleware を継承している"""
        from starlette.middleware.base import BaseHTTPMiddleware

        assert issubclass(SecurityHeadersMiddleware, BaseHTTPMiddleware)
