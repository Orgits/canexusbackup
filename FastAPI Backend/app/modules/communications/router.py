from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.security.dependencies import get_current_active_user
from app.core.tenancy import get_tenant_context
from app.modules.communications.schemas import CommunicationCreate, CommunicationListResponse, CommunicationResponse
from app.modules.communications.service import CommunicationService
from app.modules.users.models import User

router = APIRouter()


@router.post("", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED)
async def create_communication(
    data: CommunicationCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.COMMUNICATIONS_CREATE)),
):
    service = CommunicationService(db)
    communication = await service.create(data, tenant_context.tenant_id, current_user.id)
    return CommunicationResponse.model_validate(communication)


@router.get("", response_model=CommunicationListResponse)
async def list_communications(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    matter_id: UUID = None,
    task_id: UUID = None,
    campaign_id: UUID = None,
    channel: str = None,
    direction: str = None,
    status: str = None,
    thread_id: UUID = None,
    conversation_id: UUID = None,
    date_from: datetime = None,
    date_to: datetime = None,
    sort_by: str = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = CommunicationService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, client_id, matter_id, task_id,
        campaign_id, channel, direction, status, thread_id, conversation_id,
        date_from, date_to, sort_by, sort_order
    )
    return CommunicationListResponse(
        items=[CommunicationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/thread/{thread_id}", response_model=list[CommunicationResponse])
async def get_thread(
    thread_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = CommunicationService(db)
    items = await service.get_thread(thread_id, tenant_context.tenant_id)
    return [CommunicationResponse.model_validate(item) for item in items]


@router.get("/conversation/{conversation_id}", response_model=list[CommunicationResponse])
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = CommunicationService(db)
    items = await service.get_conversation(conversation_id, tenant_context.tenant_id)
    return [CommunicationResponse.model_validate(item) for item in items]


@router.get("/{communication_id}", response_model=CommunicationResponse)
async def get_communication(
    communication_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = CommunicationService(db)
    communication = await service.get_by_id(communication_id, tenant_context.tenant_id)
    return CommunicationResponse.model_validate(communication)


@router.post("/{communication_id}/send", response_model=CommunicationResponse)
async def send_communication(
    communication_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.COMMUNICATIONS_SEND)),
):
    service = CommunicationService(db)
    communication = await service.send(communication_id, tenant_context.tenant_id, current_user.id)
    return CommunicationResponse.model_validate(communication)


@router.delete("/{communication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_communication(
    communication_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission(Permission.COMMUNICATIONS_DELETE)),
):
    service = CommunicationService(db)
    await service.delete(communication_id, tenant_context.tenant_id)
