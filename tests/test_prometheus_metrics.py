"""Prometheus メトリクス テストスイート"""

from datetime import datetime

# ── MetricsCollector テスト ───────────────────────────────────────────────────


class TestMetricsCollector:
    def _make_collector(self):
        from src.core.metrics import MetricsCollector

        return MetricsCollector()

    def test_initial_values(self):
        """初期値確認"""
        mc = self._make_collector()
        assert mc.incidents_created_total == 0
        assert mc.changes_created_total == 0
        assert mc.sla_breaches_total == 0
        assert mc.ai_triage_calls_total == 0
        assert mc.ws_connections_active == 0
        assert isinstance(mc.start_time, datetime)

    def test_record_request_increments_counter(self):
        """リクエスト記録でカウンター増加"""
        mc = self._make_collector()
        mc.record_request("GET", "/api/v1/incidents", 200, 45.2)
        key = "GET:/api/v1/incidents:200"
        assert mc.http_requests_total[key] == 1
        assert len(mc.http_request_duration_ms[key]) == 1
        assert mc.http_request_duration_ms[key][0] == 45.2

    def test_record_request_5xx_adds_error(self):
        """5xxエラーのリクエストはエラーカウンターに追加"""
        mc = self._make_collector()
        mc.record_request("POST", "/api/v1/changes", 500, 120.0)
        assert mc.http_errors_total["POST:/api/v1/changes"] == 1

    def test_record_request_4xx_no_error(self):
        """4xxはエラーカウンターに含まれない"""
        mc = self._make_collector()
        mc.record_request("GET", "/api/v1/incidents/bad-id", 404, 10.0)
        assert len(mc.http_errors_total) == 0

    def test_record_multiple_requests(self):
        """複数リクエストの累積"""
        mc = self._make_collector()
        for _ in range(5):
            mc.record_request("GET", "/api/v1/health", 200, 5.0)
        key = "GET:/api/v1/health:200"
        assert mc.http_requests_total[key] == 5
        assert len(mc.http_request_duration_ms[key]) == 5

    # ── to_prometheus_text テスト ──────────────────────────────────────────

    def test_to_prometheus_text_contains_uptime(self):
        """Prometheus テキストにuptime含む"""
        mc = self._make_collector()
        text = mc.to_prometheus_text()
        assert "servicematrix_uptime_seconds" in text
        assert "# HELP" in text
        assert "# TYPE" in text

    def test_to_prometheus_text_contains_counters(self):
        """Prometheus テキストにカウンター含む"""
        mc = self._make_collector()
        mc.incidents_created_total = 3
        mc.changes_created_total = 1
        mc.sla_breaches_total = 2
        mc.ws_connections_active = 5
        text = mc.to_prometheus_text()
        assert "servicematrix_incidents_created_total 3" in text
        assert "servicematrix_changes_created_total 1" in text
        assert "servicematrix_sla_breaches_total 2" in text
        assert "servicematrix_ws_connections_active 5" in text

    def test_to_prometheus_text_with_http_requests(self):
        """HTTP リクエストラベル付きメトリクス"""
        mc = self._make_collector()
        mc.record_request("GET", "/api/v1/incidents", 200, 30.0)
        text = mc.to_prometheus_text()
        assert "servicematrix_http_requests_total" in text
        assert 'method="GET"' in text
        assert 'path="/api/v1/incidents"' in text
        assert 'status="200"' in text

    def test_to_prometheus_text_uptime_is_positive(self):
        """uptime は正の数値"""
        mc = self._make_collector()
        text = mc.to_prometheus_text()
        for line in text.splitlines():
            if line.startswith("servicematrix_uptime_seconds "):
                value = float(line.split(" ")[1])
                assert value >= 0.0

    # ── to_json テスト ────────────────────────────────────────────────────

    def test_to_json_structure(self):
        """JSON形式のキー確認"""
        mc = self._make_collector()
        data = mc.to_json()
        assert "uptime_seconds" in data
        assert "incidents_created_total" in data
        assert "changes_created_total" in data
        assert "sla_breaches_total" in data
        assert "ai_triage_calls_total" in data
        assert "ws_connections_active" in data
        assert "http_requests_total" in data
        assert "http_errors_total" in data

    def test_to_json_aggregates_requests(self):
        """http_requests_total は全リクエストの合計"""
        mc = self._make_collector()
        mc.record_request("GET", "/a", 200, 10.0)
        mc.record_request("GET", "/b", 200, 20.0)
        mc.record_request("POST", "/c", 201, 30.0)
        data = mc.to_json()
        assert data["http_requests_total"] == 3

    def test_to_json_aggregates_errors(self):
        """http_errors_total は5xxエラーの合計"""
        mc = self._make_collector()
        mc.record_request("GET", "/a", 500, 10.0)
        mc.record_request("POST", "/b", 503, 20.0)
        data = mc.to_json()
        assert data["http_errors_total"] == 2

    def test_to_json_uptime_positive(self):
        """uptime_seconds は正の値"""
        mc = self._make_collector()
        data = mc.to_json()
        assert data["uptime_seconds"] >= 0.0


# ── グローバル metrics シングルトン テスト ─────────────────────────────────────


class TestGlobalMetrics:
    def test_global_metrics_singleton(self):
        """グローバル metrics インスタンスが存在する"""
        from src.core.metrics import MetricsCollector, metrics

        assert isinstance(metrics, MetricsCollector)

    def test_global_metrics_mutable(self):
        """グローバル metrics に書き込み可能"""
        from src.core.metrics import metrics

        before = metrics.incidents_created_total
        metrics.incidents_created_total += 1
        assert metrics.incidents_created_total == before + 1
        # クリーンアップ
        metrics.incidents_created_total = before


# ── /metrics エンドポイント テスト ────────────────────────────────────────────


class TestMetricsEndpoint:
    def setup_method(self):
        from fastapi.testclient import TestClient

        from src.main import app

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_metrics_endpoint_returns_200(self):
        """/metrics エンドポイントが 200 を返す"""
        resp = self.client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_endpoint_content_type(self):
        """/metrics のコンテンツタイプ確認"""
        resp = self.client.get("/metrics")
        assert resp.status_code == 200
        # text/plain または application/json
        ct = resp.headers.get("content-type", "")
        assert "text" in ct or "json" in ct or "plain" in ct

    def test_metrics_endpoint_contains_uptime(self):
        """/metrics レスポンスに uptime 含む"""
        resp = self.client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "uptime" in body.lower() or "servicematrix" in body


# ── Prometheus テキスト形式検証 ───────────────────────────────────────────────


class TestPrometheusTextFormat:
    def test_format_lines_structure(self):
        """各メトリクスにHELP/TYPE行が存在する"""
        from src.core.metrics import MetricsCollector

        mc = MetricsCollector()
        text = mc.to_prometheus_text()
        lines = text.splitlines()
        help_lines = [ln for ln in lines if ln.startswith("# HELP")]
        type_lines = [ln for ln in lines if ln.startswith("# TYPE")]
        # 少なくとも基本メトリクス分
        assert len(help_lines) >= 5
        assert len(type_lines) >= 5

    def test_counter_type_label(self):
        """カウンターには TYPE counter ラベル"""
        from src.core.metrics import MetricsCollector

        mc = MetricsCollector()
        text = mc.to_prometheus_text()
        assert "# TYPE servicematrix_incidents_created_total counter" in text
        assert "# TYPE servicematrix_changes_created_total counter" in text
        assert "# TYPE servicematrix_sla_breaches_total counter" in text

    def test_gauge_type_label(self):
        """ゲージには TYPE gauge ラベル"""
        from src.core.metrics import MetricsCollector

        mc = MetricsCollector()
        text = mc.to_prometheus_text()
        assert "# TYPE servicematrix_uptime_seconds gauge" in text
        assert "# TYPE servicematrix_ws_connections_active gauge" in text
