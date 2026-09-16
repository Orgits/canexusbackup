# Notices CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.notices.models import Notice, NoticeEscalation, NoticeAuthority, NoticeType, NoticeStatus, NoticePriority
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestNoticesCRUD:
    """Tests for Notices CRUD operations."""

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
    async def test_create_notice(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        notice = Notice(
            notice_number="IT-2025-001",
            authority=NoticeAuthority.INCOME_TAX,
            notice_type=NoticeType.SHOW_CAUSE,
            subject="Show Cause Notice for AY 2023-24",
            description="Discrepancy in reported income",
            client_id=test_client.id,
            responsible_user_id=test_user.id,
            received_date=date(2025, 1, 15),
            deadline_date=date(2025, 2, 15),
            priority=NoticePriority.HIGH,
            status=NoticeStatus.RECEIVED,
            tenant_id=test_firm.id,
        )
        db_session.add(notice)
        await db_session.flush()
        await db_session.refresh(notice)

        assert notice.id is not None
        assert notice.notice_number == "IT-2025-001"
        assert notice.authority == NoticeAuthority.INCOME_TAX
        assert notice.status == NoticeStatus.RECEIVED

    @pytest.mark.integration
    async def test_notice_status_transitions(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        notice = Notice(
            notice_number="GST-2025-001",
            authority=NoticeAuthority.GST,
            notice_type=NoticeType.DEMAND,
            subject="GST Demand Notice",
            client_id=test_client.id,
            responsible_user_id=test_user.id,
            received_date=date(2025, 1, 15),
            deadline_date=date(2025, 2, 15),
            priority=NoticePriority.HIGH,
            status=NoticeStatus.RECEIVED,
            tenant_id=test_firm.id,
        )
        db_session.add(notice)
        await db_session.flush()

        # Test valid transitions
        notice.status = NoticeStatus.ACKNOWLEDGED
        notice.acknowledged_at = datetime.now()
        await db_session.flush()
        assert notice.status == NoticeStatus.ACKNOWLEDGED

        notice.status = NoticeStatus.UNDER_REVIEW
        await db_session.flush()
        assert notice.status == NoticeStatus.UNDER_REVIEW

        notice.status = NoticeStatus.RESPONSE_DRAFTING
        await db_session.flush()
        assert notice.status == NoticeStatus.RESPONSE_DRAFTING

        notice.status = NoticeStatus.RESPONSE_REVIEW
        await db_session.flush()
        assert notice.status == NoticeStatus.RESPONSE_REVIEW

        notice.status = NoticeStatus.RESPONSE_APPROVED
        await db_session.flush()
        assert notice.status == NoticeStatus.RESPONSE_APPROVED

        notice.status = NoticeStatus.RESPONDED
        notice.response_filed_date = datetime.now()
        await db_session.flush()
        assert notice.status == NoticeStatus.RESPONDED

    @pytest.mark.integration
    async def test_notice_escalation(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        notice = Notice(
            notice_number="IT-2025-002",
            authority=NoticeAuthority.INCOME_TAX,
            notice_type=NoticeType.SHOW_CAUSE,
            subject="Show Cause Notice",
            client_id=test_client.id,
            responsible_user_id=test_user.id,
            received_date=date(2025, 1, 15),
            deadline_date=date(2025, 2, 15),
            status=NoticeStatus.RECEIVED,
            tenant_id=test_firm.id,
        )
        db_session.add(notice)
        await db_session.flush()

        # Create escalation
        user2 = User(
            email="user2@example.com",
            hashed_password="hashed",
            full_name="User Two",
            tenant_id=test_firm.id,
            roles=["partner"],
            is_active=True,
        )
        db_session.add(user2)
        await db_session.flush()

        escalation = NoticeEscalation(
            notice_id=notice.id,
            escalated_from_id=test_user.id,
            escalated_to_id=user2.id,
            reason="EXPERTISE_REQUIRED",
            escalated_by_id=test_user.id,
            original_deadline=notice.deadline_date,
            new_deadline=date(2025, 3, 1),
            tenant_id=test_firm.id,
        )
        db_session.add(escalation)
        await db_session.flush()
        await db_session.refresh(escalation)

        assert escalation.id is not None
        assert escalation.reason == "EXPERTISE_REQUIRED"
        assert escalation.escalated_to_id == user2.id

    @pytest.mark.integration
    async def test_notice_response_tracking(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User):
        notice = Notice(
            notice_number="IT-2025-003",
            authority=NoticeAuthority.INCOME_TAX,
            notice_type=NoticeType.SCRUTINY,
            subject="Scrutiny Notice",
            client_id=test_client.id,
            responsible_user_id=test_user.id,
            received_date=date(2025, 1, 15),
            deadline_date=date(2025, 2, 15),
            status=NoticeStatus.RECEIVED,
            tenant_id=test_firm.id,
        )
        db_session.add(notice)
        await db_session.flush()

        # Update response
        notice.status = NoticeStatus.RESPONSE_DRAFTING
        notice.response_draft = "Draft response to scrutiny notice"
        notice.response_prepared_by_id = test_user.id
        await db_session.flush()

        assert notice.response_draft == "Draft response to scrutiny notice"

        # Submit response
        notice.status = NoticeStatus.RESPONDED
        notice.response_filed_date = datetime.now()
        notice.response_mode = "ONLINE"
        notice.acknowledgment_number = "ACK123456"
        await db_session.flush()

        assert notice.response_filed_date is not None
        assert notice.response_mode == "ONLINE"
        assert notice.acknowledgment_number == "ACK123456"


class TestNoticesTenantIsolation:
    """Tests for Notices tenant isolation."""

    @pytest.mark.integration
    async def test_notice_tenant_isolation(
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

        # Create clients
        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=user_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=other_firm.id, responsible_user_id=user_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        # Create notices
        notice_a = Notice(notice_number="IT-001", authority="INCOME_TAX", notice_type="SHOW_CAUSE", subject="Notice A", client_id=client_a.id, responsible_user_id=user_a.id, received_date=date(2025, 1, 15), deadline_date=date(2025, 2, 15), priority="HIGH", status="RECEIVED", tenant_id=test_firm.id)
        notice_b = Notice(notice_number="IT-002", authority="INCOME_TAX", notice_type="SHOW_CAUSE", subject="Notice B", client_id=client_b.id, responsible_user_id=user_b.id, received_date=date(2025, 1, 15), deadline_date=date(2025, 2, 15), priority="HIGH", status="RECEIVED", tenant_id=other_firm.id)
        db_session.add_all([notice_a, notice_b])
        await db_session.flush()

        # Test isolation
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(Notice))
        notices = result.scalars().all()
        assert len(notices) == 1
        assert notices[0].id == notice_a.id

        clear_tenant_context()

        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(Notice))
        notices = result.scalars().all()
        assert len(notices) == 1
        assert notices[0].id == notice_b.id

        clear_tenant_context()