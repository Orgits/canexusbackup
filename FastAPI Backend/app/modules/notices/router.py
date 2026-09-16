from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions.dependencies import require_permission
from app.core.security.dependencies import get_current_user
from app.core.tenancy import get_tenant_context
from app.modules.notices.schemas import (
    NoticeClosureUpdate,
    NoticeCreate,
    NoticeEscalationCreate,
    NoticeEscalationResponse,
    NoticeListResponse,
    NoticeResponse,
    NoticeResponseUpdate,
    NoticeStatusUpdate,
    NoticeSummaryResponse,
    NoticeUpdate,
)
from app.modules.notices.service import NoticeService
from app.modules.users.models import User

router = APIRouter(prefix="/notices", tags=["Notice Management"])


def get_notice_service(db: AsyncSession = Depends(get_db)) -> NoticeService:
    return NoticeService(db)


# Summary endpoint
@router.get(
    "/summary",
    response_model=NoticeSummaryResponse,
    summary="Get notice summary",
)
async def get_notice_summary(
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.read")),
):
    return await notice_service.get_summary(tenant_context.tenant_id)


# Notice endpoints
@router.post(
    "",
    response_model=NoticeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notice",
)
async def create_notice(
    data: NoticeCreate,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.create")),
):
    return await notice_service.create_notice(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "",
    response_model=NoticeListResponse,
    summary="List notices",
)
async def list_notices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    client_id: UUID | None = None,
    authority: str | None = None,
    notice_type: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: UUID | None = None,
    team_id: UUID | None = None,
    received_date_from: datetime | None = None,
    received_date_to: datetime | None = None,
    deadline_from: datetime | None = None,
    deadline_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.read")),
):
    items, total = await notice_service.get_all_notices(
        tenant_context.tenant_id,
        page,
        page_size,
        search,
        client_id,
        authority,
        notice_type,
        status,
        priority,
        assignee_id,
        team_id,
        received_date_from,
        received_date_to,
        deadline_from,
        deadline_to,
        sort_by,
        sort_order,
    )
    return NoticeListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/{notice_id}",
    response_model=NoticeResponse,
    summary="Get notice by ID",
)
async def get_notice(
    notice_id: UUID,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.read")),
):
    return await notice_service.get_notice_by_id(notice_id, tenant_context.tenant_id)


@router.patch(
    "/{notice_id}",
    response_model=NoticeResponse,
    summary="Update notice",
)
async def update_notice(
    notice_id: UUID,
    data: NoticeUpdate,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.update")),
):
    return await notice_service.update_notice(notice_id, tenant_context.tenant_id, data, current_user.id)


@router.patch(
    "/{notice_id}/status",
    response_model=NoticeResponse,
    summary="Update notice status",
)
async def update_notice_status(
    notice_id: UUID,
    data: NoticeStatusUpdate,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.transition")),
):
    return await notice_service.update_status(notice_id, tenant_context.tenant_id, data, current_user.id)


@router.patch(
    "/{notice_id}/response",
    response_model=NoticeResponse,
    summary="Update notice response",
)
async def update_notice_response(
    notice_id: UUID,
    data: NoticeResponseUpdate,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.update")),
):
    return await notice_service.update_response(notice_id, tenant_context.tenant_id, data, current_user.id)


@router.patch(
    "/{notice_id}/close",
    response_model=NoticeResponse,
    summary="Close notice",
)
async def close_notice(
    notice_id: UUID,
    data: NoticeClosureUpdate,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.transition")),
):
    return await notice_service.close_notice(notice_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/{notice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notice",
)
async def delete_notice(
    notice_id: UUID,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.delete")),
):
    await notice_service.delete_notice(notice_id, tenant_context.tenant_id)


# Escalation endpoints
@router.post(
    "/{notice_id}/escalate",
    response_model=NoticeEscalationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Escalate notice",
)
async def escalate_notice(
    notice_id: UUID,
    data: NoticeEscalationCreate,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.escalate")),
):
    return await notice_service.escalate_notice(notice_id, tenant_context.tenant_id, data, current_user.id)


@router.get(
    "/{notice_id}/escalations",
    response_model=list[NoticeEscalationResponse],
    summary="Get escalation history",
)
async def get_escalation_history(
    notice_id: UUID,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.read")),
):
    return await notice_service.get_escalation_history(notice_id, tenant_context.tenant_id)


@router.post(
    "/escalations/{escalation_id}/resolve",
    response_model=NoticeEscalationResponse,
    summary="Resolve escalation",
)
async def resolve_escalation(
    escalation_id: UUID,
    notice_service: NoticeService = Depends(get_notice_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notices.escalate")),
):
    return await notice_service.resolve_escalation(escalation_id, tenant_context.tenant_id, current_user.id)
