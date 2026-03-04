"""テナント解決ミドルウェア - X-Tenant-IDヘッダーからテナントを特定"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TenantMiddleware(BaseHTTPMiddleware):
    """リクエストヘッダーからテナントIDを解決し、request.stateに設定する"""

    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID")
        request.state.tenant_id = tenant_id
        return await call_next(request)
