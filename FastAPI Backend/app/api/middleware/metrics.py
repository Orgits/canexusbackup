import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.observability.metrics import increment_active_requests, record_request


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        endpoint = request.url.path
        method = request.method

        increment_active_requests(method, endpoint)
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            record_request(method, endpoint, response.status_code, duration)
            return response
        except Exception:
            duration = time.time() - start_time
            record_request(method, endpoint, 500, duration)
            raise
