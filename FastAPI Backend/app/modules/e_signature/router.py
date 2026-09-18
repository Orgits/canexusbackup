from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.e_signature.schemas import (
    ESignatureCancelRequest,
    ESignatureProviderConfigCreate,
    ESignatureProviderConfigDetailResponse,
    ESignatureProviderConfigListResponse,
    ESignatureProviderConfigResponse,
    ESignatureProviderConfigUpdate,
    ESignatureRequestCreate,
    ESignatureRequestDetailResponse,
    ESignatureRequestListResponse,
    ESignatureRequestResponse,
    ESignatureRequestUpdate,
    ESignatureSendRequest,
    ESignatureWebhookEventCreate,
    ESignatureWebhookEventListResponse,
    ESignatureWebhookEventResponse,
    ESignerCreate,
    ESignerDetailResponse,
    ESignerListResponse,
    ESignerResponse,
    ESignerUpdate,
)
from app.modules.e_signature.service import (
    ESignatureProviderConfigService,
    ESignatureRequestService,
    ESignerService,
    ESignatureWebhookService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/e-signature", tags=["E-Signature"])


# ============================================================================
# E-Signature Request Endpoints
# ============================================================================

@router.post("/requests", response_model=ESignatureRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_esignature_request(
    data: ESignatureRequestCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = ESignatureRequestService(db)
    request = await service.create(data, tenant_context.tenant_id, current_user.id)
    return ESignatureRequestResponse.model_validate(request)


@router.get("/requests", response_model=ESignatureRequestListResponse)
async def list_esignature_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    document_id: UUID | None = None,
    engagement_document_id: UUID | None = None,
    provider: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = ESignatureRequestService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, document_id, engagement_document_id,
        provider, status, date_from, date_to, sort_by, sort_order
    )
    return ESignatureRequestListResponse(
        items=[ESignatureRequestResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/requests/{request_id}", response_model=ESignatureRequestDetailResponse)
async def get_esignature_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = ESignatureRequestService(db)
    request = await service.get_by_id(request_id, tenant_context.tenant_id)
    return ESignatureRequestDetailResponse.model_validate(request)


@router.patch("/requests/{request_id}", response_model=ESignatureRequestResponse)
async def update_esignature_request(
    request_id: UUID,
    data: ESignatureRequestUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = ESignatureRequestService(db)
    request = await service.update(request_id, tenant_context.tenant_id, data, current_user.id)
    return ESignatureRequestResponse.model_validate(request)


@router.post("/requests/send", response_model=ESignatureRequestResponse)
async def send_esignature_request(
    data: ESignatureSendRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = ESignatureRequestService(db)
    request = await service.send(data, tenant_context.tenant_id, current_user.id)
    return ESignatureRequestResponse.model_validate(request)


@router.post("/requests/cancel", response_model=ESignatureRequestResponse)
async def cancel_esignature_request(
    data: ESignatureCancelRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = ESignatureRequestService(db)
    request = await service.cancel(data, tenant_context.tenant_id, current_user.id)
    return ESignatureRequestResponse.model_validate(request)


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_esignature_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = ESignatureRequestService(db)
    await service.delete(request_id, tenant_context.tenant_id)


# ============================================================================
# E-Signer Endpoints
# ============================================================================

@router.get("/requests/{request_id}/signers", response_model=list[ESignerDetailResponse])
async def list_esigners(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = ESignerService(db)
    signers = await service.get_signers(request_id, tenant_context.tenant_id)
    return [ESignerDetailResponse.model_validate(s) for s in signers]


@router.post("/requests/{request_id}/signers", response_model=ESignerResponse, status_code=status.HTTP_201_CREATED)
async def add_esigner(
    request_id: UUID,
    data: ESignerCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = ESignerService(db)
    data.request_id = request_id
    signer = ESigner(
        request_id=request_id,
        signer_id=data.signer_id,
        email=data.email,
        name=data.name,
        role=data.role,
        signing_order=data.signing_order,
        authentication_method=data.authentication_method,
        access_code=data.access_code,
        phone_number=data.phone_number,
        status="pending",
        tenant_id=tenant_context.tenant_id,
        created_by=current_user.id,
        extra_metadata=data.extra_metadata,
    )
    created = await service.signer_repo.create(signer)
    return ESignerResponse.model_validate(created)


@router.patch("/requests/{request_id}/signers/{signer_id}", response_model=ESignerResponse)
async def update_esigner(
    request_id: UUID,
    signer_id: UUID,
    data: ESignerUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = ESignerService(db)
    signer = await service.update_signer(signer_id, tenant_context.tenant_id, data, current_user.id)
    return ESignerResponse.model_validate(signer)


# ============================================================================
# E-Signature Provider Config Endpoints
# ============================================================================

@router.post("/provider-configs", response_model=ESignatureProviderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_config(
    data: ESignatureProviderConfigCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = ESignatureProviderConfigService(db)
    config = await service.create(data, tenant_context.tenant_id, current_user.id)
    return ESignatureProviderConfigResponse.model_validate(config)


@router.get("/provider-configs", response_model=ESignatureProviderConfigListResponse)
async def list_provider_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    provider: str | None = None,
    is_active: bool | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = ESignatureProviderConfigService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, provider, is_active, sort_by, sort_order
    )
    return ESignatureProviderConfigListResponse(
        items=[ESignatureProviderConfigResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/provider-configs/default", response_model=ESignatureProviderConfigResponse | None)
async def get_default_provider_config(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = ESignatureProviderConfigService(db)
    config = await service.get_default(tenant_context.tenant_id)
    if config:
        return ESignatureProviderConfigResponse.model_validate(config)
    return None


@router.get("/provider-configs/{config_id}", response_model=ESignatureProviderConfigDetailResponse)
async def get_provider_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = ESignatureProviderConfigService(db)
    config = await service.get_by_id(config_id, tenant_context.tenant_id)
    return ESignatureProviderConfigDetailResponse.model_validate(config)


@router.patch("/provider-configs/{config_id}", response_model=ESignatureProviderConfigResponse)
async def update_provider_config(
    config_id: UUID,
    data: ESignatureProviderConfigUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = ESignatureProviderConfigService(db)
    config = await service.update(config_id, tenant_context.tenant_id, data, current_user.id)
    return ESignatureProviderConfigResponse.model_validate(config)


@router.delete("/provider-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = ESignatureProviderConfigService(db)
    config = await service.get_by_id(config_id, tenant_context.tenant_id)
    await service.provider_config_repo.delete(config)


# ============================================================================
# E-Signature Webhook Endpoints
# ============================================================================

@router.post("/webhooks/{provider}", response_model=ESignatureWebhookEventResponse)
async def receive_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
):
    """Receive webhook from e-signature provider - no auth required as it's provider-initiated"""
    # Get tenant from request - in production, this would be derived from webhook URL or payload
    # For now, we require tenant_id in payload or header
    body = await request.json()
    
    # Extract tenant context - in production, this would be from subdomain or custom header
    tenant_id = body.get("tenant_id") or request.headers.get("X-Tenant-ID")
    if not tenant_id:
        # Try to find tenant from external_request_id
        external_request_id = body.get("envelopeId") or body.get("agreementId")
        if external_request_id:
            # Look up request to find tenant
            pass
    
    if not tenant_id:
        raise ValidationException(detail="Unable to determine tenant from webhook")
    
    from uuid import UUID
    tenant_uuid = UUID(tenant_id)
    
    # Create webhook event data
    webhook_data = ESignatureWebhookEventCreate(
        provider=provider,
        external_event_id=body.get("eventId", body.get("id", "")),
        event_type=body.get("event", body.get("type", "")),
        external_request_id=external_request_id,
        payload=body,
        idempotency_key=request.headers.get("X-Idempotency-Key"),
    )
    
    service = ESignatureWebhookService(db)
    event = await service.process_webhook(webhook_data, tenant_uuid)
    return ESignatureWebhookEventResponse.model_validate(event)


@router.get("/webhooks", response_model=ESignatureWebhookEventListResponse)
async def list_webhook_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    provider: str | None = None,
    processed: bool | None = None,
    external_request_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = ESignatureWebhookService(db)
    items, total = await service.get_webhook_events(
        tenant_context.tenant_id, page, page_size, provider, processed,
        external_request_id, date_from, date_to, sort_by, sort_order
    )
    return ESignatureWebhookEventListResponse(
        items=[ESignatureWebhookEventResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )