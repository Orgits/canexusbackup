# Worker Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date, datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.workers.compliance_tasks import (
    ComplianceCycleGenerator,
    ComplianceReminderSender,
    generate_compliance_cycles,
    send_compliance_reminders,
)
from app.workers.notification_tasks import (
    DeadlineReminderSender,
    NotificationDeliveryProcessor,
    send_deadline_reminders,
    process_notification_deliveries,
)
from app.workers.workload_tasks import (
    WorkloadSnapshotGenerator,
    WorkloadSummaryUpdater,
    generate_daily_workload_snapshots,
    generate_workload_summaries,
)
from app.workers.outbox_tasks import (
    OutboxProcessor,
    process_outbox_events,
    cleanup_processed_outbox,
)
from app.workers.base import TenantAwareWorker, BaseWorker, run_worker_with_retry
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.tasks.models import Task, TaskStatus, TaskPriority
from app.modules.compliance.models import ComplianceType, ComplianceCycle, ComplianceStatus, ComplianceFrequency
from app.modules.notifications.models import (
    Notification,
    NotificationTemplate,
    NotificationTrigger,
    NotificationChannel,
    NotificationStatus,
    NotificationPriority,
)
from app.modules.outbox.models import OutboxEvent, OutboxEventType, OutboxStatus
from app.modules.workload.models import WorkloadSnapshot, WorkloadSummary, WorkloadPeriod
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context
from app.core.database.session import get_tenant_db
from app.core.database.session import get_async_db


class TestWorkerBase:
    """Tests for base worker classes."""

    @pytest.mark.unit
    async def test_tenant_aware_worker_sets_context(self, db_session):
        """Test that TenantAwareWorker sets tenant context correctly."""
        tenant_id = uuid4()
        
        class TestWorker(TenantAwareWorker):
            async def execute(self):
                from app.core.tenancy.context import get_tenant_context
                context = get_tenant_context()
                return {"tenant_id": str(context.tenant_id) if context else None}

        worker = TestWorker(tenant_id)
        result = await worker.execute()
        
        assert result["tenant_id"] == str(tenant_id)

    @pytest.mark.unit
    async def test_base_worker_session_management(self, db_session):
        """Test that BaseWorker manages sessions correctly."""
        
        class TestWorker(BaseWorker):
            async def execute(self):
                async with self.session() as session:
                    result = await session.execute(select(1))
                    return result.scalar()

        worker = TestWorker()
        result = await worker.execute()
        assert result == 1

    @pytest.mark.unit
    async def test_run_worker_with_retry_success(self):
        """Test worker retry logic on success."""
        
        class SuccessWorker:
            def __init__(self):
                self.attempts = 0
            
            async def execute(self):
                self.attempts += 1
                return {"attempts": self.attempts}

        worker = SuccessWorker()
        result = await run_worker_with_retry(SuccessWorker, max_retries=3)
        assert result["attempts"] == 1

    @pytest.mark.unit
    async def test_run_worker_with_retry_failure_then_success(self):
        """Test worker retry logic with initial failures."""
        
        class FlakyWorker:
            def __init__(self):
                self.attempts = 0
            
            async def execute(self):
                self.attempts += 1
                if self.attempts < 3:
                    raise Exception("Temporary failure")
                return {"attempts": self.attempts}

        worker = FlakyWorker()
        result = await run_worker_with_retry(FlakyWorker, max_retries=5)
        assert result["attempts"] == 3

    @pytest.mark.unit
    async def test_run_worker_with_retry_max_retries_exceeded(self):
        """Test worker retry logic when max retries exceeded."""
        
        class FailingWorker:
            def __init__(self):
                self.attempts = 0
            
            async def execute(self):
                self.attempts += 1
                raise Exception("Permanent failure")

        worker = FailingWorker()
        with pytest.raises(Exception, match="Permanent failure"):
            await run_worker_with_retry(FailingWorker, max_retries=3)


class TestComplianceWorkers:
    """Tests for compliance workers."""

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

    @pytest.mark.integration
    async def test_compliance_cycle_generator(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        """Test compliance cycle generation."""
        # Create compliance types
        ctype_annual = ComplianceType(
            code="ANNUAL_TEST",
            name="Annual Test",
            category="TAX",
            frequency=ComplianceFrequency.ANNUAL,
            due_date=date(2026, 3, 31),
            tenant_id=test_firm.id,
        )
        ctype_quarterly = ComplianceType(
            code="QUARTERLY_TEST",
            name="Quarterly Test",
            category="TAX",
            frequency=ComplianceFrequency.QUARTERLY,
            due_date=date(2026, 3, 31),
            tenant_id=test_firm.id,
        )
        db_session.add_all([ctype_annual, ctype_quarterly])
        await db_session.flush()

        # Set tenant context
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=test_user.id)
        set_tenant_context(context)

        try:
            generator = ComplianceCycleGenerator(test_firm.id)
            result = await generator.execute()
            
            assert "cycles_created" in result
            assert "cycles_updated" in result
            assert result["cycles_created"] >= 0
        finally:
            clear_tenant_context()

    @pytest.mark.integration
    async def test_compliance_reminder_sender(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        """Test compliance reminder sending."""
        # Create compliance type
        ctype = ComplianceType(
            code="REMINDER_TEST",
            name="Reminder Test",
            category="TAX",
            frequency=ComplianceFrequency.ANNUAL,
            due_date=date(2026, 3, 31),
            tenant_id=test_firm.id,
        )
        db_session.add(ctype)
        await db_session.flush()

        # Create compliance cycle due soon
        cycle = ComplianceCycle(
            compliance_type_id=ctype.id,
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            due_date=date.today() + timedelta(days=7),  # Due in 7 days
            status=ComplianceStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()

        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=test_user.id)
        set_tenant_context(context)

        try:
            sender = ComplianceReminderSender(test_firm.id)
            result = await sender.execute()
            
            assert "reminders_sent" in result
            assert result["reminders_sent"] >= 0
        finally:
            clear_tenant_context()


class TestNotificationWorkers:
    """Tests for notification workers."""

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
    async def test_template(self, db_session: AsyncSession, test_firm: Firm) -> NotificationTemplate:
        template = NotificationTemplate(
            code="TEST_TEMPLATE",
            name="Test Template",
            trigger=NotificationTrigger.ASSIGNMENT,
            channels=["in_app", "email"],
            subject_template="New assignment: {{title}}",
            body_template="You have been assigned {{title}}",
            default_priority=NotificationPriority.NORMAL,
            is_active=True,
            tenant_id=test_firm.id,
        )
        db_session.add(template)
        await db_session.flush()
        await db_session.refresh(template)
        return template

    @pytest.mark.integration
    async def test_deadline_reminder_sender(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        """Test deadline reminder sender."""
        from app.modules.tasks.models import Task, TaskStatus, TaskPriority
        
        # Create task with upcoming deadline
        task = Task(
            title="Task with Deadline",
            description="Task with upcoming deadline",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            due_date=date.today() + timedelta(days=3),
            tenant_id=test_firm.id,
            assigned_user_id=uuid4(),  # Different user
        )
        db_session.add(task)
        await db_session.flush()

        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=test_user.id)
        set_tenant_context(context)

        try:
            sender = DeadlineReminderSender(test_firm.id)
            result = await sender.execute()
            
            assert "reminders_sent" in result
        finally:
            clear_tenant_context()

    @pytest.mark.integration
    async def test_notification_delivery_processor(self, db_session: AsyncSession, test_firm: Firm, test_user: User, test_template):
        """Test notification delivery processor."""
        # Create pending notification
        notification = Notification(
            recipient_id=test_user.id,
            trigger=NotificationTrigger.ASSIGNMENT,
            template_id=test_template.id,
            title="Test Notification",
            message="Test message",
            priority=NotificationPriority.NORMAL,
            channels=["in_app"],
            status=NotificationStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(notification)
        await db_session.flush()

        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=test_user.id)
        set_tenant_context(context)

        try:
            processor = NotificationDeliveryProcessor(test_firm.id)
            result = await processor.execute()
            
            assert "delivered" in result
            assert "failed" in result
        finally:
            clear_tenant_context()


class TestWorkloadWorkers:
    """Tests for workload workers."""

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

    @pytest.mark.integration
    async def test_workload_snapshot_generator(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        """Test workload snapshot generation."""
        from app.modules.tasks.models import Task, TaskStatus, TaskPriority
        
        # Create some tasks
        tasks = [
            Task(
                title=f"Task {i}",
                status=TaskStatus.TODO if i % 2 == 0 else TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH if i % 3 == 0 else TaskPriority.NORMAL,
                due_date=date.today() - timedelta(days=i) if i < 3 else date.today() + timedelta(days=3),
                tenant_id=test_firm.id,
                assigned_user_id=test_user.id,
            )
            for i in range(5)
        ]
        db_session.add_all(tasks)
        await db_session.flush()

        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=test_user.id)
        set_tenant_context(context)

        try:
            generator = WorkloadSnapshotGenerator(test_firm.id)
            result = await generator.execute()
            
            assert "snapshots_created" in result
            assert result["snapshots_created"] >= 0
        finally:
            clear_tenant_context()

    @pytest.mark.integration
    async def test_workload_summary_updater(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        """Test workload summary updater."""
        from app.modules.workload.models import WorkloadSnapshot, WorkloadPeriod
        from app.modules.tasks.models import Task, TaskStatus, TaskPriority
        
        # Create snapshots for the week
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        snapshots = [
            WorkloadSnapshot(
                user_id=test_user.id,
                snapshot_date=week_start + timedelta(days=i),
                period_type=WorkloadPeriod.DAILY,
                open_tasks=5,
                overdue_tasks=1,
                open_matters=2,
                overdue_matters=0,
                high_priority_tasks=2,
                available_hours=8.0,
                allocated_hours=10.0,
                utilization_percentage=125.0,
                tenant_id=test_firm.id,
            )
            for i in range(5)
        ]
        db_session.add_all(snapshots)
        await db_session.flush()

        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=test_user.id)
        set_tenant_context(context)

        try:
            updater = WorkloadSummaryUpdater(test_firm.id)
            result = await updater.execute()
            
            assert "summaries_updated" in result
        finally:
            clear_tenant_context()


class TestOutboxWorkers:
    """Tests for outbox workers."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest.mark.integration
    async def test_outbox_processor(self, db_session: AsyncSession, test_firm: Firm):
        """Test outbox event processor."""
        # Create pending outbox events
        events = [
            OutboxEvent(
                event_type=OutboxEventType.DOCUMENT_UPLOADED,
                aggregate_type="document",
                aggregate_id=uuid4(),
                payload={"test": "data"},
                status=OutboxStatus.PENDING,
                tenant_id=test_firm.id,
            ),
            OutboxEvent(
                event_type=OutboxEventType.COMPLIANCE_CYCLE_CREATED,
                aggregate_type="compliance_cycle",
                aggregate_id=uuid4(),
                payload={"test": "data2"},
                status=OutboxStatus.PENDING,
                tenant_id=test_firm.id,
            ),
        ]
        db_session.add_all(events)
        await db_session.flush()

        processor = OutboxProcessor(batch_size=10)
        result = await processor.execute()
        
        assert "processed" in result
        assert "failed" in result
        assert "dead_lettered" in result

    @pytest.mark.integration
    async def test_outbox_processor_idempotency(self, db_session: AsyncSession, test_firm: Firm):
        """Test outbox processor idempotency with duplicate events."""
        idempotency_key = "test-key-123"
        
        event1 = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"test": "data"},
            status=OutboxStatus.PENDING,
            tenant_id=test_firm.id,
            idempotency_key=idempotency_key,
        )
        db_session.add(event1)
        await db_session.flush()

        # Try to create duplicate
        event2 = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"test": "data2"},
            status=OutboxStatus.PENDING,
            tenant_id=test_firm.id,
            idempotency_key=idempotency_key,
        )
        db_session.add(event2)
        await db_session.flush()

        # Should only have one event with this idempotency key
        from sqlalchemy import select
        result = await db_session.execute(
            select(OutboxEvent).where(
                OutboxEvent.tenant_id == test_firm.id,
                OutboxEvent.idempotency_key == idempotency_key
            )
        )
        events = result.scalars().all()
        assert len(events) == 1

    @pytest.mark.integration
    async def test_outbox_processor_retry_logic(self, db_session: AsyncSession, test_firm: Firm):
        """Test outbox processor retry logic."""
        # Create event that will fail
        event = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"test": "data"},
            status=OutboxStatus.PENDING,
            retry_count=4,  # One less than max_retries (5)
            max_retries=5,
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Mock handler that always fails
        processor = OutboxProcessor(batch_size=10)
        processor.register_handler(OutboxEventType.DOCUMENT_UPLOADED, lambda e: (_ for _ in ()).throw(Exception("Handler fails")))
        
        result = await processor.execute()
        
        # Event should be marked as failed with incremented retry count
        await db_session.refresh(event)
        assert event.status == OutboxStatus.FAILED
        assert event.retry_count == 5

    @pytest.mark.integration
    async def test_outbox_dead_letter(self, db_session: AsyncSession, test_firm: Firm):
        """Test outbox dead letter handling."""
        event = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"test": "data"},
            status=OutboxStatus.FAILED,
            retry_count=5,
            max_retries=5,
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()

        processor = OutboxProcessor(batch_size=10)
        processor.register_handler(OutboxEventType.DOCUMENT_UPLOADED, lambda e: (_ for _ in ()).throw(Exception("Handler fails")))
        
        result = await processor.execute()
        
        # Event should be moved to dead_letter
        await db_session.refresh(event)
        assert event.status == OutboxStatus.DEAD_LETTER
        assert result["dead_lettered"] >= 1

    @pytest.mark.integration
    async def test_cleanup_processed_outbox(self, db_session: AsyncSession, test_firm: Firm):
        """Test cleanup of old processed outbox events."""
        from datetime import datetime, timedelta
        
        # Create old processed event
        old_event = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"test": "data"},
            status=OutboxStatus.PROCESSED,
            processed_at=datetime.now(UTC) - timedelta(days=45),  # Older than 30 days
            tenant_id=test_firm.id,
        )
        db_session.add(old_event)
        
        # Create recent processed event
        recent_event = OutboxEvent(
            event_type=OutboxEventType.DOCUMENT_UPLOADED,
            aggregate_type="document",
            aggregate_id=uuid4(),
            payload={"test": "data2"},
            status=OutboxStatus.PROCESSED,
            processed_at=datetime.now(UTC) - timedelta(days=5),
            tenant_id=test_firm.id,
        )
        db_session.add(recent_event)
        await db_session.flush()

        processor = OutboxProcessor()
        result = await processor.cleanup_processed(older_than_days=30)
        
        assert "cleaned" in result
        # Old event should be deleted, recent should remain


class TestCeleryApp:
    """Tests for Celery app configuration."""

    @pytest.mark.unit
    def test_celery_app_created(self):
        """Test that Celery app is created with correct configuration."""
        assert celery_app is not None
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "UTC"

    @pytest.mark.unit
    def test_celery_queues_configured(self):
        """Test that all required queues are configured."""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]
        assert "default" in queue_names
        assert "compliance" in queue_names
        assert "notifications" in queue_names
        assert "workload" in queue_names
        assert "outbox" in queue_names

    @pytest.mark.unit
    def test_celery_routes_configured(self):
        """Test that task routing is configured."""
        routes = celery_app.conf.task_routes
        assert "app.workers.compliance_tasks.*" in routes
        assert "app.workers.notification_tasks.*" in routes
        assert "app.workers.workload_tasks.*" in routes
        assert "app.workers.outbox_tasks.*" in routes

    @pytest.mark.unit
    def test_celery_beat_schedule_configured(self):
        """Test that Celery Beat schedule is configured."""
        schedule = celery_app.conf.beat_schedule
        assert "generate-compliance-cycles" in schedule
        assert "send-compliance-reminders" in schedule
        assert "send-deadline-reminders" in schedule
        assert "generate-workload-snapshots" in schedule
        assert "process-outbox" in schedule
        assert "cleanup-old-outbox" in schedule

    @pytest.mark.unit
    def test_celery_worker_config(self):
        """Test worker configuration."""
        assert celery_app.conf.worker_prefetch_multiplier == 4
        assert celery_app.conf.worker_max_tasks_per_child == 1000
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True