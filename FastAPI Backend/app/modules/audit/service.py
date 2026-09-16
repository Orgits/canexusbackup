from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditAction, AuditLog
from app.modules.audit.repository import AuditRepository


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditRepository(db)

    async def log(
        self,
        tenant_id: UUID,
        action: AuditAction,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        changed_fields: list[str] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values or {},
            new_values=new_values or {},
            changed_fields=changed_fields or [],
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata=metadata or {},
        )
        return await self.repository.create(audit_log)

    async def get_by_id(self, log_id: UUID, tenant_id: UUID) -> AuditLog:
        audit_log = await self.repository.get_by_id(log_id, tenant_id)
        if not audit_log:
            from app.core.exceptions import NotFoundException
            raise NotFoundException(detail="Audit log not found")
        return audit_log

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        user_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        start_from: datetime | None = None,
        start_to: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, user_id, action,
            resource_type, resource_id, start_from, start_to
        )

    async def log_login(self, tenant_id: UUID, user_id: UUID, ip_address: str, user_agent: str, request_id: str) -> AuditLog:
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.LOGIN,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def log_logout(self, tenant_id: UUID, user_id: UUID, ip_address: str, request_id: str) -> AuditLog:
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_create(
        self,
        tenant_id: UUID,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        new_values: dict[str, Any],
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.CREATE,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            new_values=new_values,
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_update(
        self,
        tenant_id: UUID,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
        changed_fields: list[str],
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.UPDATE,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_delete(
        self,
        tenant_id: UUID,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        old_values: dict[str, Any],
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.DELETE,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_permission_change(
        self,
        tenant_id: UUID,
        user_id: UUID,
        target_user_id: UUID,
        old_roles: list[str],
        new_roles: list[str],
        old_permissions: list[str],
        new_permissions: list[str],
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.PERMISSION_CHANGE,
            user_id=user_id,
            resource_type="user",
            resource_id=target_user_id,
            old_values={"roles": old_roles, "permissions": old_permissions},
            new_values={"roles": new_roles, "permissions": new_permissions},
            changed_fields=["roles", "permissions"],
            ip_address=ip_address,
            request_id=request_id,
        )
