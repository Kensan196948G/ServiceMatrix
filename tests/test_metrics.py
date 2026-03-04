"""MetricsCollector・メトリクスエンドポイントのテスト"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from src.core.metrics import MetricsCollector
from src.main import app


# ─── MetricsCollector 単体テスト ────────────────────────────────────────────

def test_metrics_collector_initial_values():
    """初期値がすべてゼロであること"""
    m = MetricsCollector()
    assert m.incidents_created_total == 0
    assert m.changes_created_total == 0
    assert m.sla_breaches_total == 0
    assert m.ai_triage_calls_total == 0
    assert m.ws_connections_active == 0


def test_record_request_increments_counter():
    """record_requestがカウンターを正しくインクリメントすること"""
    m = MetricsCollector()
    m.record_request("GET", "/api/v1/incidents", 200, 42.0)
    m.record_request("GET", "/api/v1/incidents", 200, 10.0)
    assert m.http_requests_total["GET:/api/v1/incidents:200"] == 2


def test_record_request_tracks_duration():
    """record_requestがレスポンス時間を記録すること"""
    m = MetricsCollector()
    m.record_request("POST", "/api/v1/changes", 201, 99.5)
    assert 99.5 in m.http_request_duration_ms["POST:/api/v1/changes:201"]


def test_record_request_increments_error_counter_on_5xx():
    """5xxエラーでhttp_errors_totalがインクリメントされること"""
    m = MetricsCollector()
    m.record_request("GET", "/api/v1/broken", 500, 5.0)
    assert m.http_errors_total["GET:/api/v1/broken"] == 1


def test_record_request_no_error_on_4xx():
    """4xxエラーではhttp_errors_totalがインクリメントされないこと"""
    m = MetricsCollector()
    m.record_request("GET", "/api/v1/missing", 404, 1.0)
    assert m.http_errors_total["GET:/api/v1/missing"] == 0


def test_to_json_contains_required_keys():
    """to_jsonが必須キーをすべて含むこと"""
    m = MetricsCollector()
    result = m.to_json()
    required = {
        "uptime_seconds", "incidents_created_total", "changes_created_total",
        "sla_breaches_total", "ai_triage_calls_total", "ws_connections_active",
        "http_requests_total", "http_errors_total",
    }
    assert required.issubset(result.keys())


def test_to_json_uptime_is_positive():
    """uptime_secondsが正の値であること"""
    m = MetricsCollector()
    assert m.to_json()["uptime_seconds"] >= 0.0


def test_to_prometheus_text_contains_metric_names():
    """to_prometheus_textが必要なメトリクス名を含むこと"""
    m = MetricsCollector()
    text = m.to_prometheus_text()
    assert "servicematrix_uptime_seconds" in text
    assert "servicematrix_incidents_created_total" in text
    assert "servicematrix_changes_created_total" in text
    assert "servicematrix_sla_breaches_total" in text
    assert "servicematrix_ws_connections_active" in text


def test_to_prometheus_text_http_labels():
    """HTTPリクエストメトリクスがラベル付きで出力されること"""
    m = MetricsCollector()
    m.record_request("DELETE", "/api/v1/incidents/1", 204, 3.0)
    text = m.to_prometheus_text()
    assert 'method="DELETE"' in text
    assert 'status="204"' in text


def test_business_metric_increment():
    """ビジネスメトリクスを手動インクリメントできること"""
    m = MetricsCollector()
    m.incidents_created_total += 3
    m.changes_created_total += 1
    m.sla_breaches_total += 2
    j = m.to_json()
    assert j["incidents_created_total"] == 3
    assert j["changes_created_total"] == 1
    assert j["sla_breaches_total"] == 2


# ─── APIエンドポイントテスト ────────────────────────────────────────────────

@pytest_asyncio.fixture
async def anon_client():
    """DB不要な匿名クライアント"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_metrics_json_endpoint(anon_client):
    """/api/v1/metricsがJSONを返すこと"""
    response = await anon_client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "http_requests_total" in data


@pytest.mark.asyncio
async def test_metrics_prometheus_endpoint(anon_client):
    """/api/v1/metrics/prometheusがPrometheusテキスト形式を返すこと"""
    response = await anon_client.get("/api/v1/metrics/prometheus")
    assert response.status_code == 200
    assert "servicematrix_uptime_seconds" in response.text
    assert response.headers["content-type"].startswith("text/plain")
