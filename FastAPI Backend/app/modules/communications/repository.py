from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.communications.models import Communication, CommunicationChannel, CommunicationDirection, CommunicationStatus


class CommunicationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, communication: Communication) -> Communication:
        self.db.add(communication)
        await self.db.flush()
        await self.db.refresh(communication)
        return communication

    async def get_by_id(self, communication_id: UUID, tenant_id: UUID) -> Optional[Communication]:
        result = await self.db.execute(
            select(Communication)
            .options(
                selectinload(Communication.client),
                selectinload(Communication.matter),
                selectinload(Communication.task),
                selectinload(Communication.campaign),
            )
            .where(Communication.id == communication_id, Communication.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        matter_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
        channel: Optional[CommunicationChannel] = None,
        direction: Optional[CommunicationDirection] = None,
        status: Optional[CommunicationStatus] = None,
        thread_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Tuple[List[Communication], int]:
        query = (
            select(Communication)
            .options(
                selectinload(Communication.client),
                selectinload(Communication.matter),
                selectinload(Communication.task),
                selectinload(Communication.campaign),
            )
            .where(Communication.tenant_id == tenant_id)
        )
        count_query = select(func.count(Communication.id)).where(Communication.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Communication.subject.ilike(f"%{search}%"),
                Communication.body.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(Communication.client_id == client_id)
            count_query = count_query.where(Communication.client_id == client_id)

        if matter_id:
            query = query.where(Communication.matter_id == matter_id)
            count_query = count_query.where(Communication.matter_id == matter_id)

        if task_id:
            query = query.where(Communication.task_id == task_id)
            count_query = count_query.where(Communication.task_id == task_id)

        if campaign_id:
            query = query.where(Communication.campaign_id == campaign_id)
            count_query = count_query.where(Communication.campaign_id == campaign_id)

        if channel:
            query = query.where(Communication.channel == channel)
            count_query = count_query.where(Communication.channel == channel)

        if direction:
            query = query.where(Communication.direction == direction)
            count_query = count_query.where(Communication.direction == direction)

        if status:
            query = query.where(Communication.status == status)
            count_query = count_query.where(Communication.status == status)

        if thread_id:
            query = query.where(Communication.thread_id == thread_id)
            count_query = count_query.where(Communication.thread_id == thread_id)

        if conversation_id:
            query = query.where(Communication.conversation_id == conversation_id)
            count_query = count_query.where(Communication.conversation_id == conversation_id)

        if date_from:
            query = query.where(Communication.sent_at >= date_from)
            count_query = count_query.where(Communication.sent_at >= date_from)

        if date_to:
            query = query.where(Communication.sent_at <= date_to)
            count_query = count_query.where(Communication.sent_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Communication, sort_by):
            sort_column = getattr(Communication, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Communication.sent_at.desc().nullslast(), Communication.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_thread(self, thread_id: UUID, tenant_id: UUID) -> List[Communication]:
        result = await self.db.execute(
            select(Communication)
            .where(Communication.thread_id == thread_id, Communication.tenant_id == tenant_id)
            .order_by(Communication.sent_at.asc().nullslast(), Communication.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_conversation(self, conversation_id: UUID, tenant_id: UUID) -> List[Communication]:
        result = await self.db.execute(
            select(Communication)
            .where(Communication.conversation_id == conversation_id, Communication.tenant_id == tenant_id)
            .order_by(Communication.sent_at.asc().nullslast(), Communication.created_at.asc())
        )
        return list(result.scalars().all())

    async def update(self, communication: Communication) -> Communication:
        await self.db.flush()
        await self.db.refresh(communication)
        return communication

    async def delete(self, communication: Communication) -> None:
        await self.db.delete(communication)
        await self.db.flush()