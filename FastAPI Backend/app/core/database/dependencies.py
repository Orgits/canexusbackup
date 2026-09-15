from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_db, get_tenant_db
from app.core.tenancy.dependencies import setup_tenant_context
from app.core.tenancy.context import TenantContext


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session WITHOUT tenant context (for auth, superuser, firms table)."""
    async for session in get_async_db():
        yield session


async def get_tenant_db_session(
    tenant_context: TenantContext = Depends(setup_tenant_context),
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session WITH tenant context (SET LOCAL app.current_tenant).
    
    This dependency ensures the tenant context is set before creating the session.
    The setup_tenant_context dependency runs first and sets the ContextVar.
    Then get_tenant_db reads the ContextVar and executes SET LOCAL.
    """
    async for session in get_tenant_db():
        yield session