from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.clients.models import Client
from app.modules.conversations.models import (
    Conversation,
    ConversationMessage,
    ConversationStatus,
    ConversationPriority,
)
from app.modules.conversations.repository import ConversationRepository
from app.modules.conversations.schemas import ConversationCreate, ConversationUpdate, ConversationMessageCreate
from app.modules.users.models import User


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ConversationRepository(db)

    async def create(self, data: ConversationCreate, tenant_id: UUID, created_by: UUID) -> Conversation:
        # Validate client exists and belongs to tenant
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        # Validate assignee if provided
        if data.assignee_id:
            assignee_result = await self.db.execute(
                select(User).where(User.id == data.assignee_id, User.tenant_id == tenant_id)
            )
            if not assignee_result.scalar_one_or_none():
                raise NotFoundException(detail="Assignee not found")

        conversation = Conversation(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=ConversationStatus.OPEN,
        )
        return await self.repository.create(conversation)

    async def get_by_id(self, conversation_id: UUID, tenant_id: UUID) -> Conversation:
        conversation = await self.repository.get_by_id(conversation_id, tenant_id)
        if not conversation:
            raise NotFoundException(detail="Conversation not found")
        return conversation

    async def get_by_id_with_messages(self, conversation_id: UUID, tenant_id: UUID) -> Conversation:
        conversation = await self.repository.get_by_id_with_messages(conversation_id, tenant_id)
        if not conversation:
            raise NotFoundException(detail="Conversation not found")
        return conversation

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        assignee_id: UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
        channel: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Conversation], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, assignee_id,
            status, priority, channel, date_from, date_to, sort_by, sort_order
        )

    async def update(
        self, conversation_id: UUID, tenant_id: UUID, data: ConversationUpdate, updated_by: UUID
    ) -> Conversation:
        conversation = await self.get_by_id(conversation_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status changes
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == ConversationStatus.CLOSED and conversation.status != ConversationStatus.CLOSED:
                conversation.closed_at = datetime.now()
                conversation.closed_by = updated_by
            elif new_status == ConversationStatus.OPEN and conversation.status == ConversationStatus.CLOSED:
                conversation.closed_at = None
                conversation.closed_by = None

        for field, value in update_data.items():
            setattr(conversation, field, value)

        conversation.updated_by = updated_by
        return await self.repository.update(conversation)

    async def add_message(
        self, conversation_id: UUID, tenant_id: UUID, data: ConversationMessageCreate, sender_id: UUID
    ) -> ConversationMessage:
        conversation = await self.get_by_id(conversation_id, tenant_id)

        message = ConversationMessage(
            **data.model_dump(),
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            sender_id=sender_id,
        )
        message = await self.repository.create_message(message)

        # Update conversation last message info
        conversation.last_message_at = datetime.now()
        conversation.last_message_preview = data.content[:500] if data.content else None
        conversation.updated_at = datetime.now()
        conversation.updated_by = sender_id

        await self.db.flush()
        await self.db.refresh(message)

        return message

    async def get_messages(
        self,
        conversation_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ConversationMessage], int]:
        conversation = await self.get_by_id(conversation_id, tenant_id)
        return await self.repository.get_messages(conversation_id, tenant_id, page, page_size)

    async def close_conversation(self, conversation_id: UUID, tenant_id: UUID, closed_by: UUID) -> Conversation:
        conversation = await self.get_by_id(conversation_id, tenant_id)
        conversation.status = ConversationStatus.CLOSED
        conversation.closed_at = datetime.now()
        conversation.closed_by = closed_by
        conversation.updated_by = closed_by
        return await self.repository.update(conversation)

    async def reopen_conversation(self, conversation_id: UUID, tenant_id: UUID, reopened_by: UUID) -> Conversation:
        conversation = await self.get_by_id(conversation_id, tenant_id)
        conversation.status = ConversationStatus.OPEN
        conversation.closed_at = None
        conversation.closed_by = None
        conversation.updated_by = reopened_by
        return await self.repository.update(conversation)

    async def delete(self, conversation_id: UUID, tenant_id: UUID) -> None:
        conversation = await self.get_by_id(conversation_id, tenant_id)
        await self.repository.delete(conversation)