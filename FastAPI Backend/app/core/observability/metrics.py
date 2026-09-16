
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

from app.core.config import get_settings

settings = get_settings()

# HTTP metrics
_request_count: Counter | None = None
_request_duration: Histogram | None = None
_active_requests: Gauge | None = None

# Database metrics
_db_pool_size: Gauge | None = None
_db_pool_checked_out: Gauge | None = None
_db_pool_overflow: Gauge | None = None
_db_query_duration: Histogram | None = None
_db_query_errors: Counter | None = None

# Celery metrics
_celery_tasks_total: Counter | None = None
_celery_task_duration: Histogram | None = None
_celery_tasks_active: Gauge | None = None
_celery_queue_depth: Gauge | None = None
_celery_worker_failures: Counter | None = None

# External provider metrics
_ext_provider_requests: Counter | None = None
_ext_provider_duration: Histogram | None = None
_ext_provider_errors: Counter | None = None


def setup_metrics() -> None:
    global _request_count, _request_duration, _active_requests
    global _db_pool_size, _db_pool_checked_out, _db_pool_overflow
    global _db_query_duration, _db_query_errors
    global _celery_tasks_total, _celery_task_duration, _celery_tasks_active, _celery_queue_depth, _celery_worker_failures
    global _ext_provider_requests, _ext_provider_duration, _ext_provider_errors

    # HTTP metrics
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

    # Database metrics
    _db_pool_size = Gauge(
        "db_pool_size",
        "Database connection pool size",
    )
    _db_pool_checked_out = Gauge(
        "db_pool_checked_out",
        "Database connections checked out",
    )
    _db_pool_overflow = Gauge(
        "db_pool_overflow",
        "Database pool overflow connections",
    )
    _db_query_duration = Histogram(
        "db_query_duration_seconds",
        "Database query duration in seconds",
        ["operation", "table"],
    )
    _db_query_errors = Counter(
        "db_query_errors_total",
        "Total database query errors",
        ["operation", "table", "error_type"],
    )

    # Celery metrics
    _celery_tasks_total = Counter(
        "celery_tasks_total",
        "Total Celery tasks",
        ["task_name", "status"],
    )
    _celery_task_duration = Histogram(
        "celery_task_duration_seconds",
        "Celery task duration in seconds",
        ["task_name"],
    )
    _celery_tasks_active = Gauge(
        "celery_tasks_active",
        "Active Celery tasks",
        ["task_name"],
    )
    _celery_queue_depth = Gauge(
        "celery_queue_depth",
        "Celery queue depth",
        ["queue_name"],
    )
    _celery_worker_failures = Counter(
        "celery_worker_failures_total",
        "Total Celery worker failures",
        ["worker_name", "task_name"],
    )

    # External provider metrics
    _ext_provider_requests = Counter(
        "external_provider_requests_total",
        "Total external provider requests",
        ["provider", "operation", "status"],
    )
    _ext_provider_duration = Histogram(
        "external_provider_duration_seconds",
        "External provider request duration in seconds",
        ["provider", "operation"],
    )
    _ext_provider_errors = Counter(
        "external_provider_errors_total",
        "Total external provider errors",
        ["provider", "operation", "error_type"],
    )


def get_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# HTTP metrics
def record_request(method: str, endpoint: str, status: int, duration: float) -> None:
    if _request_count and _request_duration and _active_requests:
        _request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        _request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        _active_requests.labels(method=method, endpoint=endpoint).dec()


def increment_active_requests(method: str, endpoint: str) -> None:
    if _active_requests:
        _active_requests.labels(method=method, endpoint=endpoint).inc()


# Database metrics
def update_db_pool_metrics(pool_size: int, checked_out: int, overflow: int) -> None:
    if _db_pool_size:
        _db_pool_size.set(pool_size)
    if _db_pool_checked_out:
        _db_pool_checked_out.set(checked_out)
    if _db_pool_overflow:
        _db_pool_overflow.set(overflow)


def record_db_query(operation: str, table: str, duration: float) -> None:
    if _db_query_duration:
        _db_query_duration.labels(operation=operation, table=table).observe(duration)


def record_db_query_error(operation: str, table: str, error_type: str) -> None:
    if _db_query_errors:
        _db_query_errors.labels(operation=operation, table=table, error_type=error_type).inc()


# Celery metrics
def record_celery_task(task_name: str, status: str, duration: float) -> None:
    if _celery_tasks_total:
        _celery_tasks_total.labels(task_name=task_name, status=status).inc()
    if _celery_task_duration:
        _celery_task_duration.labels(task_name=task_name).observe(duration)


def increment_active_celery_task(task_name: str) -> None:
    if _celery_tasks_active:
        _celery_tasks_active.labels(task_name=task_name).inc()


def decrement_active_celery_task(task_name: str) -> None:
    if _celery_tasks_active:
        _celery_tasks_active.labels(task_name=task_name).dec()


def update_celery_queue_depth(queue_name: str, depth: int) -> None:
    if _celery_queue_depth:
        _celery_queue_depth.labels(queue_name=queue_name).set(depth)


def record_celery_worker_failure(worker_name: str, task_name: str) -> None:
    if _celery_worker_failures:
        _celery_worker_failures.labels(worker_name=worker_name, task_name=task_name).inc()


# External provider metrics
def record_ext_provider_request(provider: str, operation: str, status: str) -> None:
    if _ext_provider_requests:
        _ext_provider_requests.labels(provider=provider, operation=operation, status=status).inc()


def record_ext_provider_duration(provider: str, operation: str, duration: float) -> None:
    if _ext_provider_duration:
        _ext_provider_duration.labels(provider=provider, operation=operation).observe(duration)


def record_ext_provider_error(provider: str, operation: str, error_type: str) -> None:
    if _ext_provider_errors:
        _ext_provider_errors.labels(provider=provider, operation=operation, error_type=error_type).inc()
