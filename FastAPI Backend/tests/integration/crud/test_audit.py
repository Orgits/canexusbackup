# Audit CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.audit.models import AuditLog, AuditAction
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestAuditCRUD:
    """Tests for AuditLog CRUD operations."""

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
    async def test_create_audit_log(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        audit_log = AuditLog(
            user_id=test_user.id,
            action=AuditAction.CREATE,
            resource_type="client",
            resource_id=uuid4(),
            old_values=None,
            new_values={"name": "Test Client", "category": "COMPANY"},
            changed_fields=["name", "category"],
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            request_id="req-123",
            tenant_id=test_firm.id,
        )
        db_session.add(audit_log)
        await db_session.flush()
        await db_session.refresh(audit_log)

        assert audit_log.id is not None
        assert audit_log.action == AuditAction.CREATE
        assert audit_log.resource_type == "client"
        assert audit_log.new_values["name"] == "Test Client"

    @pytest.mark.integration
    async def test_audit_log_with_old_and_new_values(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        audit_log = AuditLog(
            user_id=test_user.id,
            action=AuditAction.UPDATE,
            resource_type="matter",
            resource_id=uuid4(),
            old_values={"status": "CREATED", "priority": "LOW"},
            new_values={"status": "IN_PROGRESS", "priority": "HIGH"},
            changed_fields=["status", "priority"],
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            request_id="req-456",
            tenant_id=test_firm.id,
        )
        db_session.add(audit_log)
        await db_session.flush()
        await db_session.refresh(audit_log)

        assert audit_log.old_values["status"] == "CREATED"
        assert audit_log.new_values["status"] == "IN_PROGRESS"
        assert "status" in audit_log.changed_fields
        assert "priority" in audit_log.changed_fields

    @pytest.mark.integration
    async def test_audit_log_login_action(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        audit_log = AuditLog(
            user_id=test_user.id,
            action=AuditAction.LOGIN,
            resource_type="user",
            resource_id=test_user.id,
            old_values=None,
            new_values={"ip": "192.168.1.1", "user_agent": "Test Agent"},
            changed_fields=[],
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            request_id="req-login",
            tenant_id=test_firm.id,
        )
        db_session.add(audit_log)
        await db_session.flush()

        assert audit_log.action == AuditAction.LOGIN
        assert audit_log.resource_type == "user"

    @pytest.mark.integration
    async def test_audit_log_permission_change(self, db_session: AsyncSession, test_firm: Firm, test_user: User):
        audit_log = AuditLog(
            user_id=test_user.id,
            action=AuditAction.PERMISSION_CHANGE,
            resource_type="user",
            resource_id=test_user.id,
            old_values={"roles": ["associate"]},
            new_values={"roles": ["associate", "firm_admin"]},
            changed_fields=["roles"],
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            request_id="req-perm",
            tenant_id=test_firm.id,
        )
        db_session.add(audit_log)
        await db_session.flush()

        assert audit_log.action == AuditAction.PERMISSION_CHANGE
        assert audit_log.old_values["roles"] == ["associate"]
        assert audit_log.new_values["roles"] == ["associate", "firm_admin"]


class TestAuditTenantIsolation:
    """Tests for AuditLog tenant isolation."""

    @pytest.mark.integration
    async def test_audit_tenant_isolation(
        self, db_session: AsyncSession, test_firm: Firm
    ):
        """Test that audit logs are isolated by tenant."""
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

        # Create audit logs for each tenant
        audit_a = AuditLog(
            user_id=user_a.id,
            action=AuditAction.CREATE,
            resource_type="client",
            resource_id=uuid4(),
            new_values={"name": "Client A"},
            tenant_id=test_firm.id,
        )
        audit_b = AuditLog(
            user_id=user_b.id,
            action=AuditAction.CREATE,
            resource_type="client",
            resource_id=uuid4(),
            new_values={"name": "Client B"},
            tenant_id=other_firm.id,
        )
        db_session.add_all([audit_a, audit_b])
        await db_session.flush()

        # Set tenant context to Firm A
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(AuditLog))
        audits = result.scalars().all()
        assert len(audits) == 1
        assert audits[0].id == audit_a.id

        clear_tenant_context()

        # Set tenant context to Firm B
        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(AuditLog))
        audits = result.scalars().all()
        assert len(audits) == 1
        assert audits[0].id == audit_b.id

        clear_tenant_context()