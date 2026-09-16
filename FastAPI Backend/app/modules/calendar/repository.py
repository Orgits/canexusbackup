from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.calendar.models import CalendarEvent, EventType


class CalendarRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event: CalendarEvent) -> CalendarEvent:
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_by_id(self, event_id: UUID, tenant_id: UUID) -> CalendarEvent | None:
        result = await self.db.execute(
            select(CalendarEvent)
            .options(
                selectinload(CalendarEvent.client),
                selectinload(CalendarEvent.matter),
                selectinload(CalendarEvent.task),
                selectinload(CalendarEvent.compliance_cycle),
                selectinload(CalendarEvent.user),
            )
            .where(CalendarEvent.id == event_id, CalendarEvent.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        user_id: UUID | None = None,
        event_type: EventType | None = None,
        start_from: datetime | None = None,
        start_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[CalendarEvent], int]:
        query = (
            select(CalendarEvent)
            .options(
                selectinload(CalendarEvent.client),
                selectinload(CalendarEvent.matter),
                selectinload(CalendarEvent.task),
                selectinload(CalendarEvent.compliance_cycle),
                selectinload(CalendarEvent.user),
            )
            .where(CalendarEvent.tenant_id == tenant_id)
        )
        count_query = select(func.count(CalendarEvent.id)).where(CalendarEvent.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                CalendarEvent.title.ilike(f"%{search}%"),
                CalendarEvent.description.ilike(f"%{search}%"),
                CalendarEvent.location.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(CalendarEvent.client_id == client_id)
            count_query = count_query.where(CalendarEvent.client_id == client_id)

        if matter_id:
            query = query.where(CalendarEvent.matter_id == matter_id)
            count_query = count_query.where(CalendarEvent.matter_id == matter_id)

        if user_id:
            query = query.where(CalendarEvent.user_id == user_id)
            count_query = count_query.where(CalendarEvent.user_id == user_id)

        if event_type:
            query = query.where(CalendarEvent.event_type == event_type)
            count_query = count_query.where(CalendarEvent.event_type == event_type)

        if start_from:
            query = query.where(CalendarEvent.start_time >= start_from)
            count_query = count_query.where(CalendarEvent.start_time >= start_from)

        if start_to:
            query = query.where(CalendarEvent.start_time <= start_to)
            count_query = count_query.where(CalendarEvent.start_time <= start_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(CalendarEvent, sort_by):
            sort_column = getattr(CalendarEvent, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(CalendarEvent.start_time.asc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_events_in_range(
        self,
        tenant_id: UUID,
        start_from: datetime,
        start_to: datetime,
        user_id: UUID | None = None,
    ) -> list[CalendarEvent]:
        query = select(CalendarEvent).where(
            CalendarEvent.tenant_id == tenant_id,
            CalendarEvent.start_time >= start_from,
            CalendarEvent.start_time <= start_to,
        )
        if user_id:
            query = query.where(CalendarEvent.user_id == user_id)
        query = query.order_by(CalendarEvent.start_time.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, event: CalendarEvent) -> CalendarEvent:
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete(self, event: CalendarEvent) -> None:
        await self.db.delete(event)
        await self.db.flush()
