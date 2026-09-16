# TDS CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.tds.models import TDSComplianceCycle, TDSChallan, TDSDeductee, TDSFormType, TDSStatus
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestTDSCRUD:
    """Tests for TDS CRUD operations."""

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

    @pytest.mark.integration
    async def test_create_tds_compliance_cycle(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        cycle = TDSComplianceCycle(
            client_id=test_client.id,
            form_type=TDSFormType.FORM_24Q,
            financial_year="2025-2026",
            quarter="Q1",
            period_start=date(2025, 4, 1),
            period_end=date(2025, 6, 30),
            due_date=date(2025, 7, 31),
            status=TDSStatus.PENDING,
            priority="HIGH",
            assigned_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()
        await db_session.refresh(cycle)

        assert cycle.id is not None
        assert cycle.form_type == TDSFormType.FORM_24Q
        assert cycle.financial_year == "2025-2026"
        assert cycle.quarter == "Q1"
        assert cycle.status == TDSStatus.PENDING

    @pytest.mark.integration
    async def test_tds_cycle_status_transitions(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        cycle = TDSComplianceCycle(
            client_id=test_client.id,
            form_type=TDSFormType.FORM_26Q,
            financial_year="2025-2026",
            quarter="Q2",
            period_start=date(2025, 7, 1),
            period_end=date(2025, 9, 30),
            due_date=date(2025, 10, 31),
            status=TDSStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()

        # Test valid transitions
        cycle.status = TDSStatus.DATA_COLLECTION
        await db_session.flush()
        assert cycle.status == TDSStatus.DATA_COLLECTION

        cycle.status = TDSStatus.VALIDATION
        await db_session.flush()
        assert cycle.status == TDSStatus.VALIDATION

        cycle.status = TDSStatus.READY_FOR_FILING
        await db_session.flush()
        assert cycle.status == TDSStatus.READY_FOR_FILING

        cycle.status = TDSStatus.FILED
        cycle.token_number = "TOKEN123456"
        cycle.acknowledgment_number = "ACK123456"
        cycle.filing_date = date(2025, 10, 15)
        await db_session.flush()
        assert cycle.status == TDSStatus.FILED

        cycle.status = TDSStatus.PROCESSED
        cycle.processed_date = date(2025, 11, 1)
        await db_session.flush()
        assert cycle.status == TDSStatus.PROCESSED

    @pytest.mark.integration
    async def test_create_tds_challan(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        cycle = TDSComplianceCycle(
            client_id=test_client.id,
            form_type=TDSFormType.FORM_24Q,
            financial_year="2025-2026",
            quarter="Q1",
            period_start=date(2025, 4, 1),
            period_end=date(2025, 6, 30),
            due_date=date(2025, 7, 31),
            status=TDSStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()

        challan = TDSChallan(
            cycle_id=cycle.id,
            challan_serial_no="12345",
            bsr_code="1234567",
            challan_date=date(2025, 7, 15),
            amount=50000.00,
            cin="123456789012345",
            tenant_id=test_firm.id,
        )
        db_session.add(challan)
        await db_session.flush()
        await db_session.refresh(challan)

        assert challan.id is not None
        assert challan.cycle_id == cycle.id
        assert challan.amount == 50000.00

    @pytest.mark.integration
    async def test_create_tds_deductee(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        cycle = TDSComplianceCycle(
            client_id=test_client.id,
            form_type=TDSFormType.FORM_24Q,
            financial_year="2025-2026",
            quarter="Q1",
            period_start=date(2025, 4, 1),
            period_end=date(2025, 6, 30),
            due_date=date(2025, 7, 31),
            status=TDSStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()

        deductee = TDSDeductee(
            cycle_id=cycle.id,
            deductee_name="Test Deductee",
            deductee_pan="ABCDE1234F",
            section="192",
            amount_paid=100000.00,
            tax_deducted=10000.00,
            tax_deposited=10000.00,
            tenant_id=test_firm.id,
        )
        db_session.add(deductee)
        await db_session.flush()
        await db_session.refresh(deductee)

        assert deductee.id is not None
        assert deductee.deductee_pan == "ABCDE1234F"
        assert deductee.tax_deducted == 10000.00


class TestTDSTenantIsolation:
    """Tests for TDS tenant isolation."""

    @pytest.mark.integration
    async def test_tds_cycle_tenant_isolation(
        self, db_session: AsyncSession, test_firm: Firm
    ):
        from sqlalchemy import text

        # Create second firm
        other_firm = Firm(name="Other Firm", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        # Create users and clients
        user_a = User(email="usera@firm-a.com", hashed_password="hashed", full_name="User A", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        user_b = User(email="userb@firm-b.com", hashed_password="hashed", full_name="User B", tenant_id=other_firm.id, roles=["associate"], is_active=True)
        db_session.add_all([user_a, user_b])
        await db_session.flush()

        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=user_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=other_firm.id, responsible_user_id=user_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        # Create cycles
        cycle_a = TDSComplianceCycle(client_id=client_a.id, form_type="24Q", financial_year="2025-2026", quarter="Q1", period_start=date(2025, 4, 1), period_end=date(2025, 6, 30), due_date=date(2025, 7, 31), status="PENDING", tenant_id=test_firm.id)
        cycle_b = TDSComplianceCycle(client_id=client_b.id, form_type="24Q", financial_year="2025-2026", quarter="Q1", period_start=date(2025, 4, 1), period_end=date(2025, 6, 30), due_date=date(2025, 7, 31), status="PENDING", tenant_id=other_firm.id)
        db_session.add_all([cycle_a, cycle_b])
        await db_session.flush()

        # Test isolation
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(TDSComplianceCycle))
        cycles = result.scalars().all()
        assert len(cycles) == 1
        assert cycles[0].id == cycle_a.id

        clear_tenant_context()

        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(TDSComplianceCycle))
        cycles = result.scalars().all()
        assert len(cycles) == 1
        assert cycles[0].id == cycle_b.id

        clear_tenant_context()