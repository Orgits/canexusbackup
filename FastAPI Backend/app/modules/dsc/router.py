from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.dsc.schemas import (
    DSCCertificateCreate,
    DSCCertificateDetailResponse,
    DSCCertificateListResponse,
    DSCCertificateResponse,
    DSCCertificateSignRequest,
    DSCCertificateUpdate,
    DSCExpiringSoonResponse,
    DSCRenewalRequestCreate,
    DSCRenewalRequestDetailResponse,
    DSCRenewalRequestListResponse,
    DSCRenewalRequestResponse,
    DSCRenewalRequestUpdate,
    DSCSigningLogListResponse,
    DSCSigningLogResponse,
)
from app.modules.dsc.service import DSCCertificateService, DSCRenewalService, DSCSigningService
from app.modules.users.models import User

router = APIRouter(prefix="/dsc", tags=["DSC (Digital Signature Certificates)"])


# ============================================================================
# DSC Certificate Endpoints
# ============================================================================

@router.post("/certificates", response_model=DSCCertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_dsc_certificate(
    data: DSCCertificateCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = DSCCertificateService(db)
    certificate = await service.create(data, tenant_context.tenant_id, current_user.id)
    return DSCCertificateResponse.model_validate(certificate)


@router.get("/certificates", response_model=DSCCertificateListResponse)
async def list_dsc_certificates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    holder_id: UUID | None = None,
    status: str | None = None,
    dsc_type: str | None = None,
    custodian_id: UUID | None = None,
    client_id: UUID | None = None,
    expiry_from: datetime | None = None,
    expiry_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = DSCCertificateService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, holder_id, status,
        dsc_type, custodian_id, client_id, expiry_from, expiry_to, sort_by, sort_order
    )
    return DSCCertificateListResponse(
        items=[DSCCertificateResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/certificates/expiring-soon", response_model=list[DSCExpiringSoonResponse])
async def get_expiring_certificates(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = DSCCertificateService(db)
    certificates = await service.get_expiring_soon(tenant_context.tenant_id, days)

    # Convert to response format with holder info
    result = []
    for cert in certificates:
        holder_name = cert.holder.full_name if cert.holder else "Unknown"
        holder_email = cert.holder.email if cert.holder else "Unknown"
        days_until = (cert.expiry_date - datetime.utcnow()).days
        result.append(DSCExpiringSoonResponse(
            certificate_id=cert.id,
            certificate_serial_number=cert.certificate_serial_number,
            holder_name=holder_name,
            holder_email=holder_email,
            expiry_date=cert.expiry_date,
            days_until_expiry=days_until,
            dsc_type=cert.dsc_type,
            status=cert.status,
        ))
    return result


@router.get("/certificates/{certificate_id}", response_model=DSCCertificateDetailResponse)
async def get_dsc_certificate(
    certificate_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = DSCCertificateService(db)
    certificate = await service.get_by_id(certificate_id, tenant_context.tenant_id)
    return DSCCertificateDetailResponse.model_validate(certificate)


@router.patch("/certificates/{certificate_id}", response_model=DSCCertificateResponse)
async def update_dsc_certificate(
    certificate_id: UUID,
    data: DSCCertificateUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = DSCCertificateService(db)
    certificate = await service.update(certificate_id, tenant_context.tenant_id, data, current_user.id)
    return DSCCertificateResponse.model_validate(certificate)


@router.post("/certificates/{certificate_id}/revoke", response_model=DSCCertificateResponse)
async def revoke_dsc_certificate(
    certificate_id: UUID,
    reason: str | None = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = DSCCertificateService(db)
    certificate = await service.revoke(certificate_id, tenant_context.tenant_id, current_user.id, reason)
    return DSCCertificateResponse.model_validate(certificate)


@router.delete("/certificates/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dsc_certificate(
    certificate_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = DSCCertificateService(db)
    await service.delete(certificate_id, tenant_context.tenant_id)


# ============================================================================
# DSC Signing Endpoints
# ============================================================================

@router.post("/certificates/{certificate_id}/sign", response_model=DSCSigningLogResponse, status_code=status.HTTP_201_CREATED)
async def sign_with_dsc(
    certificate_id: UUID,
    data: DSCCertificateSignRequest,
    request_id: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = DSCSigningService(db)
    data.certificate_id = certificate_id
    log = await service.sign_document(data, tenant_context.tenant_id, current_user.id, request_id)
    return DSCSigningLogResponse.model_validate(log)


@router.get("/signing-logs", response_model=DSCSigningLogListResponse)
async def list_signing_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    certificate_id: UUID | None = None,
    document_id: UUID | None = None,
    signed_by_id: UUID | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = DSCSigningService(db)
    items, total = await service.get_signing_logs(
        tenant_context.tenant_id, page, page_size, certificate_id, document_id,
        signed_by_id, status, date_from, date_to, sort_by, sort_order
    )
    return DSCSigningLogListResponse(
        items=[DSCSigningLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ============================================================================
# DSC Renewal Endpoints
# ============================================================================

@router.post("/certificates/{certificate_id}/renewal-requests", response_model=DSCRenewalRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_renewal(
    certificate_id: UUID,
    data: DSCRenewalRequestCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = DSCRenewalService(db)
    data.certificate_id = certificate_id
    renewal = await service.request_renewal(data, tenant_context.tenant_id, current_user.id)
    return DSCRenewalRequestResponse.model_validate(renewal)


@router.get("/renewal-requests", response_model=DSCRenewalRequestListResponse)
async def list_renewal_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    certificate_id: UUID | None = None,
    requested_by_id: UUID | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = DSCRenewalService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, certificate_id, requested_by_id,
        status, date_from, date_to, sort_by, sort_order
    )
    return DSCRenewalRequestListResponse(
        items=[DSCRenewalRequestResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/renewal-requests/{request_id}", response_model=DSCRenewalRequestDetailResponse)
async def get_renewal_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = DSCRenewalService(db)
    renewal = await service.get_by_id(request_id, tenant_context.tenant_id)
    return DSCRenewalRequestDetailResponse.model_validate(renewal)


@router.post("/renewal-requests/{request_id}/approve", response_model=DSCRenewalRequestResponse)
async def approve_renewal(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = DSCRenewalService(db)
    renewal = await service.approve(request_id, tenant_context.tenant_id, current_user.id)
    return DSCRenewalRequestResponse.model_validate(renewal)


@router.post("/renewal-requests/{request_id}/reject", response_model=DSCRenewalRequestResponse)
async def reject_renewal(
    request_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = DSCRenewalService(db)
    renewal = await service.reject(request_id, tenant_context.tenant_id, current_user.id, reason)
    return DSCRenewalRequestResponse.model_validate(renewal)


@router.delete("/renewal-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_renewal_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = DSCRenewalService(db)
    await service.delete(request_id, tenant_context.tenant_id)