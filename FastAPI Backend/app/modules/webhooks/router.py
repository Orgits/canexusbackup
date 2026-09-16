from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.webhooks.schemas import (
    WebhookEndpointCreate,
    WebhookEndpointListResponse,
    WebhookEndpointResponse,
    WebhookEndpointUpdate,
    WebhookEventListResponse,
    WebhookEventResponse,
)
from app.modules.webhooks.service import WebhookService
from app.modules.users.models import User

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# Endpoint management
@router.post("/endpoints", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_endpoint(
    data: WebhookEndpointCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_CREATE)),
):
    service = WebhookService(db)
    endpoint = await service.create_endpoint(data, tenant_context.tenant_id, current_user.id)
    return WebhookEndpointResponse.model_validate(endpoint)


@router.get("/endpoints", response_model=WebhookEndpointListResponse)
async def list_webhook_endpoints(
    page: int = 1,
    page_size: int = 20,
    is_active: bool = None,
    search: str = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_READ)),
):
    service = WebhookService(db)
    items, total = await service.list_endpoints(tenant_context.tenant_id, page, page_size, is_active, search)
    return WebhookEndpointListResponse(
        items=[WebhookEndpointResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/endpoints/stats", response_model=dict)
async def get_endpoint_stats(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_READ)),
):
    service = WebhookService(db)
    stats = await service.get_endpoint_stats(tenant_context.tenant_id)
    return stats


@router.get("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
async def get_webhook_endpoint(
    endpoint_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_READ)),
):
    service = WebhookService(db)
    endpoint = await service.get_endpoint(endpoint_id, tenant_context.tenant_id)
    return WebhookEndpointResponse.model_validate(endpoint)


@router.patch("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
async def update_webhook_endpoint(
    endpoint_id: UUID,
    data: WebhookEndpointUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_UPDATE)),
):
    service = WebhookService(db)
    endpoint = await service.update_endpoint(endpoint_id, tenant_context.tenant_id, data.model_dump(exclude_unset=True), current_user.id)
    return WebhookEndpointResponse.model_validate(endpoint)


@router.patch("/endpoints/{endpoint_id}/toggle", response_model=dict)
async def toggle_webhook_endpoint(
    endpoint_id: UUID,
    is_active: bool,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_UPDATE)),
):
    service = WebhookService(db)
    endpoint = await service.toggle_endpoint(endpoint_id, tenant_context.tenant_id, is_active)
    return {"message": f"Endpoint {'activated' if is_active else 'deactivated'}", "is_active": is_active}


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_endpoint(
    endpoint_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_DELETE)),
):
    service = WebhookService(db)
    await service.delete_endpoint(endpoint_id, tenant_context.tenant_id)


@router.get("/endpoints/stats", response_model=dict)
async def get_endpoint_stats(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_READ)),
):
    service = WebhookService(db)
    stats = await service.get_endpoint_stats(tenant_context.tenant_id)
    return stats


# Webhook event receiving endpoint (public - no auth required)
@router.post("/receive/{endpoint_id}")
async def receive_webhook(
    endpoint_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
):
    service = WebhookService(db)
    
    # Get endpoint
    endpoint = await service.repository.get_endpoint_by_id(endpoint_id, UUID("00000000-0000-0000-0000-000000000000"))
    if not endpoint:
        return {"status": "error", "message": "Endpoint not found"}
    
    if not endpoint.is_active:
        return {"status": "error", "message": "Endpoint is inactive"}
    
    # Verify secret if configured
    if endpoint.secret_verification and endpoint.secret:
        signature = request.headers.get("x-signature") or request.headers.get("x-signature-256")
        if not signature:
            return {"status": "error", "message": "Missing signature"}
        
        body = await request.body()
        expected_signature = hmac.new(
            endpoint.secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return {"status": "error", "message": "Invalid signature"}
    
    # Get payload
    try:
        payload = await request.json()
    except:
        payload = {}
    
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    
    # Determine tenant_id from endpoint
    tenant_id = endpoint.tenant_id
    
    # Receive event
    service = WebhookService(db)
    event = await service.receive_event(tenant_id, endpoint, await request.json(), dict(request.headers), dict(request.query_params), "custom")
    
    return {"status": "received", "event_id": str(event.id)}


# Event management
@router.get("/events", response_model=WebhookEventListResponse)
async def list_webhook_events(
    page: int = 1,
    page_size: int = 20,
    source: str = None,
    status: str = None,
    event_type: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_READ)),
):
    service = WebhookService(db)
    items, total = await service.repository.get_events(
        tenant_context.tenant_id, page, page_size, source, status, event_type, date_from, date_to
    )
    return WebhookEventListResponse(
        items=[WebhookEventResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/events/stats", response_model=dict)
async def get_event_stats(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_READ)),
):
    service = WebhookService(db)
    stats = await service.get_event_stats(tenant_context.tenant_id)
    return stats


@router.post("/events/retry", response_model=dict)
async def retry_failed_events(
    max_events: int = 100,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_UPDATE)),
):
    service = WebhookService(db)
    retried = await service.retry_failed_events(tenant_context.tenant_id, max_events)
    return {"retried": retried}


@router.get("/events/{event_id}", response_model=WebhookEventResponse)
async def get_webhook_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.WEBHOOKS_READ)),
):
    service = WebhookService(db)
    event = await service.repository.get_event_by_id(event_id, tenant_context.tenant_id)
    if not event:
        raise NotFoundException(detail="Webhook event not found")
    return WebhookEventResponse.model_validate(event)