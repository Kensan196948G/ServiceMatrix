"""Prometheusメトリクス定義"""

from prometheus_client import Counter, Gauge, Histogram

# SLA違反カウンター
sla_breach_total = Counter(
    "sla_breach_total",
    "Total number of SLA breaches",
    ["priority", "entity_type"],
)

# インシデント解決時間ヒストグラム（秒単位）
incident_resolution_duration_seconds = Histogram(
    "incident_resolution_duration_seconds",
    "Incident resolution duration in seconds",
    ["priority"],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400, float("inf")],
)

# アクティブインシデント数ゲージ
active_incidents_gauge = Gauge(
    "active_incidents_total",
    "Number of currently active (non-resolved) incidents",
    ["priority"],
)

# APIリクエスト時間ヒストグラム
api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, float("inf")],
)

# 監査ログ記録カウンター
audit_log_total = Counter(
    "audit_log_total",
    "Total number of audit log entries",
    ["action"],
)
