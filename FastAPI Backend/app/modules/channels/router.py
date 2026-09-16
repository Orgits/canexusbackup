from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.channels.schemas import (
    ChannelProviderCreate,
    ChannelProviderListResponse,
    ChannelProviderResponse,
    ChannelProviderUpdate,
    MessageLogListResponse,
    MessageLogResponse,
    SendMessageRequest,
)
from app.modules.channels.service import ChannelService, MessageService
from app.modules.users.models import User

router = APIRouter(prefix="/channels", tags=["Channels"])


@router.post("/providers", response_model=ChannelProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_channel_provider(
    data: ChannelProviderCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_CREATE)),
):
    service = ChannelService(db)
    provider = await service.create_provider(data, tenant_context.tenant_id, current_user.id)
    return ChannelProviderResponse.model_validate(provider)


@router.get("/providers", response_model=ChannelProviderListResponse)
async def list_channel_providers(
    page: int = 1,
    page_size: int = 20,
    channel_type: str = None,
    status: str = None,
    is_active: bool = None,
    search: str = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = ChannelService(db)
    items, total = await service.list_providers(
        tenant_context.tenant_id, page, page_size, channel_type, status, is_active, search
    )
    return ChannelProviderListResponse(
        items=[ChannelProviderResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/providers/default/{channel_type}", response_model=ChannelProviderResponse)
async def get_default_channel_provider(
    channel_type: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = ChannelService(db)
    provider = await service.get_default_provider(channel_type, tenant_context.tenant_id)
    return ChannelProviderResponse.model_validate(provider)


@router.get("/providers/{provider_id}", response_model=ChannelProviderResponse)
async def get_channel_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = ChannelService(db)
    provider = await service.get_provider(provider_id, tenant_context.tenant_id)
    return ChannelProviderResponse.model_validate(provider)


@router.patch("/providers/{provider_id}", response_model=ChannelProviderResponse)
async def update_channel_provider(
    provider_id: UUID,
    data: ChannelProviderUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = ChannelService(db)
    provider = await service.update_provider(provider_id, tenant_context.tenant_id, data.model_dump(exclude_unset=True), current_user.id)
    return ChannelProviderResponse.model_validate(provider)


@router.post("/providers/{provider_id}/set-default", response_model=ChannelProviderResponse)
async def set_default_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = ChannelService(db)
    provider = await service.set_default(provider_id, tenant_context.tenant_id)
    return ChannelProviderResponse.model_validate(provider)


@router.post("/providers/{provider_id}/test", response_model=dict)
async def test_channel_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = ChannelService(db)
    result = await service.test_provider(provider_id, tenant_context.tenant_id)
    return result


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_DELETE)),
):
    service = ChannelService(db)
    await service.delete_provider(provider_id, tenant_context.tenant_id)


# Message logs
@router.post("/messages", response_model=MessageLogResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: SendMessageRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_SEND)),
):
    service = MessageService(db)
    log = await service.send_message(data, tenant_context.tenant_id, current_user.id)
    return MessageLogResponse.model_validate(log)


@router.get("/messages", response_model=MessageLogListResponse)
async def list_messages(
    page: int = 1,
    page_size: int = 50,
    channel_type: str = None,
    provider_id: UUID = None,
    status: str = None,
    recipient: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = MessageService(db)
    items, total = await service.get_logs(
        tenant_context.tenant_id, page, page_size, channel_type, provider_id, status, recipient, date_from, date_to
    )
    return MessageLogListResponse(
        items=[MessageLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/messages/{log_id}", response_model=MessageLogResponse)
async def get_message_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = MessageService(db)
    log = await service.get_log(log_id, tenant_context.tenant_id)
    return MessageLogResponse.model_validate(log)


@router.post("/messages/{log_id}/retry", response_model=MessageLogResponse)
async def retry_message(
    log_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = MessageService(db)
    log = await service.retry_message(log_id, tenant_context.tenant_id)
    return MessageLogResponse.model_validate(log)