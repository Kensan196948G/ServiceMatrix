"""OpenTelemetry 分散トレーシング設定 - Issue #74"""

import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None


def setup_telemetry(
    service_name: str = "servicematrix", service_version: str = "2.0.0"
) -> TracerProvider:
    """OpenTelemetry TracerProvider を初期化する。

    OTEL_EXPORTER_OTLP_ENDPOINT が設定されている場合は OTLP HTTP エクスポーターを使用。
    未設定（テスト・ローカル環境）の場合は ConsoleSpanExporter にフォールバック。
    """
    global _tracer_provider

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info("OpenTelemetry: OTLP エクスポーターを設定 endpoint=%s", otlp_endpoint)
        except Exception as exc:
            logger.warning(
                "OpenTelemetry: OTLP エクスポーター設定失敗、Console にフォールバック: %s", exc
            )
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # ローカル開発・テスト環境: stdout にスパンを出力しない（ノイズ防止）
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        _in_memory_exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(_in_memory_exporter))
        logger.debug("OpenTelemetry: InMemory エクスポーター使用（開発モード）")

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider


def get_tracer(name: str = "servicematrix") -> trace.Tracer:
    """名前付きトレーサーを取得する。"""
    return trace.get_tracer(name)


def get_current_trace_id() -> str | None:
    """現在のリクエストのトレース ID を16進数文字列で返す。トレースがない場合は None。"""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """現在のスパン ID を16進数文字列で返す。"""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        return format(ctx.span_id, "016x")
    return None
