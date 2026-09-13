from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.core.config import get_settings

settings = get_settings()

_request_count: Optional[Counter] = None
_request_duration: Optional[Histogram] = None
_active_requests: Optional[Gauge] = None


def setup_metrics() -> None:
    global _request_count, _request_duration, _active_requests
    _request_count = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    _request_duration = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
    )
    _active_requests = Gauge(
        "http_requests_active",
        "Active HTTP requests",
        ["method", "endpoint"],
    )


def get_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def record_request(method: str, endpoint: str, status: int, duration: float) -> None:
    if _request_count and _request_duration and _active_requests:
        _request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        _request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        _active_requests.labels(method=method, endpoint=endpoint).dec()


def increment_active_requests(method: str, endpoint: str) -> None:
    if _active_requests:
        _active_requests.labels(method=method, endpoint=endpoint).inc()