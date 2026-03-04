"""レート制限ミドルウェア - スライディングウィンドウ方式"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IPアドレスベースのスライディングウィンドウレート制限"""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        # 古いリクエストを削除
        req_times = self._requests[client_ip]
        while req_times and req_times[0] < window_start:
            req_times.popleft()

        if len(req_times) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry later."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        req_times.append(now)
        return await call_next(request)
