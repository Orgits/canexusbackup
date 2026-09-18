from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.engagement_documents.schemas import (
    EngagementDocumentCreate,
    EngagementDocumentDetailResponse,
    EngagementDocumentListResponse,
    EngagementDocumentResponse,
    EngagementDocumentSignerCreate,
    EngagementDocumentSignerDetailResponse,
    EngagementDocumentSignerResponse,
    EngagementDocumentSignerUpdate,
    EngagementDocumentTemplateCreate,
    EngagementDocumentTemplateDetailResponse,
    EngagementDocumentTemplateListResponse,
    EngagementDocumentTemplateResponse,
    EngagementDocumentTemplateUpdate,
    EngagementDocumentUpdate,
    EngagementDocumentVersionCreate,
    EngagementDocumentVersionResponse,
)
from app.modules.engagement_documents.service import (
    EngagementDocumentService,
    EngagementDocumentSignerService,
    EngagementDocumentTemplateService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/engagement-documents", tags=["Engagement Documents"])


# ============================================================================
# Engagement Document Endpoints
# ============================================================================

@router.post("", response_model=EngagementDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement_document(
    data: EngagementDocumentCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = EngagementDocumentService(db)
    doc = await service.create(data, tenant_context.tenant_id, current_user.id)
    return EngagementDocumentResponse.model_validate(doc)


@router.get("", response_model=EngagementDocumentListResponse)
async def list_engagement_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    client_id: UUID | None = None,
    matter_id: UUID | None = None,
    status: str | None = None,
    document_type: str | None = None,
    engagement_partner_id: UUID | None = None,
    engagement_manager_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = EngagementDocumentService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, client_id, matter_id,
        status, document_type, engagement_partner_id, engagement_manager_id,
        date_from, date_to, sort_by, sort_order
    )
    return EngagementDocumentListResponse(
        items=[EngagementDocumentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{doc_id}", response_model=EngagementDocumentDetailResponse)
async def get_engagement_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = EngagementDocumentService(db)
    doc = await service.get_by_id(doc_id, tenant_context.tenant_id)
    return EngagementDocumentDetailResponse.model_validate(doc)


@router.patch("/{doc_id}", response_model=EngagementDocumentResponse)
async def update_engagement_document(
    doc_id: UUID,
    data: EngagementDocumentUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = EngagementDocumentService(db)
    doc = await service.update(doc_id, tenant_context.tenant_id, data, current_user.id)
    return EngagementDocumentResponse.model_validate(doc)


@router.post("/{doc_id}/versions", response_model=EngagementDocumentVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_document_version(
    doc_id: UUID,
    data: EngagementDocumentVersionCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = EngagementDocumentService(db)
    data.engagement_document_id = doc_id
    version = await service.create_version(doc_id, tenant_context.tenant_id, data, current_user.id)
    return EngagementDocumentVersionResponse.model_validate(version)


@router.get("/{doc_id}/versions", response_model=list[EngagementDocumentVersionResponse])
async def list_document_versions(
    doc_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = EngagementDocumentService(db)
    versions = await service.get_versions(doc_id, tenant_context.tenant_id)
    return [EngagementDocumentVersionResponse.model_validate(v) for v in versions]


@router.post("/{doc_id}/submit-for-signature", response_model=EngagementDocumentResponse)
async def submit_for_signature(
    doc_id: UUID,
    signers: list[EngagementDocumentSignerCreate],
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = EngagementDocumentService(db)
    doc = await service.submit_for_signature(doc_id, tenant_context.tenant_id, signers, current_user.id)
    return EngagementDocumentResponse.model_validate(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = EngagementDocumentService(db)
    await service.delete(doc_id, tenant_context.tenant_id)


# ============================================================================
# Engagement Document Signer Endpoints
# ============================================================================

@router.get("/{doc_id}/signers", response_model=list[EngagementDocumentSignerDetailResponse])
async def list_document_signers(
    doc_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = EngagementDocumentSignerService(db)
    signers = await service.get_signers(doc_id, tenant_context.tenant_id)
    return [EngagementDocumentSignerDetailResponse.model_validate(s) for s in signers]


@router.post("/{doc_id}/signers/{signer_id}/sign", response_model=EngagementDocumentSignerResponse)
async def sign_engagement_document(
    doc_id: UUID,
    signer_id: UUID,
    signature_data: dict,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = EngagementDocumentSignerService(db)
    signer = await service.mark_signed(signer_id, tenant_context.tenant_id, current_user.id, signature_data)
    return EngagementDocumentSignerResponse.model_validate(signer)


@router.post("/{doc_id}/signers/{signer_id}/decline", response_model=EngagementDocumentSignerResponse)
async def decline_engagement_document(
    doc_id: UUID,
    signer_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = EngagementDocumentSignerService(db)
    signer = await service.decline(signer_id, tenant_context.tenant_id, current_user.id, reason)
    return EngagementDocumentSignerResponse.model_validate(signer)


@router.post("/{doc_id}/signers/{signer_id}/remind", response_model=EngagementDocumentSignerResponse)
async def remind_signer(
    doc_id: UUID,
    signer_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = EngagementDocumentSignerService(db)
    signer = await service.send_reminder(signer_id, tenant_context.tenant_id, current_user.id)
    return EngagementDocumentSignerResponse.model_validate(signer)


# ============================================================================
# Engagement Document Template Endpoints
# ============================================================================

@router.post("/templates", response_model=EngagementDocumentTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: EngagementDocumentTemplateCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_CREATE)),
):
    service = EngagementDocumentTemplateService(db)
    template = await service.create(data, tenant_context.tenant_id, current_user.id)
    return EngagementDocumentTemplateResponse.model_validate(template)


@router.get("/templates", response_model=EngagementDocumentTemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    document_type: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = EngagementDocumentTemplateService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, document_type, is_active, search, sort_by, sort_order
    )
    return EngagementDocumentTemplateListResponse(
        items=[EngagementDocumentTemplateResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/templates/by-type/{document_type}", response_model=list[EngagementDocumentTemplateResponse])
async def get_templates_by_type(
    document_type: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = EngagementDocumentTemplateService(db)
    templates = await service.get_by_type(document_type, tenant_context.tenant_id)
    return [EngagementDocumentTemplateResponse.model_validate(t) for t in templates]


@router.get("/templates/default/{document_type}", response_model=EngagementDocumentTemplateResponse | None)
async def get_default_template(
    document_type: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = EngagementDocumentTemplateService(db)
    template = await service.get_default(document_type, tenant_context.tenant_id)
    if template:
        return EngagementDocumentTemplateResponse.model_validate(template)
    return None


@router.get("/templates/{template_id}", response_model=EngagementDocumentTemplateDetailResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_READ)),
):
    service = EngagementDocumentTemplateService(db)
    template = await service.get_by_id(template_id, tenant_context.tenant_id)
    return EngagementDocumentTemplateDetailResponse.model_validate(template)


@router.patch("/templates/{template_id}", response_model=EngagementDocumentTemplateResponse)
async def update_template(
    template_id: UUID,
    data: EngagementDocumentTemplateUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_UPDATE)),
):
    service = EngagementDocumentTemplateService(db)
    template = await service.update(template_id, tenant_context.tenant_id, data, current_user.id)
    return EngagementDocumentTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TEMPLATES_DELETE)),
):
    service = EngagementDocumentTemplateService(db)
    await service.delete(template_id, tenant_context.tenant_id)