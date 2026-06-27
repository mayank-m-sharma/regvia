"""OpenTelemetry setup — call configure_telemetry() once at application startup."""

from __future__ import annotations

from loguru import logger


def configure_telemetry(service_name: str = "regvia-backend") -> None:
    """Instrument FastAPI, SQLAlchemy, and httpx and export traces via OTLP HTTP.

    No-ops when OTEL_ENABLED=false so local dev is unaffected.
    Uses the HTTP/protobuf exporter (port 4318) — more reliable than gRPC.
    """
    from app.core.settings import settings

    if not settings.OTEL_ENABLED:
        logger.debug("otel_disabled | skipping OpenTelemetry setup")
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    # OTLP HTTP endpoint: <base>/v1/traces  (Jaeger listens on port 4318)
    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/") + "/v1/traces"
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    logger.info(
        "otel_configured | endpoint={} service={}",
        endpoint,
        service_name,
    )
