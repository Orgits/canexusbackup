# Outbox CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.outbox.models import OutboxEvent, OutboxEventType, OutboxStatus
from app.modules.firms.models import Firm
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestOutboxCRUD:
    """Tests for Outbox CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest.mark.integration
    async def test_create_outbox_event(self, db_session: AsyncSession, test_firm: Firm):
        event = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"document_id": "doc-123", "filename": "test.pdf"},
            status=OutboxStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()
        await db_session.refresh(event)

        assert event.id is not None
        assert event.event_type == OutboxEventType.DOCUMENT_UPLOADED
        assert event.aggregate_type == "document"
        assert event.status == OutboxStatus.PENDING
        assert event.payload["filename"] == "test.pdf"

    @pytest.mark.integration
    async def test_outbox_event_with_idempotency_key(self, db_session: AsyncSession, test_firm: Firm):
        idempotency_key = "doc-upload-123"
        
        event = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"document_id": "doc-123"},
            status=OutboxStatus.PENDING,
            idempotency_key=idempotency_key,
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Try to create duplicate
        from sqlalchemy.exc import IntegrityError
        event2 = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"document_id": "doc-456"},
            status=OutboxStatus.PENDING,
            idempotency_key=idempotency_key,
            tenant_id=test_firm.id,
        )
        db_session.add(event2)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.integration
    async def test_outbox_event_retry_logic(self, db_session: AsyncSession, test_firm: Firm):
        event = OutboxEvent(
            event_type=OutboxEventType.COMPLIANCE_CYCLE_CREATED,
            aggregate_type="compliance_cycle",
            aggregate_id=uuid4(),
            payload={"cycle_id": "cycle-123"},
            status=OutboxStatus.PENDING,
            retry_count=0,
            max_retries=5,
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Simulate retry
        event.retry_count += 1
        event.last_error = "Temporary failure"
        await db_session.flush()

        assert event.retry_count == 1
        assert event.last_error == "Temporary failure"

    @pytest.mark.integration
    async def test_outbox_event_max_retries_exceeded(self, db_session: AsyncSession, test_firm: Firm):
        event = OutboxEvent(
            event_type=OutboxEventType.COMPLIANCE_CYCLE_CREATED,
            aggregate_type="compliance_cycle",
            aggregate_id=uuid4(),
            payload={"cycle_id": "cycle-123"},
            status=OutboxStatus.FAILED,
            retry_count=5,
            max_retries=5,
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Should be marked as dead_letter
        event.status = OutboxStatus.DEAD_LETTER
        await db_session.flush()

        assert event.status == OutboxStatus.DEAD_LETTER

    @pytest.mark.integration
    async def test_outbox_event_processed(self, db_session: AsyncSession, test_firm: Firm):
        event = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"document_id": "doc-123"},
            status=OutboxStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Mark as processed
        event.status = OutboxStatus.PROCESSED
        event.processed_at = datetime.now(UTC)
        await db_session.flush()

        assert event.status == OutboxStatus.PROCESSED
        assert event.processed_at is not None


class TestOutboxTenantIsolation:
    """Tests for Outbox tenant isolation."""

    @pytest.mark.integration
    async def test_outbox_tenant_isolation(
        self, db_session: AsyncSession, test_firm: Firm
    ):
        from sqlalchemy import text

        # Create second firm
        other_firm = Firm(name="Other Firm", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        # Create events
        event_a = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"test": "data_a"},
            status=OutboxStatus.PENDING,
            tenant_id=test_firm.id,
        )
        event_b = OutboxEvent(
            event_type=OutboxEventType.COMPLIANCE_CYCLE_CREATED,
            aggregate_type="compliance_cycle",
            aggregate_id=uuid4(),
            payload={"test": "data_b"},
            status=OutboxStatus.PENDING,
            tenant_id=other_firm.id,
        )
        db_session.add_all([event_a, event_b])
        await db_session.flush()

        # Test isolation
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=None)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(OutboxEvent))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].id == event_a.id

        clear_tenant_context()

        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=None)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(OutboxEvent))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].id == event_b.id

        clear_tenant_context()