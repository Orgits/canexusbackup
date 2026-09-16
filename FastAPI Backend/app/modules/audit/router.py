from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy.dependencies import get_current_tenant
from app.modules.audit.schemas import AuditLogListResponse, AuditLogResponse
from app.modules.audit.service import AuditService
from app.modules.users.models import User

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    user_id: UUID = None,
    action: str = None,
    resource_type: str = None,
    resource_id: UUID = None,
    start_from: datetime = None,
    start_to: datetime = None,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
):
    service = AuditService(db)
    items, total = await service.get_all(
        current_tenant.id, page, page_size, user_id, action,
        resource_type, resource_id, start_from, start_to
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
):
    service = AuditService(db)
    audit_log = await service.get_by_id(log_id, current_tenant.id)
    return AuditLogResponse.model_validate(audit_log)
