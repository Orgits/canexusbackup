from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.suppression.schemas import (
    SuppressionCheckRequest,
    SuppressionCheckResponse,
    SuppressionCreate,
    SuppressionListResponse,
    SuppressionResponse,
    SuppressionUpdate,
)
from app.modules.suppression.service import SuppressionService
from app.modules.users.models import User

router = APIRouter(prefix="/suppression", tags=["Suppression"])


@router.post("", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
async def create_suppression(
    data: SuppressionCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = SuppressionService(db)
    suppression = await service.create(data, tenant_context.tenant_id, current_user.id)
    return SuppressionResponse.model_validate(suppression)


@router.get("", response_model=SuppressionListResponse)
async def list_suppressions(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    channel: str = None,
    reason: str = None,
    is_global: bool = None,
    date_from: datetime = None,
    date_to: datetime = None,
    sort_by: str = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = SuppressionService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, channel, reason, is_global, date_from, date_to, sort_by, sort_order
    )
    return SuppressionListResponse(
        items=[SuppressionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{suppression_id}", response_model=SuppressionResponse)
async def get_suppression(
    suppression_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = SuppressionService(db)
    suppression = await service.get_by_id(suppression_id, tenant_context.tenant_id)
    return SuppressionResponse.model_validate(suppression)


@router.patch("/{suppression_id}", response_model=SuppressionResponse)
async def update_suppression(
    suppression_id: UUID,
    data: SuppressionUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = SuppressionService(db)
    suppression = await service.update(suppression_id, tenant_context.tenant_id, data, current_user.id)
    return SuppressionResponse.model_validate(suppression)


@router.delete("/{suppression_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suppression(
    suppression_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_DELETE)),
):
    service = SuppressionService(db)
    await service.delete(suppression_id, tenant_context.tenant_id)


@router.post("/check", response_model=SuppressionCheckResponse)
async def check_suppression(
    request: SuppressionCheckRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = SuppressionService(db)
    result = await service.check_suppression(request.value, request.channel, tenant_context.tenant_id)
    return SuppressionCheckResponse(**result)


@router.post("/bulk-check", response_model=dict[str, bool])
async def bulk_check_suppression(
    request: SuppressionCheckRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = SuppressionService(db)
    results = await service.bulk_check(request, tenant_context.tenant_id)
    return results