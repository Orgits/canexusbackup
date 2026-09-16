from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.clients.models import Client
from app.modules.communications.models import (
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationStatus,
)
from app.modules.communications.repository import CommunicationRepository
from app.modules.communications.schemas import CommunicationCreate
from app.modules.matters.models import Matter
from app.modules.tasks.models import Task


class CommunicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = CommunicationRepository(db)

    async def create(self, data: CommunicationCreate, tenant_id: UUID, created_by: UUID) -> Communication:
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

        communication = Communication(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=CommunicationStatus.DRAFT,
        )
        return await self.repository.create(communication)

    async def get_by_id(self, communication_id: UUID, tenant_id: UUID) -> Communication:
        communication = await self.repository.get_by_id(communication_id, tenant_id)
        if not communication:
            raise NotFoundException(detail="Communication not found")
        return communication

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        task_id: UUID | None = None,
        campaign_id: UUID | None = None,
        channel: CommunicationChannel | None = None,
        direction: CommunicationDirection | None = None,
        status: CommunicationStatus | None = None,
        thread_id: UUID | None = None,
        conversation_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Communication], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, matter_id, task_id,
            campaign_id, channel, direction, status, thread_id, conversation_id,
            date_from, date_to, sort_by, sort_order
        )

    async def get_thread(self, thread_id: UUID, tenant_id: UUID) -> list[Communication]:
        return await self.repository.get_thread(thread_id, tenant_id)

    async def get_conversation(self, conversation_id: UUID, tenant_id: UUID) -> list[Communication]:
        return await self.repository.get_conversation(conversation_id, tenant_id)

    async def update(self, communication_id: UUID, tenant_id: UUID, data: CommunicationCreate, updated_by: UUID) -> Communication:
        communication = await self.get_by_id(communication_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(communication, field, value)
        communication.updated_by = updated_by
        return await self.repository.update(communication)

    async def send(self, communication_id: UUID, tenant_id: UUID, sent_by: UUID) -> Communication:
        communication = await self.get_by_id(communication_id, tenant_id)
        communication.status = CommunicationStatus.SENT
        communication.sent_at = datetime.now()
        communication.updated_by = sent_by
        return await self.repository.update(communication)

    async def mark_delivered(self, communication_id: UUID, tenant_id: UUID) -> Communication:
        communication = await self.get_by_id(communication_id, tenant_id)
        communication.status = CommunicationStatus.DELIVERED
        communication.delivered_at = datetime.now()
        return await self.repository.update(communication)

    async def mark_read(self, communication_id: UUID, tenant_id: UUID) -> Communication:
        communication = await self.get_by_id(communication_id, tenant_id)
        communication.status = CommunicationStatus.READ
        communication.read_at = datetime.now()
        return await self.repository.update(communication)

    async def delete(self, communication_id: UUID, tenant_id: UUID) -> None:
        communication = await self.get_by_id(communication_id, tenant_id)
        await self.repository.delete(communication)
