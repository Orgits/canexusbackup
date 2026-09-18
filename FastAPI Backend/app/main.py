from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Import all models FIRST to ensure they are registered with SQLAlchemy
import app.models
from app.api.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    TenantMiddleware,
    init_rate_limiter,
)
from app.api.routers import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.observability import get_metrics, setup_metrics, setup_tracing, instrument_app
from app.core.redis.client import close_redis, get_redis, init_redis
from app.modules.mongodb.manager import close_mongodb, get_mongodb
from app.modules.opensearch.manager import close_opensearch, get_opensearch

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    setup_metrics()
    setup_tracing()
    await init_redis()
    
    # Initialize MongoDB
    try:
        await get_mongodb()
        logger.info("MongoDB connected")
    except Exception as e:
        logger.warning("MongoDB connection failed", error=str(e))
    
    # Initialize OpenSearch
    try:
        await get_opensearch()
        logger.info("OpenSearch connected")
    except Exception as e:
        logger.warning("OpenSearch connection failed", error=str(e))
    
    logger.info("Application starting up", environment=settings.ENVIRONMENT)
    yield
    logger.info("Application shutting down")
    await close_redis()
    await close_mongodb()
    await close_opensearch()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="CA Nexus API - Unified practice management for CA firms",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Rate limiting middleware (added first to catch all requests)
    app.add_middleware(RateLimitMiddleware)

    app.add_middleware(LoggingMiddleware)
    if settings.ENABLE_METRICS:
        app.add_middleware(MetricsMiddleware)
    app.add_middleware(TenantMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Initialize rate limiter
    init_rate_limiter(app)

    # Instrument with OpenTelemetry after all routes are added
    if settings.ENABLE_TRACING:
        instrument_app(app)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": settings.APP_NAME}

    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        checks = {"service": settings.APP_NAME, "checks": {}}

        # Database check
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["checks"]["database"] = "connected"
        except Exception as e:
            checks["checks"]["database"] = f"disconnected: {str(e)}"

        # Redis check
        try:
            redis_client = await get_redis()
            await redis_client.ping()
            checks["checks"]["redis"] = "connected"
        except Exception as e:
            checks["checks"]["redis"] = f"disconnected: {str(e)}"

        # Determine overall status
        all_healthy = all(v == "connected" for v in checks["checks"].values())
        checks["status"] = "ready" if all_healthy else "not ready"

        return checks

    if settings.ENABLE_METRICS:
        @app.get("/metrics", tags=["Metrics"])
        async def metrics():
            return get_metrics()

    return app


app = create_app()
