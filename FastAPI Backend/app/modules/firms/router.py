from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security.dependencies import get_current_active_user
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.modules.firms.schemas import FirmCreate, FirmUpdate, FirmResponse, FirmListResponse
from app.modules.firms.service import FirmService
from app.modules.users.models import User

router = APIRouter()


@router.post("", response_model=FirmResponse, status_code=status.HTTP_201_CREATED)
async def create_firm(
    data: FirmCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = FirmService(db)
    firm = await service.create(data)
    return FirmResponse.model_validate(firm)


@router.get("", response_model=FirmListResponse)
async def list_firms(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = FirmService(db)
    items, total = await service.get_all(page, page_size, search, is_active)
    return FirmListResponse(
        items=[FirmResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{firm_id}", response_model=FirmResponse)
async def get_firm(
    firm_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = FirmService(db)
    firm = await service.get_by_id(firm_id)
    return FirmResponse.model_validate(firm)


@router.patch("/{firm_id}", response_model=FirmResponse)
async def update_firm(
    firm_id: str,
    data: FirmUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = FirmService(db)
    firm = await service.update(firm_id, data)
    return FirmResponse.model_validate(firm)


@router.delete("/{firm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_firm(
    firm_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = FirmService(db)
    await service.delete(firm_id)
    return None


@router.post("/{firm_id}/activate", response_model=FirmResponse)
async def activate_firm(
    firm_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = FirmService(db)
    firm = await service.activate(firm_id)
    return FirmResponse.model_validate(firm)


@router.post("/{firm_id}/deactivate", response_model=FirmResponse)
async def deactivate_firm(
    firm_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = FirmService(db)
    firm = await service.deactivate(firm_id)
    return FirmResponse.model_validate(firm)