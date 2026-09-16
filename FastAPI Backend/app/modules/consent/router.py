from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.consent.schemas import (
    ConsentCreate,
    ConsentListResponse,
    ConsentResponse,
    ConsentTemplateCreate,
    ConsentTemplateListResponse,
    ConsentTemplateResponse,
    ConsentTemplateUpdate,
    ConsentUpdate,
)
from app.modules.consent.service import ConsentService
from app.modules.users.models import User

router = APIRouter(prefix="/consent", tags=["Consent"])


# Consent endpoints
@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def create_consent(
    data: ConsentCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_REQUESTS_CREATE)),
):
    service = ConsentService(db)
    consent = await service.create(data, tenant_context.tenant_id, current_user.id)
    return ConsentResponse.model_validate(consent)


@router.get("", response_model=ConsentListResponse)
async def list_consents(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    channel: str = None,
    status: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    sort_by: str = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = ConsentService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, client_id, channel, status, date_from, date_to, sort_by, sort_order
    )
    return ConsentListResponse(
        items=[ConsentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{consent_id}", response_model=ConsentResponse)
async def get_consent(
    consent_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_READ)),
):
    service = ConsentService(db)
    consent = await service.get_by_id(consent_id, tenant_context.tenant_id)
    return ConsentResponse.model_validate(consent)


@router.patch("/{consent_id}", response_model=ConsentResponse)
async def update_consent(
    consent_id: UUID,
    data: ConsentUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = ConsentService(db)
    consent = await service.update(consent_id, tenant_context.tenant_id, data, current_user.id)
    return ConsentResponse.model_validate(consent)


@router.post("/{consent_id}/withdraw", response_model=ConsentResponse)
async def withdraw_consent(
    consent_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.COMMUNICATIONS_UPDATE)),
):
    service = ConsentService(db)
    consent = await service.withdraw(consent_id, tenant_context.tenant_id, current_user.id)
    return ConsentResponse.model_validate(consent)


# Template endpoints
@router.post("/templates", response_model=ConsentTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_consent_template(
    data: ConsentTemplateCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_CREATE)),
):
    service = ConsentService(db)
    template = await service.create_template(data, tenant_context.tenant_id, current_user.id)
    return ConsentTemplateResponse.model_validate(template)


@router.get("/templates", response_model=ConsentTemplateListResponse)
async def list_consent_templates(
    page: int = 1,
    page_size: int = 20,
    channel: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = ConsentService(db)
    items, total = await service.get_all_templates(tenant_context.tenant_id, page, page_size, channel, is_active)
    return ConsentTemplateListResponse(
        items=[ConsentTemplateResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/templates/{template_id}", response_model=ConsentTemplateResponse)
async def get_consent_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = ConsentService(db)
    template = await service.get_template_by_id(template_id, tenant_context.tenant_id)
    return ConsentTemplateResponse.model_validate(template)


@router.patch("/templates/{template_id}", response_model=ConsentTemplateResponse)
async def update_consent_template(
    template_id: UUID,
    data: ConsentTemplateUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_UPDATE)),
):
    service = ConsentService(db)
    template = await service.update_template(template_id, tenant_context.tenant_id, data, current_user.id)
    return ConsentTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consent_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_DELETE)),
):
    service = ConsentService(db)
    await service.delete_template(template_id, tenant_context.tenant_id)


@router.post("/templates/{template_id}/set-default", response_model=ConsentResponse)
async def set_default_consent_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_UPDATE)),
):
    service = ConsentService(db)
    template = await service.set_default_template(template_id, tenant_context.tenant_id)
    return ConsentTemplateResponse.model_validate(template)