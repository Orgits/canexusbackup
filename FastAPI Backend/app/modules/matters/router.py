from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy.dependencies import get_current_tenant
from app.modules.matters.schemas import (
    MatterCreate,
    MatterListResponse,
    MatterResponse,
    MatterStatusTransition,
    MatterUpdate,
)
from app.modules.matters.service import MatterService
from app.modules.users.models import User

router = APIRouter()


@router.post("", response_model=MatterResponse, status_code=status.HTTP_201_CREATED)
async def create_matter(
    data: MatterCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.MATTERS_CREATE)),
):
    service = MatterService(db)
    matter = await service.create(data, current_tenant.id, current_user.id)
    return MatterResponse.model_validate(matter)


@router.get("", response_model=MatterListResponse)
async def list_matters(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    matter_type: str = None,
    status: str = None,
    priority: str = None,
    responsible_user_id: UUID = None,
    responsible_team_id: UUID = None,
    due_date_from: datetime = None,
    due_date_to: datetime = None,
    tags: str = None,
    sort_by: str = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.MATTERS_READ)),
):
    service = MatterService(db)
    tag_list = tags.split(",") if tags else None
    items, total = await service.get_all(
        current_tenant.id, page, page_size, search, client_id, matter_type,
        status, priority, responsible_user_id, responsible_team_id,
        due_date_from, due_date_to, tag_list, sort_by, sort_order
    )
    return MatterListResponse(
        items=[MatterResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{matter_id}", response_model=MatterResponse)
async def get_matter(
    matter_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.MATTERS_READ)),
):
    service = MatterService(db)
    matter = await service.get_by_id(matter_id, current_tenant.id)
    return MatterResponse.model_validate(matter)


@router.patch("/{matter_id}", response_model=MatterResponse)
async def update_matter(
    matter_id: UUID,
    data: MatterUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.MATTERS_UPDATE)),
):
    service = MatterService(db)
    matter = await service.update(matter_id, current_tenant.id, data, current_user.id)
    return MatterResponse.model_validate(matter)


@router.post("/{matter_id}/status", response_model=MatterResponse)
async def transition_matter_status(
    matter_id: UUID,
    data: MatterStatusTransition,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.MATTERS_UPDATE)),
):
    service = MatterService(db)
    matter = await service.transition_status(matter_id, current_tenant.id, data, current_user.id)
    return MatterResponse.model_validate(matter)


@router.delete("/{matter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_matter(
    matter_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.MATTERS_DELETE)),
):
    service = MatterService(db)
    await service.delete(matter_id, current_tenant.id)
