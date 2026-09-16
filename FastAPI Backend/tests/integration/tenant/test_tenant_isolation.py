# Tenant Isolation and RLS Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.matters.models import Matter
from app.modules.tasks.models import Task
from app.modules.documents.models import Document
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context
from app.core.database.session import get_tenant_db
from app.core.security import hash_password


class TestTenantIsolation:
    """Tests for tenant isolation at the application and database level."""

    @pytest_asyncio.fixture
    async def tenant_a(self, db_session: AsyncSession) -> Firm:
        firm = Firm(
            id=uuid4(),
            name="Tenant A",
            display_name="Tenant A",
            is_active=True,
            settings={},
            country="India",
        )
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def tenant_b(self, db_session: AsyncSession) -> Firm:
        firm = Firm(
            id=uuid4(),
            name="Tenant B",
            display_name="Tenant B",
            is_active=True,
            settings={},
            country="India",
        )
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def user_a(self, db_session: AsyncSession, tenant_a: Firm) -> User:
        user = User(
            email="usera@tenant-a.com",
            hashed_password=hash_password("Pass123!"),
            full_name="User A",
            tenant_id=tenant_a.id,
            roles=["associate"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def user_b(self, db_session: AsyncSession, tenant_b: Firm) -> User:
        user = User(
            email="userb@tenant-b.com",
            hashed_password=hash_password("Pass123!"),
            full_name="User B",
            tenant_id=tenant_b.id,
            roles=["associate"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.mark.integration
    async def test_tenant_a_cannot_see_tenant_b_clients(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm, user_a: User
    ):
        """Test that Tenant A cannot see Tenant B's clients."""
        # Create client for Tenant A
        client_a = Client(
            name="Client A",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=tenant_a.id,
        )
        db_session.add(client_a)

        # Create client for Tenant B
        client_b = Client(
            name="Client B",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=tenant_b.id,
        )
        db_session.add(client_b)
        await db_session.flush()

        # Set tenant context to Tenant A
        context = TenantContext(tenant_id=tenant_a.id, firm=tenant_a, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_a.id}'"))

        # Query clients - should only see Tenant A's client
        result = await db_session.execute(select(Client))
        clients = result.scalars().all()

        assert len(clients) == 1
        assert clients[0].id == client_a.id
        clear_tenant_context()

    @pytest.mark.integration
    async def test_tenant_b_cannot_see_tenant_a_clients(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm, user_b: User
    ):
        """Test that Tenant B cannot see Tenant A's clients."""
        client_a = Client(
            name="Client A",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=tenant_a.id,
        )
        db_session.add(client_a)

        client_b = Client(
            name="Client B",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=tenant_b.id,
        )
        db_session.add(client_b)
        await db_session.flush()

        context = TenantContext(tenant_id=tenant_b.id, firm=tenant_b, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_b.id}'"))

        result = await db_session.execute(select(Client))
        clients = result.scalars().all()

        assert len(clients) == 1
        assert clients[0].id == client_b.id
        clear_tenant_context()

    @pytest.mark.integration
    async def test_tenant_a_cannot_update_tenant_b_client(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm, user_a: User
    ):
        """Test that Tenant A cannot update Tenant B's client."""
        client_b = Client(
            name="Client B",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=tenant_b.id,
        )
        db_session.add(client_b)
        await db_session.flush()

        context = TenantContext(tenant_id=tenant_a.id, firm=tenant_a, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_a.id}'"))

        # Try to update Tenant B's client
        from sqlalchemy import update
        result = await db_session.execute(
            update(Client)
            .where(Client.id == client_b.id)
            .values(name="Hacked Name")
        )
        assert result.rowcount == 0  # No rows affected

        # Verify client wasn't updated
        await db_session.refresh(client_b)
        assert client_b.name == "Client B"
        clear_tenant_context()

    @pytest.mark.integration
    async def test_tenant_a_cannot_delete_tenant_b_client(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm, user_a: User
    ):
        """Test that Tenant A cannot delete Tenant B's client."""
        client_b = Client(
            name="Client B",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=tenant_b.id,
        )
        db_session.add(client_b)
        await db_session.flush()

        context = TenantContext(tenant_id=tenant_a.id, firm=tenant_a, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_a.id}'"))

        from sqlalchemy import delete
        result = await db_session.execute(
            delete(Client).where(Client.id == client_b.id)
        )
        assert result.rowcount == 0

        # Verify client still exists
        result = await db_session.execute(select(Client).where(Client.id == client_b.id))
        assert result.scalar_one_or_none() is not None
        clear_tenant_context()

    @pytest.mark.integration
    async def test_no_tenant_context_sees_no_data(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm
    ):
        """Test that without tenant context, no tenant data is visible (fail closed)."""
        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=tenant_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=tenant_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        clear_tenant_context()

        result = await db_session.execute(select(Client))
        clients = result.scalars().all()

        assert len(clients) == 0  # Fail closed - no data visible

    @pytest.mark.integration
    async def test_explicit_tenant_filter_with_rls(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm, user_a: User
    ):
        """Test that explicit tenant filter works with RLS (defense in depth)."""
        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=tenant_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=tenant_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        context = TenantContext(tenant_id=tenant_a.id, firm=tenant_a, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_a.id}'"))

        # Explicit filter for Tenant B's data
        from sqlalchemy import select
        result = await db_session.execute(
            select(Client).where(Client.tenant_id == tenant_b.id)
        )
        clients = result.scalars().all()

        # Even with explicit filter, RLS should prevent access
        assert len(clients) == 0
        clear_tenant_context()


class TestRepositoryTenantFiltering:
    """Tests for repository-level tenant filtering."""

    @pytest_asyncio.fixture
    async def tenant_a(self, db_session: AsyncSession) -> Firm:
        firm = Firm(
            name="Tenant A",
            display_name="Tenant A",
            is_active=True,
            settings={},
            country="India",
        )
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def tenant_b(self, db_session: AsyncSession) -> Firm:
        firm = Firm(
            name="Tenant B",
            display_name="Tenant B",
            is_active=True,
            settings={},
            country="India",
        )
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest.mark.integration
    async def test_client_repository_tenant_filter(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm
    ):
        """Test ClientRepository filters by tenant."""
        from app.modules.clients.repository import ClientRepository

        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=tenant_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=tenant_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        repo = ClientRepository(db_session)

        # Query with Tenant A context
        clients_a = await repo.get_all(tenant_a.id, page=1, page_size=10)
        assert len(clients_a) == 1
        assert clients_a[0].id == client_a.id

        # Query with Tenant B context
        clients_b = await repo.get_all(tenant_b.id, page=1, page_size=10)
        assert len(clients_b) == 1
        assert clients_b[0].id == client_b.id

    @pytest.mark.integration
    async def test_matter_repository_tenant_filter(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm
    ):
        """Test MatterRepository filters by tenant."""
        from app.modules.matters.repository import MatterRepository
        from app.modules.clients.models import Client

        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=tenant_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=tenant_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        matter_a = Matter(name="Matter A", matter_type="TAX", status="IN_PROGRESS", client_id=client_a.id, tenant_id=tenant_a.id)
        matter_b = Matter(name="Matter B", matter_type="TAX", status="IN_PROGRESS", client_id=client_b.id, tenant_id=tenant_b.id)
        db_session.add_all([matter_a, matter_b])
        await db_session.flush()

        repo = MatterRepository(db_session)

        matters_a = await repo.get_all(tenant_a.id, page=1, page_size=10)
        assert len(matters_a) == 1
        assert matters_a[0].id == matter_a.id

        matters_b = await repo.get_all(tenant_b.id, page=1, page_size=10)
        assert len(matters_b) == 1
        assert matters_b[0].id == matter_b.id


class TestConnectionPoolIsolation:
    """Tests for connection pool isolation."""

    @pytest.mark.integration
    async def test_tenant_context_not_leaked_across_requests(
        self, db_session: AsyncSession, tenant_a: Firm, tenant_b: Firm, user_a: User, user_b: User
    ):
        """Test that tenant context doesn't leak across pooled connections."""
        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=tenant_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=tenant_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        # Request 1: Tenant A
        context_a = TenantContext(tenant_id=tenant_a.id, firm=tenant_a, user_id=user_a.id)
        set_tenant_context(context_a)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_a.id}'"))

        result = await db_session.execute(select(Client))
        clients_a = result.scalars().all()
        assert len(clients_a) == 1
        assert clients_a[0].id == client_a.id
        clear_tenant_context()

        # Request 2: Tenant B (simulating connection reuse from pool)
        context_b = TenantContext(tenant_id=tenant_b.id, firm=tenant_b, user_id=user_b.id)
        set_tenant_context(context_b)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_b.id}'"))

        result = await db_session.execute(select(Client))
        clients_b = result.scalars().all()
        assert len(clients_b) == 1
        assert clients_b[0].id == client_b.id
        clear_tenant_context()

        # Request 3: Tenant A again
        context_a2 = TenantContext(tenant_id=tenant_a.id, firm=tenant_a, user_id=user_a.id)
        set_tenant_context(context_a2)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_a.id}'"))

        result = await db_session.execute(select(Client))
        clients_a2 = result.scalars().all()
        assert len(clients_a2) == 1
        assert clients_a2[0].id == client_a.id
        clear_tenant_context()

    @pytest.mark.integration
    async def test_get_tenant_db_dependency(
        self, db_session: AsyncSession, tenant_a: Firm
    ):
        """Test that get_tenant_db dependency works correctly."""
        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=tenant_a.id)
        db_session.add(client_a)
        await db_session.flush()

        # Use get_tenant_db dependency
        from app.core.database.session import get_tenant_db
        from app.core.tenancy.context import TenantContext, set_tenant_context

        context = TenantContext(tenant_id=tenant_a.id, firm=tenant_a)
        set_tenant_context(context)

        async for session in get_tenant_db():
            result = await session.execute(select(Client))
            clients = result.scalars().all()
            assert len(clients) == 1
            break

        clear_tenant_context()

        # Without context - should see nothing
        clear_tenant_context()
        async for session in get_tenant_db():
            result = await session.execute(select(Client))
            clients = result.scalars().all()
            assert len(clients) == 0
            break