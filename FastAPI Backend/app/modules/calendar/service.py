from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.calendar.models import CalendarEvent, EventType
from app.modules.calendar.repository import CalendarRepository
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate
from app.modules.clients.models import Client
from app.modules.compliance.models import ComplianceCycle
from app.modules.matters.models import Matter
from app.modules.tasks.models import Task
from app.modules.users.models import User


class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = CalendarRepository(db)

    async def create(self, data: CalendarEventCreate, tenant_id: UUID, created_by: UUID) -> CalendarEvent:
        if data.client_id:
            client_result = await self.db.execute(
                select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        if data.matter_id:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == data.matter_id, Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        if data.task_id:
            task_result = await self.db.execute(
                select(Task).where(Task.id == data.task_id, Task.tenant_id == tenant_id)
            )
            if not task_result.scalar_one_or_none():
                raise NotFoundException(detail="Task not found")

        if data.compliance_cycle_id:
            cycle_result = await self.db.execute(
                select(ComplianceCycle).where(ComplianceCycle.id == data.compliance_cycle_id, ComplianceCycle.tenant_id == tenant_id)
            )
            if not cycle_result.scalar_one_or_none():
                raise NotFoundException(detail="Compliance cycle not found")

        if data.user_id:
            user_result = await self.db.execute(
                select(User).where(User.id == data.user_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="User not found")

        for attendee_id in data.attendee_ids:
            user_result = await self.db.execute(
                select(User).where(User.id == attendee_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail=f"Attendee {attendee_id} not found")

        event = CalendarEvent(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create(event)

    async def get_by_id(self, event_id: UUID, tenant_id: UUID) -> CalendarEvent:
        event = await self.repository.get_by_id(event_id, tenant_id)
        if not event:
            raise NotFoundException(detail="Calendar event not found")
        return event

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
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, matter_id,
            user_id, event_type, start_from, start_to, sort_by, sort_order
        )

    async def get_events_in_range(
        self,
        tenant_id: UUID,
        start_from: datetime,
        start_to: datetime,
        user_id: UUID | None = None,
    ) -> list[CalendarEvent]:
        return await self.repository.get_events_in_range(tenant_id, start_from, start_to, user_id)

    async def update(self, event_id: UUID, tenant_id: UUID, data: CalendarEventUpdate, updated_by: UUID) -> CalendarEvent:
        event = await self.get_by_id(event_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("client_id"):
            client_result = await self.db.execute(
                select(Client).where(Client.id == update_data["client_id"], Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        if update_data.get("matter_id"):
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == update_data["matter_id"], Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        if update_data.get("task_id"):
            task_result = await self.db.execute(
                select(Task).where(Task.id == update_data["task_id"], Task.tenant_id == tenant_id)
            )
            if not task_result.scalar_one_or_none():
                raise NotFoundException(detail="Task not found")

        if update_data.get("compliance_cycle_id"):
            cycle_result = await self.db.execute(
                select(ComplianceCycle).where(ComplianceCycle.id == update_data["compliance_cycle_id"], ComplianceCycle.tenant_id == tenant_id)
            )
            if not cycle_result.scalar_one_or_none():
                raise NotFoundException(detail="Compliance cycle not found")

        if update_data.get("user_id"):
            user_result = await self.db.execute(
                select(User).where(User.id == update_data["user_id"], User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="User not found")

        if "attendee_ids" in update_data:
            for attendee_id in update_data["attendee_ids"]:
                user_result = await self.db.execute(
                    select(User).where(User.id == attendee_id, User.tenant_id == tenant_id)
                )
                if not user_result.scalar_one_or_none():
                    raise NotFoundException(detail=f"Attendee {attendee_id} not found")

        for field, value in update_data.items():
            setattr(event, field, value)
        event.updated_by = updated_by
        return await self.repository.update(event)

    async def delete(self, event_id: UUID, tenant_id: UUID) -> None:
        event = await self.get_by_id(event_id, tenant_id)
        await self.repository.delete(event)
