import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import AsyncSessionLocal
from app.core.tenancy.context import TenantContext, clear_tenant_context, set_tenant_context

logger = logging.getLogger(__name__)


class TenantAwareWorker(ABC):
    """Base class for workers that need tenant context."""

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self._session: AsyncSession | None = None

    @asynccontextmanager
    async def session(self):
        """Get a database session with tenant context set."""
        context = TenantContext(tenant_id=self.tenant_id)
        set_tenant_context(context)
        async with AsyncSessionLocal() as session:
            self._session = session
            try:
                await session.execute(text(f"SET LOCAL app.current_tenant = '{self.tenant_id}'"))
                yield session
            finally:
                self._session = None
                clear_tenant_context()

    @abstractmethod
    async def execute(self) -> dict:
        """Execute the worker task."""


class BaseWorker(ABC):
    """Base class for workers that don't need tenant context."""

    def __init__(self):
        self._session: AsyncSession | None = None

    @asynccontextmanager
    async def session(self):
        async with AsyncSessionLocal() as session:
            self._session = session
            try:
                yield session
            finally:
                self._session = None

    @abstractmethod
    async def execute(self) -> dict:
        """Execute the worker task."""


async def run_worker_with_retry(worker_class, *args, max_retries: int = 3, **kwargs):
    """Run a worker with retry logic."""
    last_error = None
    for attempt in range(max_retries):
        try:
            worker = worker_class(*args, **kwargs)
            result = await worker.execute()
            return result
        except Exception as e:
            last_error = e
            logger.warning(f"Worker {worker_class.__name__} attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    logger.error(f"Worker {worker_class.__name__} failed after {max_retries} attempts: {last_error}")
    raise last_error
