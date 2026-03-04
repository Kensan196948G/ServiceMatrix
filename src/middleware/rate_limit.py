"""シンプルなインメモリレート制限"""
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 200, period: int = 60):
        super().__init__(app)
        self._calls = calls
        self._period = period
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        # テスト環境（testclient）はレート制限をスキップ
        if client_ip in ("testclient", "127.0.0.1", "unknown"):
            return await call_next(request)

        now = time.time()
        window_start = now - self._period

        # 古いリクエストを削除
        self._clients[client_ip] = [t for t in self._clients[client_ip] if t > window_start]

        if len(self._clients[client_ip]) >= self._calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        self._clients[client_ip].append(now)
        return await call_next(request)


rate_limit_middleware = RateLimitMiddleware
