# MCA/ROC CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.mca_roc.models import MCAFilingConfig, MCAFilingCycle, MCAEntityType, MCAFilingCategory, MCAStatus
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestMCAROCCRUD:
    """Tests for MCA/ROC CRUD operations."""

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
    async def test_create_mca_filing_config(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        config = MCAFilingConfig(
            code="MGT-7_TEST",
            name="Annual Return Test",
            entity_type=MCAEntityType.COMPANY,
            filing_category=MCAFilingCategory.ANNUAL,
            form_number="MGT-7",
            description="Test annual return filing",
            due_date_rule="Within 60 days of AGM",
            period_rule="Financial Year",
            fee_structure={"base": 600, "additional_per_day": 100},
            default_checklist=[{"item": "Board resolution"}, {"item": "Financial statements"}],
            default_document_requirements=[{"doc": "Audited financials"}, {"doc": "Board report"}],
            default_workflow_stages=[{"stage": "Document Collection"}, {"stage": "Board Approval"}],
            is_active=True,
            is_system=True,
            tenant_id=test_firm.id,
        )
        db_session.add(config)
        await db_session.flush()
        await db_session.refresh(config)

        assert config.id is not None
        assert config.code == "MGT-7_TEST"
        assert config.entity_type == MCAEntityType.COMPANY
        assert config.filing_category == MCAFilingCategory.ANNUAL

    @pytest.mark.integration
    async def test_create_mca_filing_cycle(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        # Create config first
        config = MCAFilingConfig(
            code="MGT-7",
            name="Annual Return",
            entity_type=MCAEntityType.COMPANY,
            filing_category=MCAFilingCategory.ANNUAL,
            form_number="MGT-7",
            due_date_rule="Within 60 days of AGM",
            period_rule="Financial Year",
            tenant_id=test_firm.id,
        )
        db_session.add(config)
        await db_session.flush()

        cycle = MCAFilingCycle(
            client_id=test_client.id,
            config_id=config.id,
            entity_type=MCAEntityType.COMPANY,
            financial_year="2025-2026",
            agm_date=date(2025, 9, 30),
            due_date=date(2025, 11, 29),
            status=MCAStatus.PENDING,
            priority="HIGH",
            assigned_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()
        await db_session.refresh(cycle)

        assert cycle.id is not None
        assert cycle.form_number == "MGT-7"
        assert cycle.financial_year == "2025-2026"
        assert cycle.status == MCAStatus.PENDING

    @pytest.mark.integration
    async def test_mca_cycle_status_transitions(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        config = MCAFilingConfig(
            code="AOC-4",
            name="Financial Statements",
            entity_type=MCAEntityType.COMPANY,
            filing_category=MCAFilingCategory.ANNUAL,
            form_number="AOC-4",
            tenant_id=test_firm.id,
        )
        db_session.add(config)
        await db_session.flush()

        cycle = MCAFilingCycle(
            client_id=test_client.id,
            config_id=config.id,
            entity_type=MCAEntityType.COMPANY,
            financial_year="2025-2026",
            due_date=date(2025, 10, 31),
            status=MCAStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()

        # Test valid transitions
        cycle.status = MCAStatus.DOCUMENT_COLLECTION
        await db_session.flush()
        assert cycle.status == MCAStatus.DOCUMENT_COLLECTION

        cycle.status = MCAStatus.PREPARATION
        await db_session.flush()
        assert cycle.status == MCAStatus.PREPARATION

        cycle.status = MCAStatus.REVIEW
        await db_session.flush()
        assert cycle.status == MCAStatus.REVIEW

        cycle.status = MCAStatus.BOARD_APPROVAL
        await db_session.flush()
        assert cycle.status == MCAStatus.BOARD_APPROVAL

        cycle.status = MCAStatus.READY_FOR_FILING
        await db_session.flush()
        assert cycle.status == MCAStatus.READY_FOR_FILING

    @pytest.mark.integration
    async def test_mca_cycle_agm_completion(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        config = MCAFilingConfig(
            code="MGT-7_AGM",
            name="Annual Return with AGM",
            entity_type=MCAEntityType.COMPANY,
            filing_category=MCAFilingCategory.ANNUAL,
            form_number="MGT-7",
            tenant_id=test_firm.id,
        )
        db_session.add(config)
        await db_session.flush()

        cycle = MCAFilingCycle(
            client_id=test_client.id,
            config_id=config.id,
            entity_type=MCAEntityType.COMPANY,
            financial_year="2025-2026",
            agm_date=date(2025, 9, 30),
            due_date=date(2025, 11, 29),
            status=MCAStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()

        # Set AGM date
        cycle.agm_date = date(2025, 9, 30)
        cycle.agm_completed = True
        await db_session.flush()

        assert cycle.agm_date == date(2025, 9, 30)
        assert cycle.agm_completed is True

    @pytest.mark.integration
    async def test_mca_cycle_filing_and_approval(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        config = MCAFilingConfig(
            code="MGT-7_FILE",
            name="Annual Return Filing",
            entity_type=MCAEntityType.COMPANY,
            filing_category=MCAFilingCategory.ANNUAL,
            form_number="MGT-7",
            tenant_id=test_firm.id,
        )
        db_session.add(config)
        await db_session.flush()

        cycle = MCAFilingCycle(
            client_id=test_client.id,
            config_id=config.id,
            entity_type=MCAEntityType.COMPANY,
            financial_year="2025-2026",
            due_date=date(2025, 11, 29),
            status=MCAStatus.READY_FOR_FILING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()

        # Mark as filed
        cycle.status = MCAStatus.FILED
        cycle.srn = "F12345678"
        cycle.acknowledgment_number = "ACK123456"
        cycle.filing_date = date(2025, 11, 15)
        cycle.challan_amount = 600.0
        await db_session.flush()

        assert cycle.status == MCAStatus.FILED
        assert cycle.srn == "F12345678"

        # Mark as approved
        cycle.status = MCAStatus.APPROVED
        cycle.approval_date = date(2025, 12, 1)
        await db_session.flush()

        assert cycle.status == MCAStatus.APPROVED
        assert cycle.approval_date == date(2025, 12, 1)


class TestMCAROCTenantIsolation:
    """Tests for MCA/ROC tenant isolation."""

    @pytest.mark.integration
    async def test_mca_config_tenant_isolation(
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

        # Create configs
        config_a = MCAFilingConfig(code="MGT-7_A", name="Config A", entity_type="COMPANY", filing_category="ANNUAL", form_number="MGT-7", tenant_id=test_firm.id)
        config_b = MCAFilingConfig(code="MGT-7_B", name="Config B", entity_type="COMPANY", filing_category="ANNUAL", form_number="MGT-7", tenant_id=other_firm.id)
        db_session.add_all([config_a, config_b])
        await db_session.flush()

        # Set tenant context to Firm A
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(MCAFilingConfig))
        configs = result.scalars().all()
        assert len(configs) == 1
        assert configs[0].id == config_a.id

        clear_tenant_context()

        # Set tenant context to Firm B
        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(MCAFilingConfig))
        configs = result.scalars().all()
        assert len(configs) == 1
        assert configs[0].id == config_b.id

        clear_tenant_context()

    @pytest.mark.integration
    async def test_mca_cycle_tenant_isolation(
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

        # Create configs
        config_a = MCAFilingConfig(code="MGT-7_A", name="Config A", entity_type="COMPANY", filing_category="ANNUAL", form_number="MGT-7", tenant_id=test_firm.id)
        config_b = MCAFilingConfig(code="MGT-7_B", name="Config B", entity_type="COMPANY", filing_category="ANNUAL", form_number="MGT-7", tenant_id=other_firm.id)
        db_session.add_all([config_a, config_b])
        await db_session.flush()

        # Create cycles
        cycle_a = MCAFilingCycle(client_id=client_a.id, config_id=config_a.id, entity_type="COMPANY", financial_year="2025-2026", due_date=date(2025, 11, 29), status="PENDING", tenant_id=test_firm.id)
        cycle_b = MCAFilingCycle(client_id=client_b.id, config_id=config_b.id, entity_type="COMPANY", financial_year="2025-2026", due_date=date(2025, 11, 29), status="PENDING", tenant_id=other_firm.id)
        db_session.add_all([cycle_a, cycle_b])
        await db_session.flush()

        # Test isolation
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(MCAFilingCycle))
        cycles = result.scalars().all()
        assert len(cycles) == 1
        assert cycles[0].id == cycle_a.id

        clear_tenant_context()

        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(MCAFilingCycle))
        cycles = result.scalars().all()
        assert len(cycles) == 1
        assert cycles[0].id == cycle_b.id

        clear_tenant_context()