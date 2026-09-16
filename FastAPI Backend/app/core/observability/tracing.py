"""OpenTelemetry tracing configuration and utilities."""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.propagate import get_global_textmap, set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_tracer_provider = None


def setup_tracing():
    """Initialize OpenTelemetry tracing."""
    global _tracer_provider

    if _tracer_provider is not None:
        return _tracer_provider

    resource = Resource.create(
        {
            "service.name": settings.APP_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
            "service.instance.id": os.getenv("HOSTNAME", "local"),
        }
    )

    _tracer_provider = TracerProvider(resource=resource)

    # Add console exporter for development
    if settings.is_development:
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    # Add OTLP exporter if endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(_tracer_provider)

    # Set up propagators for distributed tracing (W3C TraceContext)
    set_global_textmap(
        CompositePropagator(
            [
                TraceContextTextMapPropagator(),
            ]
        )
    )

    logger.info(
        "OpenTelemetry tracing initialized",
        service_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        otlp_endpoint=otlp_endpoint,
    )

    return _tracer_provider


def setup_metrics():
    """Initialize OpenTelemetry metrics with Prometheus exporter."""
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider

    metric_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    from opentelemetry.metrics import set_meter_provider
    set_meter_provider(meter_provider)

    logger.info("OpenTelemetry metrics initialized with Prometheus exporter")
    return meter_provider


def instrument_app(app):
    """Instrument FastAPI app with OpenTelemetry."""
    # FastAPI instrumentation
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
        excluded_urls="/health,/ready,/metrics,/docs,/redoc,/openapi.json",
    )

    # SQLAlchemy instrumentation
    SQLAlchemyInstrumentor().instrument(
        engine=None,  # Will be set up when engine is available
        tracer_provider=trace.get_tracer_provider(),
    )

    # HTTPX instrumentation
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HTTPXClientInstrumentor().instrument()

    # Redis instrumentation
    RedisInstrumentor().instrument()

    logger.info("OpenTelemetry instrumentation applied")


def get_tracer(name):
    """Get a tracer instance."""
    return trace.get_tracer(name)


def get_current_span():
    """Get the current active span."""
    return trace.get_current_span()


def get_trace_id():
    """Get the current trace ID as hex string."""
    span = get_current_span()
    if span and span.get_span_context():
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_span_id():
    """Get the current span ID as hex string."""
    span = get_current_span()
    if span and span.get_span_context():
        return format(span.get_span_context().span_id, "016x")
    return None


@contextmanager
def trace_operation(
    name,
    attributes=None,
    kind=trace.SpanKind.INTERNAL,
):
    """Context manager for tracing an operation."""
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def add_span_attributes(attributes):
    """Add attributes to the current span."""
    span = get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exception):
    """Record an exception in the current span."""
    span = get_current_span()
    if span:
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))


def inject_trace_context(carrier):
    """Inject trace context into a carrier for propagation."""
    from opentelemetry.propagate import inject
    inject(carrier)


def extract_trace_context(carrier):
    """Extract trace context from a carrier."""
    from opentelemetry.propagate import extract
    return extract(carrier)


@contextmanager
def trace_db_operation(
    operation,
    table,
    query_type="SELECT",
):
    """Context manager for tracing database operations."""
    with trace_operation(
        f"db.{query_type.lower()}.{table}",
        attributes={
            "db.operation": operation,
            "db.table": table,
            "db.query_type": query_type,
        },
        kind=trace.SpanKind.CLIENT,
    ) as span:
        yield span


@contextmanager
def trace_redis_operation(
    operation,
    key=None,
):
    """Context manager for tracing Redis operations."""
    attributes = {"redis.operation": operation}
    if key:
        attributes["redis.key"] = key

    with trace_operation(
        f"redis.{operation}",
        attributes=attributes,
        kind=trace.SpanKind.CLIENT,
    ) as span:
        yield span


@contextmanager
def trace_http_request(
    method,
    url,
    service,
):
    """Context manager for tracing outgoing HTTP requests."""
    with trace_operation(
        f"http.{method.lower()}",
        attributes={
            "http.method": method,
            "http.url": url,
            "http.service": service,
        },
        kind=trace.SpanKind.CLIENT,
    ) as span:
        yield span


def setup_tracing_for_worker(worker_name):
    """Set up tracing for a Celery worker."""
    global _tracer_provider

    resource = Resource.create(
        {
            "service.name": f"{settings.APP_NAME}-worker",
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
            "worker.name": worker_name,
        }
    )

    _tracer_provider = TracerProvider(resource=resource)

    # Add console exporter for development
    if settings.is_development:
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    # Add OTLP exporter if endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(_tracer_provider)

    # Instrument Redis for workers
    RedisInstrumentor().instrument()

    logger.info("OpenTelemetry tracing initialized for worker", worker_name=worker_name)
    return _tracer_provider