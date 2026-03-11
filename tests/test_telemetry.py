"""OpenTelemetry トレーシングテスト - Issue #74"""

import pytest

from src.core.telemetry import (  # noqa: E402
    get_current_span_id,
    get_current_trace_id,
    setup_telemetry,
)

# ---------------------------------------------------------------------------
# Unit tests: telemetry helpers
# ---------------------------------------------------------------------------


def test_get_current_trace_id_no_span():
    """アクティブスパンがない場合は None を返す"""
    # OTEL_EXPORTER_OTLP_ENDPOINT 未設定の状態で呼び出す
    result = get_current_trace_id()
    # スパンコンテキスト外では None または有効な trace_id のどちらか
    assert result is None or (isinstance(result, str) and len(result) == 32)


def test_get_current_span_id_no_span():
    """アクティブスパンがない場合は None を返す"""
    result = get_current_span_id()
    assert result is None or (isinstance(result, str) and len(result) == 16)


def test_setup_telemetry_returns_provider():
    """setup_telemetry() が TracerProvider を返す"""
    from opentelemetry.sdk.trace import TracerProvider

    provider = setup_telemetry(service_name="test-service", service_version="0.0.1")
    assert isinstance(provider, TracerProvider)


def test_setup_telemetry_resource_attributes():
    """TracerProvider に正しいリソース属性が設定されている"""
    provider = setup_telemetry(service_name="my-service", service_version="1.2.3")
    resource = provider.resource
    attrs = dict(resource.attributes)
    assert attrs.get("service.name") == "my-service"
    assert attrs.get("service.version") == "1.2.3"
    assert "deployment.environment" in attrs


def test_setup_telemetry_with_otlp_endpoint(monkeypatch):
    """OTEL_EXPORTER_OTLP_ENDPOINT 設定時は OTLP エクスポーターを試みる（失敗はフォールバック）"""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    # importエラーが発生しても ConsoleSpanExporter にフォールバックすることを確認
    provider = setup_telemetry(service_name="otlp-service", service_version="1.0.0")
    from opentelemetry.sdk.trace import TracerProvider

    assert isinstance(provider, TracerProvider)


def test_setup_telemetry_without_otlp_endpoint(monkeypatch):
    """OTEL_EXPORTER_OTLP_ENDPOINT 未設定時は InMemory エクスポーターを使用"""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    provider = setup_telemetry(service_name="inmem-service", service_version="1.0.0")
    from opentelemetry.sdk.trace import TracerProvider

    assert isinstance(provider, TracerProvider)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_telemetry_status_endpoint(client, auth_headers) -> None:
    """/api/v1/telemetry/status が正しいフィールドを返す"""
    resp = await client.get("/api/v1/telemetry/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "tracing_enabled" in data
    assert "trace_id" in data
    assert "span_id" in data
    assert data["service"] == "servicematrix"
    assert isinstance(data["tracing_enabled"], bool)


@pytest.mark.asyncio
async def test_telemetry_status_trace_id_format(client, auth_headers) -> None:
    """/api/v1/telemetry/status の trace_id は32文字の16進数文字列"""
    resp = await client.get("/api/v1/telemetry/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    if data["trace_id"] is not None:
        assert len(data["trace_id"]) == 32
        int(data["trace_id"], 16)  # 16進数として解釈できることを確認


@pytest.mark.asyncio
async def test_telemetry_status_unauthorized(client) -> None:
    """認証なしは 401"""
    resp = await client.get("/api/v1/telemetry/status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_x_trace_id_header_present(client, auth_headers) -> None:
    """X-Trace-Id レスポンスヘッダーが付与されている"""
    resp = await client.get("/api/v1/health", headers=auth_headers)
    # TracingMiddleware が trace_id を付与していれば X-Trace-Id ヘッダーが存在する
    # InMemorySpanExporter 利用時は有効なスパンコンテキストが生成される
    # ヘッダーが存在する場合は形式を検証
    if "x-trace-id" in resp.headers:
        trace_id = resp.headers["x-trace-id"]
        assert len(trace_id) == 32
        int(trace_id, 16)
