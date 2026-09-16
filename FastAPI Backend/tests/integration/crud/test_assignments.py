# Assignment CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.assignments.models import Assignment, Escalation
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.matters.models import Matter
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestAssignmentCRUD:
    """Tests for Assignment CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(
            email="user@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Test User",
            tenant_id=test_firm.id,
            roles=["associate"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def test_client(self, db_session: AsyncSession, test_firm: Firm, test_user: User) -> Client:
        client = Client(name="Test Client", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=test_user.id)
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)
        return client

    @pytest_asyncio.fixture
    async def test_matter(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User) -> Matter:
        from app.modules.matters.models import MatterType, MatterStatus, MatterPriority
        matter = Matter(
            name="Test Matter",
            matter_type=MatterType.TAX,
            status=MatterStatus.IN_PROGRESS,
            priority=MatterPriority.HIGH,
            client_id=test_client.id,
            responsible_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(matter)
        await db_session.flush()
        await db_session.refresh(matter)
        return matter

    @pytest.mark.integration
    async def test_create_assignment(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User, test_matter: Matter):
        assignment = Assignment(
            entity_type="matter",
            entity_id=test_matter.id,
            assigned_user_id=test_user.id,
            assigned_by_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(assignment)
        await db_session.flush()
        await db_session.refresh(assignment)

        assert assignment.id is not None
        assert assignment.entity_type == "matter"
        assert assignment.assigned_user_id == test_user.id

    @pytest.mark.integration
    async def test_assignment_history_created(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User, test_matter: Matter):
        """Test that assignment history is created on assignment."""
        from app.modules.assignments.models import AssignmentHistory

        assignment = Assignment(
            entity_type="matter",
            entity_id=test_matter.id,
            assigned_user_id=test_user.id,
            assigned_by_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(assignment)
        await db_session.flush()

        # Check history was created
        result = await db_session.execute(
            select(AssignmentHistory).where(AssignmentHistory.assignment_id == assignment.id)
        )
        history = result.scalars().all()
        assert len(history) >= 1
        assert history[0].action == "ASSIGNED"

    @pytest.mark.integration
    async def test_reassign_entity(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User, test_matter: Matter):
        """Test reassignment creates history."""
        from app.modules.assignments.models import AssignmentHistory

        # Create initial assignment
        assignment = Assignment(
            entity_type="matter",
            entity_id=test_matter.id,
            assigned_user_id=test_user.id,
            assigned_by_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(assignment)
        await db_session.flush()

        # Create second user
        user2 = User(
            email="user2@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="User Two",
            tenant_id=test_firm.id,
            roles=["associate"],
            is_active=True,
        )
        db_session.add(user2)
        await db_session.flush()

        # Reassign
        old_user_id = assignment.assigned_user_id
        assignment.assigned_user_id = user2.id
        assignment.assigned_by_id = test_user.id
        await db_session.flush()

        # Check history
        result = await db_session.execute(
            select(AssignmentHistory).where(AssignmentHistory.assignment_id == assignment.id).order_by(AssignmentHistory.created_at)
        )
        history = result.scalars().all()
        assert len(history) >= 2
        assert history[-1].action == "REASSIGNED"
        assert history[-1].from_user_id == old_user_id
        assert history[-1].to_user_id == user2.id

    @pytest.mark.integration
    async def test_create_escalation(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User, test_matter: Matter):
        escalation = Escalation(
            entity_type="matter",
            entity_id=test_matter.id,
            escalated_from_id=test_user.id,
            escalated_to_id=test_user.id,
            reason="OVERDUE",
            tenant_id=test_firm.id,
        )
        db_session.add(escalation)
        await db_session.flush()
        await db_session.refresh(escalation)

        assert escalation.id is not None
        assert escalation.reason == "OVERDUE"

    @pytest.mark.integration
    async def test_escalation_resolution(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User, test_matter: Matter):
        escalation = Escalation(
            entity_type="matter",
            entity_id=test_matter.id,
            escalated_from_id=test_user.id,
            escalated_to_id=test_user.id,
            reason="OVERDUE",
            tenant_id=test_firm.id,
        )
        db_session.add(escalation)
        await db_session.flush()

        # Resolve escalation
        escalation.resolved_at = datetime.now()
        escalation.resolved_by_id = test_user.id
        await db_session.flush()

        assert escalation.resolved_at is not None
        assert escalation.resolved_by_id == test_user.id


class TestAssignmentTenantIsolation:
    """Tests for Assignment tenant isolation."""

    @pytest.mark.integration
    async def test_assignment_tenant_isolation(
        self, db_session: AsyncSession, test_firm: Firm
    ):
        """Test that assignments are isolated by tenant."""
        # Create second firm
        other_firm = Firm(name="Other Firm", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        # Create users for each firm
        user_a = User(email="usera@firm-a.com", hashed_password=hash_password("Pass123!"), full_name="User A", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        user_b = User(email="userb@firm-b.com", hashed_password=hash_password("Pass123!"), full_name="User B", tenant_id=other_firm.id, roles=["associate"], is_active=True)
        db_session.add_all([user_a, user_b])
        await db_session.flush()

        # Create clients
        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=user_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=other_firm.id, responsible_user_id=user_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        # Create matters
        from app.modules.matters.models import MatterType, MatterStatus, MatterPriority
        matter_a = Matter(name="Matter A", matter_type=MatterType.TAX, status=MatterStatus.IN_PROGRESS, priority=MatterPriority.HIGH, client_id=client_a.id, responsible_user_id=user_a.id, tenant_id=test_firm.id)
        matter_b = Matter(name="Matter B", matter_type=MatterType.TAX, status=MatterStatus.IN_PROGRESS, priority=MatterPriority.HIGH, client_id=client_b.id, responsible_user_id=user_b.id, tenant_id=other_firm.id)
        db_session.add_all([matter_a, matter_b])
        await db_session.flush()

        # Create assignments
        assignment_a = Assignment(entity_type="matter", entity_id=matter_a.id, assigned_user_id=user_a.id, assigned_by_id=user_a.id, tenant_id=test_firm.id)
        assignment_b = Assignment(entity_type="matter", entity_id=matter_b.id, assigned_user_id=user_b.id, assigned_by_id=user_b.id, tenant_id=other_firm.id)
        db_session.add_all([assignment_a, assignment_b])
        await db_session.flush()

        # Set tenant context to Firm A
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        # Query assignments - should only see Firm A's
        result = await db_session.execute(select(Assignment))
        assignments = result.scalars().all()
        assert len(assignments) == 1
        assert assignments[0].id == assignment_a.id

        clear_tenant_context()

        # Set tenant context to Firm B
        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(Assignment))
        assignments = result.scalars().all()
        assert len(assignments) == 1
        assert assignments[0].id == assignment_b.id

        clear_tenant_context()


from datetime import datetime
from sqlalchemy import text