# Authorization Tests

import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.calendar.models import CalendarEvent, EventType
from app.modules.communications.models import Communication, CommunicationChannel, CommunicationDirection, CommunicationStatus
from app.modules.workflow.models import WorkflowDefinition, WorkflowInstance, WorkflowEntityType
from app.core.security import hash_password
from app.core.permissions.registry import Permission


class TestAuthorization:
    """Tests for authorization across modules."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def admin_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(
            email="admin@example.com",
            hashed_password="hashed",
            full_name="Admin User",
            tenant_id=test_firm.id,
            roles=["firm_admin"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def associate_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(
            email="associate@example.com",
            hashed_password="hashed",
            full_name="Associate User",
            tenant_id=test_firm.id,
            roles=["associate"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def viewer_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(
            email="viewer@example.com",
            hashed_password="hashed",
            full_name="Viewer User",
            tenant_id=test_firm.id,
            roles=["junior_associate"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def auth_headers(self, async_client: AsyncClient, email: str, password: str) -> dict:
        response = await async_client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass123!"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    @pytest_asyncio.fixture
    async def admin_headers(self, async_client: AsyncClient, admin_user: User) -> dict:
        return await self.auth_headers(async_client, "admin@example.com", "TestPass123!")

    @pytest_asyncio.fixture
    async def associate_headers(self, async_client: AsyncClient, associate_user: User) -> dict:
        return await self.auth_headers(async_client, "associate@example.com", "TestPass123!")

    @pytest_asyncio.fixture
    async def viewer_headers(self, async_client: AsyncClient, viewer_user: User) -> dict:
        return await self.auth_headers(async_client, "viewer@example.com", "TestPass123!")

    @pytest_asyncio.fixture
    async def test_client(self, db_session: AsyncSession, test_firm: Firm, admin_user: User) -> User:
        client = Client(
            name="Test Client",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=test_firm.id,
            responsible_user_id=admin_user.id,
        )
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)
        return client

    # Calendar Authorization Tests
    @pytest.mark.integration
    async def test_calendar_create_permitted(self, async_client: AsyncClient, admin_headers: dict):
        """Test that admin can create calendar events."""
        response = await async_client.post(
            "/api/calendar",
            json={
                "title": "Meeting",
                "event_type": "client_meeting",
                "start_at": "2026-01-15T10:00:00",
                "end_at": "2026-01-15T11:00:00",
            },
            headers=admin_headers
        )
        assert response.status_code == 201

    @pytest.mark.integration
    async def test_calendar_create_denied_for_viewer(self, async_client: AsyncClient, viewer_headers: dict):
        """Test that viewer cannot create calendar events."""
        response = await async_client.post(
            "/api/calendar",
            json={
                "title": "Meeting",
                "event_type": "client_meeting",
                "start_at": "2026-01-15T10:00:00",
                "end_at": "2026-01-15T11:00:00",
            },
            headers=viewer_headers
        )
        assert response.status_code == 403

    @pytest.mark.integration
    async def test_calendar_read_permitted_for_associate(self, async_client: AsyncClient, associate_headers: dict):
        """Test that associate can read calendar events."""
        response = await async_client.get("/api/calendar", headers=associate_headers)
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_calendar_read_denied_without_permission(self, async_client: AsyncClient):
        """Test that unauthenticated user cannot read calendar."""
        response = await async_client.get("/api/calendar")
        assert response.status_code == 401

    # Communications Authorization Tests
    @pytest.mark.integration
    async def test_communications_create_permitted(self, async_client: AsyncClient, admin_headers: dict):
        """Test that admin can create communications."""
        response = await async_client.post(
            "/api/communications",
            json={
                "subject": "Test Email",
                "body": "Email body",
                "channel": "email",
                "direction": "outbound",
            },
            headers=admin_headers
        )
        assert response.status_code == 201

    @pytest.mark.integration
    async def test_communications_send_permitted(self, async_client: AsyncClient, admin_headers: dict, test_client):
        """Test that admin can send communications."""
        # First create a communication
        create_response = await async_client.post(
            "/api/communications",
            json={
                "subject": "Test Email",
                "body": "Email body",
                "channel": "email",
                "direction": "outbound",
            },
            headers=admin_headers
        )
        comm_id = create_response.json()["id"]

        # Send it
        response = await async_client.post(
            f"/api/communications/{comm_id}/send",
            headers=admin_headers
        )
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_communications_send_denied_for_associate(self, async_client: AsyncClient, associate_headers: dict, test_client):
        """Test that associate cannot send communications."""
        # First create a communication as admin
        admin_response = await async_client.post(
            "/api/communications",
            json={
                "subject": "Test Email",
                "body": "Email body",
                "channel": "email",
                "direction": "outbound",
            },
            headers=admin_headers
        )
        comm_id = admin_response.json()["id"]

        # Try to send as associate
        response = await async_client.post(
            f"/api/communications/{comm_id}/send",
            headers=associate_headers
        )
        assert response.status_code == 403

    # Workflow Transition Authorization Tests
    @pytest.mark.integration
    async def test_workflow_transition_permitted_with_permission(
        self, async_client: AsyncClient, admin_headers: dict, test_firm
    ):
        """Test that user with workflow.transition permission can execute transitions."""
        from app.modules.workflow.schemas import WorkflowStateBase, WorkflowTransitionBase

        # Create workflow definition with transition requiring permission
        definition = WorkflowDefinition(
            code="PERM_TEST",
            name="Permission Test Workflow",
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
                    required_permissions=["workflow.transition"],
                ),
            ],
            is_active=True,
        )
        from app.modules.workflow.models import WorkflowDefinition
        db_session.add(definition)
        await db_session.flush()

        # Create instance
        instance = WorkflowInstance(
            workflow_definition_id=definition.id,
            entity_type="matter",
            entity_id=uuid4(),
            current_state="draft",
            tenant_id=test_firm.id,
        )
        db_session.add(instance)
        await db_session.flush()

        # Execute transition
        response = await async_client.post(
            f"/api/workflow/instances/{instance.id}/transition",
            json={"transition_code": "approve", "comment": "Approved"},
            headers=admin_headers
        )
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_workflow_transition_denied_without_permission(
        self, async_client: AsyncClient, associate_headers: dict, test_firm
    ):
        """Test that user without workflow.transition permission cannot execute transitions."""
        from app.modules.workflow.schemas import WorkflowStateBase, WorkflowTransitionBase

        definition = WorkflowDefinition(
            code="PERM_TEST_2",
            name="Permission Test Workflow 2",
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
                    required_permissions=["workflow.transition"],
                ),
            ],
            is_active=True,
        )
        from app.modules.workflow.models import WorkflowDefinition
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

        response = await async_client.post(
            f"/api/workflow/instances/{instance.id}/transition",
            json={"transition_code": "approve", "comment": "Approved"},
            headers=associate_headers
        )
        assert response.status_code == 403

    @pytest.mark.integration
    async def test_workflow_available_transitions_shows_permissions(
        self, async_client: AsyncClient, admin_headers: dict, associate_headers: dict, test_firm
    ):
        """Test that available-transitions endpoint shows missing permissions."""
        from app.modules.workflow.schemas import WorkflowStateBase, WorkflowTransitionBase

        definition = WorkflowDefinition(
            code="PERM_TEST_3",
            name="Permission Test Workflow 3",
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
                    required_permissions=["workflow.transition"],
                    required_roles=["firm_admin"],
                ),
            ],
            is_active=True,
        )
        from app.modules.workflow.models import WorkflowDefinition
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

        # Admin should see can_execute=true
        admin_response = await async_client.get(
            f"/api/workflow/instances/{instance.id}/available-transitions",
            headers=admin_headers
        )
        assert admin_response.status_code == 200
        admin_data = admin_response.json()
        assert len(admin_data) > 0
        assert admin_data[0]["can_execute"] is True

        # Associate should see can_execute=false with missing permissions/roles
        associate_response = await async_client.get(
            f"/api/workflow/instances/{instance.id}/available-transitions",
            headers=associate_headers
        )
        assert associate_response.status_code == 200
        associate_data = associate_response.json()
        assert len(associate_data) > 0
        assert associate_data[0]["can_execute"] is False
        assert "workflow.transition" in associate_data[0]["missing_permissions"]
        assert "firm_admin" in associate_data[0]["missing_roles"]

    # Cross-Tenant Access Tests
    @pytest.mark.integration
    async def test_cross_tenant_client_access_denied(
        self, async_client: AsyncClient, admin_headers: dict, db_session, test_firm
    ):
        """Test that users cannot access other tenants' data."""
        # Create another firm
        other_firm = Firm(name="Other Firm", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        # Create client in other firm
        other_client = Client(
            name="Other Client",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=other_firm.id,
        )
        db_session.add(other_client)
        await db_session.flush()

        # Try to access other firm's client
        response = await async_client.get(
            f"/api/clients/{other_client.id}",
            headers=admin_headers
        )
        assert response.status_code == 404  # Not found due to RLS

    @pytest.mark.integration
    async def test_cross_tenant_matter_access_denied(
        self, async_client: AsyncClient, admin_headers: dict, db_session, test_firm, admin_user
    ):
        """Test that users cannot access other tenants' matters."""
        other_firm = Firm(name="Other Firm 2", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        other_client = Client(
            name="Other Client",
            category="COMPANY",
            status="ACTIVE",
            tenant_id=other_firm.id,
            responsible_user_id=admin_user.id,
        )
        db_session.add(other_client)
        await db_session.flush()

        other_matter = Matter(
            name="Other Matter",
            matter_type="TAX",
            status="IN_PROGRESS",
            client_id=other_client.id,
            responsible_user_id=admin_user.id,
            tenant_id=other_firm.id,
        )
        db_session.add(other_matter)
        await db_session.flush()

        # Try to access other firm's matter
        response = await async_client.get(
            f"/api/matters/{other_matter.id}",
            headers=admin_headers
        )
        assert response.status_code == 404

    # Role-based Access Tests
    @pytest.mark.integration
    async def test_admin_can_manage_users(self, async_client: AsyncClient, admin_headers: dict):
        """Test that firm_admin can manage users."""
        response = await async_client.get("/api/users", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_associate_cannot_manage_users(self, async_client: AsyncClient, associate_headers: dict):
        """Test that associate cannot manage users."""
        response = await async_client.get("/api/users", headers=associate_headers)
        assert response.status_code == 403

    @pytest.mark.integration
    async def test_admin_can_manage_firm_settings(self, async_client: AsyncClient, admin_headers: dict):
        """Test that firm_admin can manage firm settings."""
        response = await async_client.get("/api/firms", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_associate_cannot_manage_firm_settings(self, async_client: AsyncClient, associate_headers: dict):
        """Test that associate cannot manage firm settings."""
        response = await async_client.get("/api/firms", headers=associate_headers)
        assert response.status_code == 403

    @pytest.mark.integration
    async def test_viewer_can_read_clients(self, async_client: AsyncClient, viewer_headers: dict):
        """Test that viewer can read clients."""
        response = await async_client.get("/api/clients", headers=viewer_headers)
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_viewer_cannot_create_clients(self, async_client: AsyncClient, viewer_headers: dict):
        """Test that viewer cannot create clients."""
        response = await async_client.post(
            "/api/clients",
            json={"name": "New Client", "category": "COMPANY", "status": "ACTIVE"},
            headers=viewer_headers
        )
        assert response.status_code == 403