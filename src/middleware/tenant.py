"""テナント分離ミドルウェア - Issue #75 マルチテナント基盤

X-Tenant-ID ヘッダーを解析し、リクエストコンテキストにテナント情報を注入する。
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class TenantMiddleware(BaseHTTPMiddleware):
    """X-Tenant-ID ヘッダーからテナント ID を解析し request.state に注入する。

    テナント ID が指定された場合のみ検証する（省略時はシステム管理操作として扱う）。
    """

    # テナント分離が不要なパス（ヘルスチェック・認証等）
    EXCLUDED_PATHS = {"/api/v1/health", "/api/v1/auth/login", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.tenant_id = None

        # 除外パスはテナントヘッダーを検証しない
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        tenant_header = request.headers.get("X-Tenant-ID", "").strip()

        if tenant_header:
            try:
                request.state.tenant_id = uuid.UUID(tenant_header)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"Invalid X-Tenant-ID format: '{tenant_header}'"},
                )

        response = await call_next(request)

        if request.state.tenant_id:
            response.headers["X-Tenant-ID"] = str(request.state.tenant_id)

        return response
