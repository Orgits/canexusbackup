from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.logging import configure_logging, get_logger
from app.core.exceptions import register_exception_handlers
from app.core.observability import setup_metrics, get_metrics
from app.api.middleware import TenantMiddleware, LoggingMiddleware, MetricsMiddleware
from app.api.routers import api_router

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    setup_metrics()
    logger.info("Application starting up", environment=settings.ENVIRONMENT)
    yield
    logger.info("Application shutting down")
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
        return {"status": "ready", "service": settings.APP_NAME}

    if settings.ENABLE_METRICS:
        @app.get("/metrics", tags=["Metrics"])
        async def metrics():
            return get_metrics()

    return app


app = create_app()