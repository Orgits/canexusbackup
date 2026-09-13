from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog, AuditAction
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.repository import AuditRepository


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditRepository(db)

    async def log(
        self,
        tenant_id: UUID,
        action: AuditAction,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        changed_fields: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        start_from: Optional[datetime] = None,
        start_to: Optional[datetime] = None,
    ) -> Tuple[List[AuditLog], int]:
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
        new_values: Dict[str, Any],
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
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
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        changed_fields: List[str],
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
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
        old_values: Dict[str, Any],
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
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
        old_roles: List[str],
        new_roles: List[str],
        old_permissions: List[str],
        new_permissions: List[str],
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
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