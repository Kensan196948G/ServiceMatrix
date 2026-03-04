"""Prometheus メトリクス テストスイート (Step39)"""

import pytest
from prometheus_client import REGISTRY


class TestMetricsEndpoint:
    """GET /metrics エンドポイントのテスト"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_200(self, client):
        response = await client.get("/metrics")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_endpoint_content_type(self, client):
        response = await client.get("/metrics")
        assert "text/plain" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_metrics_contains_prometheus_format(self, client):
        response = await client.get("/metrics")
        body = response.text
        # Prometheus形式の出力には # HELP と # TYPE が含まれる
        assert "# HELP" in body
        assert "# TYPE" in body

    @pytest.mark.asyncio
    async def test_metrics_endpoint_no_auth_required(self, client):
        """認証なしでも /metrics にアクセスできること"""
        response = await client.get("/metrics")
        assert response.status_code == 200
        # 401/403 ではないことを確認
        assert response.status_code != 401
        assert response.status_code != 403


class TestSLABreachCounter:
    """sla_breach_total カウンターのテスト"""

    def test_sla_breach_counter_increment(self):
        from src.core.metrics import sla_breach_total

        before = (
            REGISTRY.get_sample_value(
                "sla_breach_total",
                {"priority": "P1", "entity_type": "incident"},
            )
            or 0.0
        )

        sla_breach_total.labels(priority="P1", entity_type="incident").inc()

        after = REGISTRY.get_sample_value(
            "sla_breach_total",
            {"priority": "P1", "entity_type": "incident"},
        )
        assert after == before + 1.0

    def test_metrics_labels_sla_breach(self):
        """異なるラベル値でカウンターが独立して動作すること"""
        from src.core.metrics import sla_breach_total

        before_p2 = (
            REGISTRY.get_sample_value(
                "sla_breach_total",
                {"priority": "P2", "entity_type": "change"},
            )
            or 0.0
        )

        sla_breach_total.labels(priority="P2", entity_type="change").inc(3)

        after_p2 = REGISTRY.get_sample_value(
            "sla_breach_total",
            {"priority": "P2", "entity_type": "change"},
        )
        assert after_p2 == before_p2 + 3.0


class TestIncidentResolutionHistogram:
    """incident_resolution_duration_seconds ヒストグラムのテスト"""

    def test_incident_resolution_histogram_observe(self):
        from src.core.metrics import incident_resolution_duration_seconds

        before_count = (
            REGISTRY.get_sample_value(
                "incident_resolution_duration_seconds_count",
                {"priority": "P1"},
            )
            or 0.0
        )

        incident_resolution_duration_seconds.labels(priority="P1").observe(1800)

        after_count = REGISTRY.get_sample_value(
            "incident_resolution_duration_seconds_count",
            {"priority": "P1"},
        )
        assert after_count == before_count + 1.0


class TestActiveIncidentsGauge:
    """active_incidents_gauge ゲージのテスト"""

    def test_active_incidents_gauge_set(self):
        from src.core.metrics import active_incidents_gauge

        active_incidents_gauge.labels(priority="P1").set(5)

        value = REGISTRY.get_sample_value(
            "active_incidents_total",
            {"priority": "P1"},
        )
        assert value == 5.0

        active_incidents_gauge.labels(priority="P1").set(3)
        value = REGISTRY.get_sample_value(
            "active_incidents_total",
            {"priority": "P1"},
        )
        assert value == 3.0


class TestAPIRequestHistogram:
    """api_request_duration_seconds ヒストグラムのテスト"""

    def test_api_request_histogram_observe(self):
        from src.core.metrics import api_request_duration_seconds

        before_count = (
            REGISTRY.get_sample_value(
                "api_request_duration_seconds_count",
                {"method": "GET", "endpoint": "/api/v1/health", "status_code": "200"},
            )
            or 0.0
        )

        api_request_duration_seconds.labels(
            method="GET",
            endpoint="/api/v1/health",
            status_code="200",
        ).observe(0.05)

        after_count = REGISTRY.get_sample_value(
            "api_request_duration_seconds_count",
            {"method": "GET", "endpoint": "/api/v1/health", "status_code": "200"},
        )
        assert after_count == before_count + 1.0


class TestAuditLogCounter:
    """audit_log_total カウンターのテスト"""

    def test_audit_log_counter_increment(self):
        from src.core.metrics import audit_log_total

        before = (
            REGISTRY.get_sample_value(
                "audit_log_total",
                {"action": "create_incident"},
            )
            or 0.0
        )

        audit_log_total.labels(action="create_incident").inc()

        after = REGISTRY.get_sample_value(
            "audit_log_total",
            {"action": "create_incident"},
        )
        assert after == before + 1.0
