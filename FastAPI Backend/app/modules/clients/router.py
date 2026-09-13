from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_async_db
from app.core.tenancy.dependencies import get_current_tenant, setup_tenant_context
from app.core.security.dependencies import get_current_active_user
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.modules.clients.schemas import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientListResponse,
    ClientOverviewResponse,
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
)
from app.modules.clients.service import ClientService, ClientContactService, ClientServiceService
from app.modules.users.models import User

router = APIRouter()


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_CREATE)),
):
    service = ClientService(db)
    client = await service.create(data, current_tenant.id, current_user.id)
    return ClientResponse.model_validate(client)


@router.get("", response_model=ClientListResponse)
async def list_clients(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    category: str = None,
    status: str = None,
    responsible_user_id: UUID = None,
    responsible_team_id: UUID = None,
    is_archived: bool = False,
    tags: str = None,
    sort_by: str = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_READ)),
):
    service = ClientService(db)
    tag_list = tags.split(",") if tags else None
    items, total = await service.get_all(
        current_tenant.id, page, page_size, search, category, status,
        responsible_user_id, responsible_team_id, is_archived, tag_list, sort_by, sort_order
    )
    return ClientListResponse(
        items=[ClientResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_READ)),
):
    service = ClientService(db)
    client = await service.get_by_id(client_id, current_tenant.id)
    return ClientResponse.model_validate(client)


@router.get("/{client_id}/overview", response_model=ClientOverviewResponse)
async def get_client_overview(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_READ)),
):
    service = ClientService(db)
    overview = await service.get_overview(client_id, current_tenant.id)
    return ClientOverviewResponse(**overview)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    data: ClientUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientService(db)
    client = await service.update(client_id, current_tenant.id, data, current_user.id)
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_DELETE)),
):
    service = ClientService(db)
    await service.delete(client_id, current_tenant.id)
    return None


@router.post("/{client_id}/archive", response_model=ClientResponse)
async def archive_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_DELETE)),
):
    service = ClientService(db)
    client = await service.archive(client_id, current_tenant.id, current_user.id)
    return ClientResponse.model_validate(client)


@router.post("/{client_id}/unarchive", response_model=ClientResponse)
async def unarchive_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientService(db)
    client = await service.unarchive(client_id, current_tenant.id)
    return ClientResponse.model_validate(client)


contact_router = APIRouter(prefix="/{client_id}/contacts", tags=["Client Contacts"])


@contact_router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    client_id: UUID,
    data: ContactCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientContactService(db)
    contact = await service.create(client_id, current_tenant.id, data, current_user.id)
    return ContactResponse.model_validate(contact)


@contact_router.get("", response_model=list[ContactResponse])
async def list_contacts(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_READ)),
):
    service = ClientContactService(db)
    contacts = await service.get_by_client(client_id, current_tenant.id)
    return [ContactResponse.model_validate(c) for c in contacts]


@contact_router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    client_id: UUID,
    contact_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_READ)),
):
    service = ClientContactService(db)
    contact = await service.get_by_id(contact_id, current_tenant.id)
    return ContactResponse.model_validate(contact)


@contact_router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    client_id: UUID,
    contact_id: UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientContactService(db)
    contact = await service.update(contact_id, current_tenant.id, data, current_user.id)
    return ContactResponse.model_validate(contact)


@contact_router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    client_id: UUID,
    contact_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientContactService(db)
    await service.delete(contact_id, current_tenant.id)
    return None


service_router = APIRouter(prefix="/{client_id}/services", tags=["Client Services"])


@service_router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    client_id: UUID,
    data: ServiceCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientServiceService(db)
    svc = await service.create(client_id, current_tenant.id, data, current_user.id)
    return ServiceResponse.model_validate(svc)


@service_router.get("", response_model=list[ServiceResponse])
async def list_services(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_READ)),
):
    service = ClientServiceService(db)
    services = await service.get_by_client(client_id, current_tenant.id)
    return [ServiceResponse.model_validate(s) for s in services]


@service_router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    client_id: UUID,
    service_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_READ)),
):
    service = ClientServiceService(db)
    svc = await service.get_by_id(service_id, current_tenant.id)
    return ServiceResponse.model_validate(svc)


@service_router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    client_id: UUID,
    service_id: UUID,
    data: ServiceUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientServiceService(db)
    svc = await service.update(service_id, current_tenant.id, data, current_user.id)
    return ServiceResponse.model_validate(svc)


@service_router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    client_id: UUID,
    service_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.CLIENTS_UPDATE)),
):
    service = ClientServiceService(db)
    await service.delete(service_id, current_tenant.id)
    return None


router.include_router(contact_router)
router.include_router(service_router)