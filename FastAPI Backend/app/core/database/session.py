from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.is_development,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def _set_tenant_context_on_session(session: AsyncSession) -> None:
    """Set the tenant context on the database session using SET LOCAL.
    
    This is transaction-scoped and automatically reset on commit/rollback.
    """
    # Lazy import to avoid circular dependency
    from app.core.tenancy.context import get_tenant_context
    
    context = get_tenant_context()
    if context and context.tenant_id:
        # SET LOCAL doesn't support parameterized queries, use string interpolation
        await session.execute(
            text(f"SET LOCAL app.current_tenant = '{context.tenant_id}'"),
        )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency WITHOUT automatic tenant context.
    
    Use this for operations that don't require tenant isolation (e.g., auth, superuser).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_tenant_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency WITH automatic tenant context (SET LOCAL).
    
    This MUST be used for all tenant-scoped operations. It sets
    app.current_tenant at transaction start, ensuring RLS policies work correctly.
    The setting is transaction-local and cannot leak through connection pooling.
    """
    async with AsyncSessionLocal() as session:
        try:
            await _set_tenant_context_on_session(session)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Legacy alias for get_async_db()."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_tenant_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager version with tenant context."""
    async with AsyncSessionLocal() as session:
        try:
            await _set_tenant_context_on_session(session)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()