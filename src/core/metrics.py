"""アプリケーションメトリクス収集"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricsCollector:
    """アプリケーションメトリクス収集器"""

    # HTTPリクエストカウンター
    http_requests_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    http_request_duration_ms: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    http_errors_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # ビジネスメトリクス
    incidents_created_total: int = 0
    changes_created_total: int = 0
    sla_breaches_total: int = 0
    ai_triage_calls_total: int = 0
    ws_connections_active: int = 0

    # 起動時刻
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        key = f"{method}:{path}:{status_code}"
        self.http_requests_total[key] += 1
        self.http_request_duration_ms[key].append(duration_ms)
        if status_code >= 500:
            self.http_errors_total[f"{method}:{path}"] += 1

    def to_prometheus_text(self) -> str:
        """Prometheus text format形式で出力"""
        lines = []
        uptime = (datetime.now(UTC) - self.start_time).total_seconds()
        lines.append("# HELP servicematrix_uptime_seconds Application uptime in seconds")
        lines.append("# TYPE servicematrix_uptime_seconds gauge")
        lines.append(f"servicematrix_uptime_seconds {uptime:.1f}")

        lines.append("# HELP servicematrix_incidents_created_total Total incidents created")
        lines.append("# TYPE servicematrix_incidents_created_total counter")
        lines.append(f"servicematrix_incidents_created_total {self.incidents_created_total}")

        lines.append("# HELP servicematrix_changes_created_total Total changes created")
        lines.append("# TYPE servicematrix_changes_created_total counter")
        lines.append(f"servicematrix_changes_created_total {self.changes_created_total}")

        lines.append("# HELP servicematrix_sla_breaches_total Total SLA breaches")
        lines.append("# TYPE servicematrix_sla_breaches_total counter")
        lines.append(f"servicematrix_sla_breaches_total {self.sla_breaches_total}")

        lines.append("# HELP servicematrix_ws_connections_active Active WebSocket connections")
        lines.append("# TYPE servicematrix_ws_connections_active gauge")
        lines.append(f"servicematrix_ws_connections_active {self.ws_connections_active}")

        lines.append("# HELP servicematrix_http_requests_total HTTP requests total")
        lines.append("# TYPE servicematrix_http_requests_total counter")
        for key, count in self.http_requests_total.items():
            method, path, status = key.rsplit(":", 2)
            label = (
                f'servicematrix_http_requests_total{{method="{method}",'
                f'path="{path}",status="{status}"}}'
            )
            lines.append(f"{label} {count}")

        return "\n".join(lines)

    def to_json(self) -> dict:
        """JSON形式のサマリー"""
        uptime = (datetime.now(UTC) - self.start_time).total_seconds()
        return {
            "uptime_seconds": uptime,
            "incidents_created_total": self.incidents_created_total,
            "changes_created_total": self.changes_created_total,
            "sla_breaches_total": self.sla_breaches_total,
            "ai_triage_calls_total": self.ai_triage_calls_total,
            "ws_connections_active": self.ws_connections_active,
            "http_requests_total": sum(self.http_requests_total.values()),
            "http_errors_total": sum(self.http_errors_total.values()),
        }


metrics = MetricsCollector()
