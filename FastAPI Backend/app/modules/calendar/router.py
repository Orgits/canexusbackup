from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.security.dependencies import get_current_active_user
from app.core.tenancy.dependencies import get_current_tenant
from app.modules.calendar.schemas import (
    CalendarEventCreate,
    CalendarEventListResponse,
    CalendarEventResponse,
    CalendarEventUpdate,
)
from app.modules.calendar.service import CalendarService
from app.modules.users.models import User

router = APIRouter()


@router.post("", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    data: CalendarEventCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.CALENDAR_CREATE)),
):
    service = CalendarService(db)
    event = await service.create(data, current_tenant.id, current_user.id)
    return CalendarEventResponse.model_validate(event)


@router.get("", response_model=CalendarEventListResponse)
async def list_calendar_events(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    matter_id: UUID = None,
    user_id: UUID = None,
    event_type: str = None,
    start_from: datetime = None,
    start_to: datetime = None,
    sort_by: str = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.CALENDAR_READ)),
):
    service = CalendarService(db)
    items, total = await service.get_all(
        current_tenant.id, page, page_size, search, client_id, matter_id,
        user_id, event_type, start_from, start_to, sort_by, sort_order
    )
    return CalendarEventListResponse(
        items=[CalendarEventResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/range", response_model=list[CalendarEventResponse])
async def get_events_in_range(
    start_from: datetime,
    start_to: datetime,
    user_id: UUID = None,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.CALENDAR_READ)),
):
    service = CalendarService(db)
    items = await service.get_events_in_range(current_tenant.id, start_from, start_to, user_id)
    return [CalendarEventResponse.model_validate(item) for item in items]


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_calendar_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.CALENDAR_READ)),
):
    service = CalendarService(db)
    event = await service.get_by_id(event_id, current_tenant.id)
    return CalendarEventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(
    event_id: UUID,
    data: CalendarEventUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.CALENDAR_UPDATE)),
):
    service = CalendarService(db)
    event = await service.update(event_id, current_tenant.id, data, current_user.id)
    return CalendarEventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.CALENDAR_DELETE)),
):
    service = CalendarService(db)
    await service.delete(event_id, current_tenant.id)
