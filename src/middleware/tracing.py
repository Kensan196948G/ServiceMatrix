"""OpenTelemetry トレーシング middleware - Issue #74

全リクエストに trace_id を付与し、X-Trace-Id レスポンスヘッダーで公開する。
"""

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.telemetry import get_current_trace_id


class TracingMiddleware(BaseHTTPMiddleware):
    """リクエスト・レスポンスに OpenTelemetry トレース ID を付与するミドルウェア。

    - リクエスト属性 `http.method`, `http.url`, `http.route` をスパンに記録
    - レスポンスヘッダー `X-Trace-Id` にトレース ID を付与
    - エラー時はスパンのステータスを ERROR に設定
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        tracer = trace.get_tracer("servicematrix.http")
        route = request.url.path
        span_name = f"{request.method} {route}"

        with tracer.start_as_current_span(
            span_name,
            kind=trace.SpanKind.SERVER,
        ) as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.route", route)
            client_ip = request.client.host if request.client else "unknown"
            span.set_attribute("http.client_ip", client_ip)

            try:
                response = await call_next(request)
            except Exception as exc:
                span.set_status(trace.StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

            span.set_attribute("http.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(trace.StatusCode.ERROR, f"HTTP {response.status_code}")
            else:
                span.set_status(trace.StatusCode.OK)

            trace_id = get_current_trace_id()
            if trace_id:
                response.headers["X-Trace-Id"] = trace_id

            return response
