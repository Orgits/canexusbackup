import time
import uuid

import structlog
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Extract trace context from headers
        traceparent = request.headers.get("traceparent")
        tracestate = request.headers.get("tracestate")

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Extract trace context for propagation
        carrier = {}
        if traceparent:
            carrier["traceparent"] = traceparent
        if tracestate:
            carrier["tracestate"] = tracestate

        # Add trace context to structlog
        span = trace.get_current_span()
        if span and span.get_span_context().trace_id:
            trace_id = format(span.get_span_context().trace_id, "032x")
            span_id = format(span.get_span_context().span_id, "016x")
            structlog.contextvars.bind_contextvars(
                trace_id=trace_id,
                span_id=span_id,
            )

        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Add trace headers to response
            span = trace.get_current_span()
            if span and span.get_span_context().trace_id:
                trace_id = format(span.get_span_context().trace_id, "032x")
                span_id = format(span.get_span_context().span_id, "016x")
                response.headers["X-Request-ID"] = request_id
                response.headers["traceparent"] = f"00-{trace_id}-{span_id}-01"

            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration=duration,
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(
                "Request failed",
                duration=duration,
                error=str(e),
            )
            raise
