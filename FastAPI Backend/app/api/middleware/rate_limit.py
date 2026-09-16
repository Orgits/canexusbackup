"""Rate limiting middleware using slowapi."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"] if not settings.is_development else ["10000/hour"],
    storage_uri=settings.REDIS_URL,
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with path-specific limits."""

    def __init__(self, app, limiter_instance: Limiter = None):
        super().__init__(app)
        self.limiter = limiter_instance or limiter

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health/readiness/metrics
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        # Apply rate limiting based on path
        path = request.url.path

        # Stricter limits for authentication endpoints
        if path.startswith("/api/v1/auth/"):
            if path.endswith("/login"):
                # Login: 5 requests per minute per IP
                limit = "5/minute"
            elif path.endswith("/refresh"):
                # Refresh: 10 requests per minute per IP
                limit = "10/minute"
            elif path.endswith("/logout"):
                # Logout: 20 requests per minute per IP
                limit = "20/minute"
            elif "password" in path or "reset" in path or "unlock" in path:
                # Password operations: 3 requests per minute per IP
                limit = "3/minute"
            else:
                limit = "30/minute"
        # Expensive endpoints
        elif path.startswith("/api/v1/documents/"):
            limit = "30/minute"
        elif path.startswith("/api/v1/compliance/") and "initialize" in path:
            limit = "5/minute"
        elif path.startswith("/api/v1/workflow/") and "transition" in path:
            limit = "20/minute"
        elif path.startswith("/api/v1/workload/") and "snapshot" in path:
            limit = "10/minute"
        elif path.startswith("/api/v1/notices/") and "escalate" in path:
            limit = "10/minute"
        elif path.startswith("/api/v1/assignments/") and "escalate" in path:
            limit = "10/minute"
        elif path.startswith("/api/v1/notifications/") and "send" in path:
            limit = "20/minute"
        # External provider endpoints
        elif path.startswith("/api/v1/") and any(
            ext in path for ext in ["azure", "aws", "gcp", "external"]
        ):
            limit = "20/minute"
        else:
            # Default rate limit
            limit = "100/minute"

        # Apply rate limit
        try:
            await self.limiter.check_request_limit(request, limit)
        except Exception:
            # If rate limit check fails (e.g., Redis down), allow request
            pass

        return await call_next(request)


def get_rate_limiter() -> Limiter:
    """Get the rate limiter instance."""
    return limiter


def init_rate_limiter(app):
    """Initialize rate limiter for FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    return limiter