# CRUD Integration Tests for Representative Modules

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client, ClientContact, ClientService
from app.modules.matters.models import Matter, MatterType, MatterStatus, MatterPriority
from app.modules.tasks.models import Task, TaskStatus, TaskPriority
from app.modules.compliance.models import ComplianceType, ComplianceCycle, ComplianceStatus, ComplianceFrequency
from app.modules.documents.models import Document, DocumentStatus, DocumentCategory
from app.modules.billing.models import Invoice, InvoiceItem, Payment, Expense
from app.modules.calendar.models import CalendarEvent, CalendarEventType
from app.modules.communications.models import Communication, CommunicationChannel, CommunicationDirection, CommunicationStatus
from app.modules.workflow.models import WorkflowDefinition, WorkflowInstance, WorkflowEntityType, WorkflowTransitionHistory
from app.modules.notifications.models import Notification, NotificationTemplate, NotificationTrigger, NotificationChannel, NotificationStatus, NotificationPriority
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestFirmCRUD:
    """Tests for Firm CRUD operations."""

    @pytest.mark.integration
    async def test_create_firm(self, db_session: AsyncSession):
        firm = Firm(
            name="Test Firm",
            display_name="Test Firm",
            registration_number="REG123",
            is_active=True,
            settings={"key": "value"},
            country="India",
        )
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)

        assert firm.id is not None
        assert firm.name == "Test Firm"
        assert firm.settings == {"key": "value"}

    @pytest.mark.integration
    async def test_update_firm(self, db_session: AsyncSession):
        firm = Firm(name="Original", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()

        firm.name = "Updated"
        firm.settings = {"updated": True}
        await db_session.flush()
        await db_session.refresh(firm)

        assert firm.name == "Updated"
        assert firm.settings == {"updated": True}

    @pytest.mark.integration
    async def test_delete_firm(self, db_session: AsyncSession):
        firm = Firm(name="To Delete", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        firm_id = firm.id

        await db_session.delete(firm)
        await db_session.flush()

        result = await db_session.execute(select(Firm).where(Firm.id == firm_id))
        assert result.scalar_one_or_none() is None


class TestUserCRUD:
    """Tests for User CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest.mark.integration
    async def test_create_user(self, db_session: AsyncSession, test_firm: Firm):
        from app.core.security import hash_password
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

        assert user.id is not None
        assert user.email == "user@example.com"

    @pytest.mark.integration
    async def test_user_roles(self, db_session: AsyncSession, test_firm: Firm):
        from app.core.security import hash_password
        user = User(
            email="admin@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Admin User",
            tenant_id=test_firm.id,
            roles=["firm_admin"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        permissions = user.get_all_permissions()
        assert "admin.users.manage" in permissions


class TestClientCRUD:
    """Tests for Client CRUD operations."""

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
            hashed_password="hashed",
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
    async def test_create_client(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        client = Client(
            name="Test Client",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=test_firm.id,
            responsible_user_id=test_user.id,
        )
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)

        assert client.id is not None
        assert client.name == "Test Client"
        assert client.tenant_id == test_firm.id

    @pytest.mark.integration
    async def test_create_client_with_contact(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        client = Client(
            name="Client with Contact",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=test_firm.id,
            responsible_user_id=test_user.id,
        )
        db_session.add(client)
        await db_session.flush()

        contact = ClientContact(
            client_id=client.id,
            name="John Doe",
            emails=["john@example.com"],
            phones=["+1234567890"],
            is_primary=True,
            tenant_id=test_firm.id,
        )
        db_session.add(contact)
        await db_session.flush()
        await db_session.refresh(contact)

        assert contact.id is not None
        assert contact.client_id == client.id

    @pytest.mark.integration
    async def test_create_client_with_service(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        client = Client(
            name="Client with Service",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=test_firm.id,
        )
        db_session.add(client)
        await db_session.flush()

        service = ClientService(
            client_id=client.id,
            service_type="TAX",
            billing_frequency="MONTHLY",
            responsible_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(service)
        await db_session.flush()
        await db_session.refresh(service)

        assert service.id is not None
        assert service.client_id == client.id


class TestMatterCRUD:
    """Tests for Matter CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def test_client(self, db_session: AsyncSession, test_firm: Firm, test_user: User) -> User:
        client = Client(name="Test Client", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=test_user.id)
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)
        return client

    @pytest.mark.integration
    async def test_create_matter(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
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

        assert matter.id is not None
        assert matter.matter_type == MatterType.TAX
        assert matter.status == MatterStatus.IN_PROGRESS

    @pytest.mark.integration
    async def test_matter_status_transitions(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
        matter = Matter(
            name="Matter for Transitions",
            matter_type=MatterType.TAX,
            status=MatterStatus.CREATED,
            client_id=test_client.id,
            responsible_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(matter)
        await db_session.flush()

        # Test valid transitions
        matter.status = MatterStatus.IN_PROGRESS
        await db_session.flush()
        assert matter.status == MatterStatus.IN_PROGRESS


class TestTaskCRUD:
    """Tests for Task CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def test_client(self, db_session: AsyncSession, test_firm: Firm, test_user: User) -> User:
        client = Client(name="Test Client", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=test_user.id)
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)
        return client

    @pytest_asyncio.fixture
    async def test_matter(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User) -> User:
        matter = Matter(name="Test Matter", matter_type="TAX", status="IN_PROGRESS", client_id=test_client.id, responsible_user_id=test_user.id, tenant_id=test_firm.id)
        db_session.add(matter)
        await db_session.flush()
        await db_session.refresh(matter)
        return matter

    @pytest.mark.integration
    async def test_create_task(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User, test_matter: User):
        task = Task(
            title="Test Task",
            description="Task description",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            client_id=test_client.id,
            matter_id=test_matter.id,
            assigned_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(task)
        await db_session.flush()
        await db_session.refresh(task)

        assert task.id is not None
        assert task.title == "Test Task"
        assert task.status == TaskStatus.TODO

    @pytest.mark.integration
    async def test_task_subtasks(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
        parent_task = Task(
            title="Parent Task",
            status=TaskStatus.TODO,
            client_id=test_client.id,
            assigned_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(parent_task)
        await db_session.flush()

        subtask = Task(
            title="Subtask",
            status=TaskStatus.TODO,
            client_id=test_client.id,
            parent_task_id=parent_task.id,
            assigned_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(subtask)
        await db_session.flush()

        assert subtask.parent_task_id == parent_task.id


class TestComplianceCRUD:
    """Tests for Compliance CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.mark.integration
    async def test_create_compliance_type(self, db_session: AsyncSession, test_firm: Firm):
        ctype = ComplianceType(
            code="TEST",
            name="Test Compliance",
            category="TAX",
            frequency=ComplianceFrequency.ANNUAL,
            due_date=date(2026, 3, 31),
            tenant_id=test_firm.id,
        )
        db_session.add(ctype)
        await db_session.flush()
        await db_session.refresh(ctype)

        assert ctype.id is not None
        assert ctype.code == "TEST"

    @pytest.mark.integration
    async def test_create_compliance_cycle(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        ctype = ComplianceType(
            code="ITR",
            name="Income Tax Return",
            category="TAX",
            frequency=ComplianceFrequency.ANNUAL,
            due_date=date(2026, 7, 31),
            tenant_id=test_firm.id,
        )
        db_session.add(ctype)
        await db_session.flush()

        cycle = ComplianceCycle(
            compliance_type_id=ctype.id,
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            due_date=date(2026, 7, 31),
            status=ComplianceStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(cycle)
        await db_session.flush()
        await db_session.refresh(cycle)

        assert cycle.id is not None
        assert cycle.status == ComplianceStatus.PENDING


class TestDocumentCRUD:
    """Tests for Document CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def test_client(self, db_session: AsyncSession, test_firm: Firm, test_user: User) -> User:
        client = Client(name="Test Client", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=test_user.id)
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)
        return client

    @pytest.mark.integration
    async def test_create_document(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
        doc = Document(
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension="pdf",
            mime_type="application/pdf",
            file_size=1024,
            storage_path="path/to/test.pdf",
            storage_key="key123",
            category=DocumentCategory.TAX,
            status=DocumentStatus.UPLOADED,
            client_id=test_client.id,
            uploaded_by=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(doc)
        await db_session.flush()
        await db_session.refresh(doc)

        assert doc.id is not None
        assert doc.filename == "test.pdf"
        assert doc.status == DocumentStatus.UPLOADED

    @pytest.mark.integration
    async def test_document_versioning(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
        doc_v1 = Document(
            filename="doc_v1.pdf",
            original_filename="doc_v1.pdf",
            file_extension="pdf",
            mime_type="application/pdf",
            file_size=1024,
            storage_path="path/v1.pdf",
            storage_key="key1",
            category=DocumentCategory.TAX,
            status=DocumentStatus.PROCESSED,
            client_id=test_client.id,
            uploaded_by=test_user.id,
            tenant_id=test_firm.id,
            version=1,
            is_latest_version=True,
        )
        db_session.add(doc_v1)
        await db_session.flush()

        # Create version 2
        doc_v1.is_latest_version = False
        doc_v2 = Document(
            filename="doc_v2.pdf",
            original_filename="doc_v2.pdf",
            file_extension="pdf",
            mime_type="application/pdf",
            file_size=2048,
            storage_path="path/v2.pdf",
            storage_key="key2",
            category=DocumentCategory.TAX,
            status=DocumentStatus.UPLOADED,
            client_id=test_client.id,
            uploaded_by=test_user.id,
            tenant_id=test_firm.id,
            version=2,
            is_latest_version=True,
            previous_version_id=doc_v1.id,
        )
        db_session.add(doc_v2)
        await db_session.flush()

        assert doc_v2.version == 2
        assert doc_v2.previous_version_id == doc_v1.id
        assert doc_v1.is_latest_version is False
        assert doc_v2.is_latest_version is True


class TestBillingCRUD:
    """Tests for Billing CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def test_client(self, db_session: AsyncSession, test_firm: Firm, test_user: User) -> User:
        client = Client(name="Test Client", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=test_user.id)
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)
        return client

    @pytest.mark.integration
    async def test_create_invoice(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
        invoice = Invoice(
            invoice_number="INV-001",
            client_id=test_client.id,
            invoice_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("1800.00"),
            total_amount=Decimal("11800.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("11800.00"),
            status="DRAFT",
            tenant_id=test_firm.id,
        )
        db_session.add(invoice)
        await db_session.flush()
        await db_session.refresh(invoice)

        assert invoice.id is not None
        assert invoice.invoice_number == "INV-001"

    @pytest.mark.integration
    async def test_create_invoice_item(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
        invoice = Invoice(
            invoice_number="INV-001",
            client_id=test_client.id,
            invoice_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("1800.00"),
            total_amount=Decimal("11800.00"),
            balance_amount=Decimal("11800.00"),
            status="DRAFT",
            tenant_id=test_firm.id,
        )
        db_session.add(invoice)
        await db_session.flush()

        item = InvoiceItem(
            invoice_id=invoice.id,
            description="Tax Consulting",
            quantity=Decimal("10"),
            unit_price=Decimal("1000.00"),
            tax_rate=Decimal("18.00"),
            total=Decimal("11800.00"),
            tenant_id=test_firm.id,
        )
        db_session.add(item)
        await db_session.flush()
        await db_session.refresh(item)

        assert item.id is not None
        assert item.invoice_id == invoice.id

    @pytest.mark.integration
    async def test_create_payment(self, db_session: AsyncSession, test_firm: Firm, test_client: User, test_user: User):
        invoice = Invoice(
            invoice_number="INV-001",
            client_id=test_client.id,
            invoice_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("1800.00"),
            total_amount=Decimal("11800.00"),
            balance_amount=Decimal("11800.00"),
            status="SENT",
            tenant_id=test_firm.id,
        )
        db_session.add(invoice)
        await db_session.flush()

        payment = Payment(
            payment_number="PAY-001",
            invoice_id=invoice.id,
            client_id=test_client.id,
            payment_date=date(2026, 1, 15),
            amount=Decimal("11800.00"),
            status="COMPLETED",
            tenant_id=test_firm.id,
        )
        db_session.add(payment)
        await db_session.flush()
        await db_session.refresh(payment)

        assert payment.id is not None
        assert payment.amount == Decimal("11800.00")


class TestCalendarCRUD:
    """Tests for Calendar CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.mark.integration
    async def test_create_calendar_event(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        event = CalendarEvent(
            title="Client Meeting",
            event_type=CalendarEventType.CLIENT_MEETING,
            start_at=datetime(2026, 1, 15, 10, 0),
            end_at=datetime(2026, 1, 15, 11, 0),
            tenant_id=test_firm.id,
        )
        db_session.add(event)
        await db_session.flush()
        await db_session.refresh(event)

        assert event.id is not None
        assert event.title == "Client Meeting"
        assert event.event_type == CalendarEventType.CLIENT_MEETING


class TestCommunicationCRUD:
    """Tests for Communication CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.mark.integration
    async def test_create_communication(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        comm = Communication(
            subject="Test Email",
            body="Email body",
            channel=CommunicationChannel.EMAIL,
            direction=CommunicationDirection.OUTBOUND,
            status=CommunicationStatus.SENT,
            sender_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(comm)
        await db_session.flush()
        await db_session.refresh(comm)

        assert comm.id is not None
        assert comm.subject == "Test Email"
        assert comm.channel == CommunicationChannel.EMAIL


class TestWorkflowCRUD:
    """Tests for Workflow CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest.mark.integration
    async def test_create_workflow_definition(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        from app.modules.workflow.schemas import WorkflowStateBase, WorkflowTransitionBase

        definition = WorkflowDefinition(
            code="TEST_WF",
            name="Test Workflow",
            entity_type=WorkflowEntityType.MATTER,
            initial_state="draft",
            states=[
                WorkflowStateBase(code="draft", name="Draft", is_initial=True, order=1),
                WorkflowStateBase(code="approved", name="Approved", is_terminal=True, order=2),
            ],
            transitions=[
                WorkflowTransitionBase(
                    code="approve",
                    name="Approve",
                    from_state="draft",
                    to_state="approved",
                ),
            ],
            is_active=True,
            tenant_id=test_firm.id,
        )
        db_session.add(definition)
        await db_session.flush()
        await db_session.refresh(definition)

        assert definition.id is not None
        assert definition.code == "TEST_WF"

    @pytest.mark.integration
    async def test_create_workflow_instance(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        from app.modules.workflow.schemas import WorkflowStateBase, WorkflowTransitionBase

        definition = WorkflowDefinition(
            code="TEST_WF_2",
            name="Test Workflow 2",
            entity_type=WorkflowEntityType.MATTER,
            initial_state="draft",
            states=[
                WorkflowStateBase(code="draft", name="Draft", is_initial=True, order=1),
                WorkflowStateBase(code="approved", name="Approved", is_terminal=True, order=2),
            ],
            transitions=[
                WorkflowTransitionBase(code="approve", from_state="draft", to_state="approved"),
            ],
            tenant_id=test_firm.id,
        )
        db_session.add(definition)
        await db_session.flush()

        instance = WorkflowInstance(
            workflow_definition_id=definition.id,
            entity_type="matter",
            entity_id=uuid4(),
            current_state="draft",
            tenant_id=test_firm.id,
        )
        db_session.add(instance)
        await db_session.flush()
        await db_session.refresh(instance)

        assert instance.id is not None
        assert instance.current_state == "draft"


class TestNotificationCRUD:
    """Tests for Notification CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(email="user@example.com", hashed_password="hashed", full_name="Test User", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.mark.integration
    async def test_create_notification_template(self, db_session: AsyncSession, test_firm: Firm):
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

        assert template.id is not None
        assert template.code == "TEST_TEMPLATE"

    @pytest.mark.integration
    async def test_create_notification(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        notification = Notification(
            recipient_id=test_user.id,
            trigger=NotificationTrigger.ASSIGNMENT,
            title="New Task Assigned",
            message="You have been assigned a new task",
            priority=NotificationPriority.NORMAL,
            channels=["in_app"],
            status=NotificationStatus.PENDING,
            tenant_id=test_firm.id,
        )
        db_session.add(notification)
        await db_session.flush()
        await db_session.refresh(notification)

        assert notification.id is not None
        assert notification.title == "New Task Assigned"
        assert notification.status == NotificationStatus.PENDING