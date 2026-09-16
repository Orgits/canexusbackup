# Workload CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.workload.models import UserAvailability, TeamCapacity, WorkloadSnapshot, WorkloadSummary, WorkloadPeriod
from app.modules.firms.models import Firm
from app.modules.users.models import User, Team
from app.modules.clients.models import Client
from app.modules.tasks.models import Task, TaskStatus, TaskPriority
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestWorkloadCRUD:
    """Tests for Workload CRUD operations."""

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
    async def test_team(self, db_session: AsyncSession, test_firm: Firm, test_user: User) -> Team:
        team = Team(
            name="Test Team",
            department="Tax",
            specialization=["ITR", "GST"],
            lead_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)
        return team

    @pytest.mark.integration
    async def test_create_user_availability(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        availability = UserAvailability(
            user_id=test_user.id,
            availability_date=date(2025, 1, 15),
            available_hours=8.0,
            reason="Normal working day",
            tenant_id=test_firm.id,
        )
        db_session.add(availability)
        await db_session.flush()
        await db_session.refresh(availability)

        assert availability.id is not None
        assert availability.available_hours == 8.0
        assert availability.reason == "Normal working day"

    @pytest.mark.integration
    async def test_bulk_user_availability(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        availabilities = [
            UserAvailability(
                user_id=test_user.id,
                availability_date=date(2025, 1, 15) + timedelta(days=i),
                available_hours=8.0 if i < 5 else 4.0,
                reason="Normal" if i < 5 else "Half day",
                tenant_id=test_firm.id,
            )
            for i in range(10)
        ]
        db_session.add_all(availabilities)
        await db_session.flush()

        assert len(availabilities) == 10
        assert all(a.tenant_id == test_firm.id for a in availabilities)

    @pytest.mark.integration
    async def test_create_team_capacity(self, db_session: AsyncSession, test_firm: Firm, test_team: Team):
        capacity = TeamCapacity(
            team_id=test_team.id,
            period_type=WorkloadPeriod.WEEKLY,
            period_start=date(2025, 1, 13),
            period_end=date(2025, 1, 19),
            allocated_hours=160.0,
            available_hours=200.0,
            tenant_id=test_firm.id,
        )
        db_session.add(capacity)
        await db_session.flush()
        await db_session.refresh(capacity)

        assert capacity.id is not None
        assert capacity.team_id == test_team.id
        assert capacity.period_type == WorkloadPeriod.WEEKLY
        assert capacity.utilization_percentage == 80.0

    @pytest.mark.integration
    async def test_create_workload_snapshot(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        # Create some tasks first
        client = Client(name="Test Client", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=test_user.id)
        db_session.add(client)
        await db_session.flush()

        tasks = [
            Task(
                title=f"Task {i}",
                status=TaskStatus.TODO if i % 2 == 0 else TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH if i % 3 == 0 else TaskPriority.NORMAL,
                due_date=date.today() - timedelta(days=i) if i < 3 else date.today() + timedelta(days=3),
                client_id=client.id,
                assigned_user_id=test_user.id,
                tenant_id=test_firm.id,
            )
            for i in range(5)
        ]
        db_session.add_all(tasks)
        await db_session.flush()

        snapshot = WorkloadSnapshot(
            user_id=test_user.id,
            snapshot_date=date.today(),
            period_type=WorkloadPeriod.DAILY,
            open_tasks=5,
            overdue_tasks=2,
            open_matters=2,
            overdue_matters=0,
            high_priority_tasks=2,
            available_hours=8.0,
            allocated_hours=10.0,
            utilization_percentage=125.0,
            tenant_id=test_firm.id,
        )
        db_session.add(snapshot)
        await db_session.flush()
        await db_session.refresh(snapshot)

        assert snapshot.id is not None
        assert snapshot.user_id == test_user.id
        assert snapshot.utilization_percentage == 125.0

    @pytest.mark.integration
    async def test_create_workload_summary(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        summary = WorkloadSummary(
            user_id=test_user.id,
            summary_date=date.today(),
            period_type=WorkloadPeriod.WEEKLY,
            avg_open_tasks=4.5,
            avg_overdue_tasks=1.0,
            avg_utilization=110.0,
            peak_utilization=130.0,
            tenant_id=test_firm.id,
        )
        db_session.add(summary)
        await db_session.flush()
        await db_session.refresh(summary)

        assert summary.id is not None
        assert summary.avg_utilization == 110.0
        assert summary.peak_utilization == 130.0


class TestWorkloadTenantIsolation:
    """Tests for Workload tenant isolation."""

    @pytest.mark.integration
    async def test_workload_tenant_isolation(
        self, db_session: AsyncSession, test_firm: Firm
    ):
        from sqlalchemy import text

        # Create second firm
        other_firm = Firm(name="Other Firm", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        # Create users
        user_a = User(email="usera@firm-a.com", hashed_password="hashed", full_name="User A", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        user_b = User(email="userb@firm-b.com", hashed_password="hashed", full_name="User B", tenant_id=other_firm.id, roles=["associate"], is_active=True)
        db_session.add_all([user_a, user_b])
        await db_session.flush()

        # Create availabilities
        avail_a = UserAvailability(user_id=user_a.id, availability_date=date(2025, 1, 15), available_hours=8.0, tenant_id=test_firm.id)
        avail_b = UserAvailability(user_id=user_b.id, availability_date=date(2025, 1, 15), available_hours=8.0, tenant_id=other_firm.id)
        db_session.add_all([avail_a, avail_b])
        await db_session.flush()

        # Test isolation
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(UserAvailability))
        avails = result.scalars().all()
        assert len(avails) == 1
        assert avails[0].id == avail_a.id

        clear_tenant_context()

        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(UserAvailability))
        avails = result.scalars().all()
        assert len(avails) == 1
        assert avails[0].id == avail_b.id

        clear_tenant_context()