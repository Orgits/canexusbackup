from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Import all models FIRST to ensure they are registered with SQLAlchemy
import app.models
from app.api.middleware import LoggingMiddleware, MetricsMiddleware, TenantMiddleware
from app.api.routers import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.observability import get_metrics, setup_metrics
from app.core.redis.client import close_redis, get_redis, init_redis

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    setup_metrics()
    await init_redis()
    logger.info("Application starting up", environment=settings.ENVIRONMENT)
    yield
    logger.info("Application shutting down")
    await close_redis()
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

    app.add_middleware(LoggingMiddleware)
    if settings.ENABLE_METRICS:
        app.add_middleware(MetricsMiddleware)
    app.add_middleware(TenantMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": settings.APP_NAME}

    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            return {"status": "not ready", "service": settings.APP_NAME, "database": "disconnected"}

        try:
            redis_client = await get_redis()
            await redis_client.ping()
        except Exception:
            return {"status": "not ready", "service": settings.APP_NAME, "redis": "disconnected"}

        return {"status": "ready", "service": settings.APP_NAME}

    if settings.ENABLE_METRICS:
        @app.get("/metrics", tags=["Metrics"])
        async def metrics():
            return get_metrics()

    return app


app = create_app()
