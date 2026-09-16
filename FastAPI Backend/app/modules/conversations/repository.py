from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.conversations.models import Conversation, ConversationMessage, ConversationStatus


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: UUID, tenant_id: UUID) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.client),
                selectinload(Conversation.assignee),
            )
            .where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_messages(self, conversation_id: UUID, tenant_id: UUID) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.client),
                selectinload(Conversation.assignee),
                selectinload(Conversation.messages),
            )
            .where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        assignee_id: UUID | None = None,
        status: ConversationStatus | None = None,
        priority: str | None = None,
        channel: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Conversation], int]:
        query = (
            select(Conversation)
            .options(
                selectinload(Conversation.client),
                selectinload(Conversation.assignee),
            )
            .where(Conversation.tenant_id == tenant_id)
        )
        count_query = select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Conversation.subject.ilike(f"%{search}%"),
                Conversation.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(Conversation.client_id == client_id)
            count_query = count_query.where(Conversation.client_id == client_id)

        if assignee_id:
            query = query.where(Conversation.assignee_id == assignee_id)
            count_query = count_query.where(Conversation.assignee_id == assignee_id)

        if status:
            query = query.where(Conversation.status == status)
            count_query = count_query.where(Conversation.status == status)

        if priority:
            query = query.where(Conversation.priority == priority)
            count_query = count_query.where(Conversation.priority == priority)

        if channel:
            query = query.where(Conversation.channel == channel)
            count_query = count_query.where(Conversation.channel == channel)

        if date_from:
            query = query.where(Conversation.updated_at >= date_from)
            count_query = count_query.where(Conversation.updated_at >= date_from)

        if date_to:
            query = query.where(Conversation.updated_at <= date_to)
            count_query = count_query.where(Conversation.updated_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Conversation, sort_by):
            sort_column = getattr(Conversation, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.updated_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_messages(
        self,
        conversation_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ConversationMessage], int]:
        query = (
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.tenant_id == tenant_id,
            )
            .order_by(ConversationMessage.created_at.asc())
        )
        count_query = select(func.count(ConversationMessage.id)).where(
            ConversationMessage.conversation_id == conversation_id,
            ConversationMessage.tenant_id == tenant_id,
        )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create_message(self, message: ConversationMessage) -> ConversationMessage:
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_message_by_id(self, message_id: UUID, tenant_id: UUID) -> ConversationMessage | None:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.id == message_id, ConversationMessage.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update(self, conversation: Conversation) -> Conversation:
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def delete(self, conversation: Conversation) -> None:
        await self.db.delete(conversation)
        await self.db.flush()