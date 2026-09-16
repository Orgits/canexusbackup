from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.conversations.schemas import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessageCreate,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationUpdate,
)
from app.modules.conversations.service import ConversationService
from app.modules.users.models import User

router = APIRouter()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_CREATE)),
):
    service = ConversationService(db)
    conversation = await service.create(data, tenant_context.tenant_id, current_user.id)
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    client_id: UUID | None = None,
    assignee_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    channel: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_READ)),
):
    service = ConversationService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, client_id, assignee_id,
        status, priority, channel, date_from, date_to, sort_by, sort_order
    )
    return ConversationListResponse(
        items=[ConversationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_READ)),
):
    service = ConversationService(db)
    conversation = await service.get_by_id_with_messages(conversation_id, tenant_context.tenant_id)
    return ConversationDetailResponse.model_validate(conversation)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_UPDATE)),
):
    service = ConversationService(db)
    conversation = await service.update(conversation_id, tenant_context.tenant_id, data, current_user.id)
    return ConversationResponse.model_validate(conversation)


@router.post("/{conversation_id}/close", response_model=ConversationResponse)
async def close_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_UPDATE)),
):
    service = ConversationService(db)
    conversation = await service.close_conversation(conversation_id, tenant_context.tenant_id, current_user.id)
    return ConversationResponse.model_validate(conversation)


@router.post("/{conversation_id}/reopen", response_model=ConversationResponse)
async def reopen_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_UPDATE)),
):
    service = ConversationService(db)
    conversation = await service.reopen_conversation(conversation_id, tenant_context.tenant_id, current_user.id)
    return ConversationResponse.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_DELETE)),
):
    service = ConversationService(db)
    await service.delete(conversation_id, tenant_context.tenant_id)


# Message endpoints
@router.post("/{conversation_id}/messages", response_model=ConversationMessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: UUID,
    data: ConversationMessageCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_CREATE)),
):
    service = ConversationService(db)
    message = await service.add_message(conversation_id, tenant_context.tenant_id, data, current_user.id)
    return ConversationMessageResponse.model_validate(message)


@router.get("/{conversation_id}/messages", response_model=list[ConversationMessageResponse])
async def get_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CONVERSATIONS_READ)),
):
    service = ConversationService(db)
    messages, _ = await service.get_messages(conversation_id, tenant_context.tenant_id, page, page_size)
    return [ConversationMessageResponse.model_validate(m) for m in messages]