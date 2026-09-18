from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.licenses.schemas import (
    LicenseCreate,
    LicenseDetailResponse,
    LicenseDocumentCreate,
    LicenseDocumentResponse,
    LicenseDocumentListResponse,
    LicenseExpiringSoonResponse,
    LicenseListResponse,
    LicenseRenewalRequestCreate,
    LicenseRenewalRequestDetailResponse,
    LicenseRenewalRequestListResponse,
    LicenseRenewalRequestResponse,
    LicenseRenewalRequestUpdate,
    LicenseResponse,
    LicenseUpdate,
)
from app.modules.licenses.service import LicenseDocumentService, LicenseRenewalService, LicenseService
from app.modules.users.models import User

router = APIRouter(prefix="/licenses", tags=["Licenses & Registrations"])


# ============================================================================
# License Endpoints
# ============================================================================

@router.post("", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
async def create_license(
    data: LicenseCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = LicenseService(db)
    license = await service.create(data, tenant_context.tenant_id, current_user.id)
    return LicenseResponse.model_validate(license)


@router.get("", response_model=LicenseListResponse)
async def list_licenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    professional_id: UUID | None = None,
    status: str | None = None,
    license_type: str | None = None,
    expiry_from: datetime | None = None,
    expiry_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = LicenseService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, professional_id, status,
        license_type, expiry_from, expiry_to, sort_by, sort_order
    )
    return LicenseListResponse(
        items=[LicenseResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/expiring-soon", response_model=list[LicenseExpiringSoonResponse])
async def get_expiring_licenses(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = LicenseService(db)
    licenses = await service.get_expiring_soon(tenant_context.tenant_id, days)

    result = []
    for lic in licenses:
        prof_name = lic.professional.full_name if lic.professional else "Unknown"
        prof_email = lic.professional.email if lic.professional else "Unknown"
        days_until = (lic.expiry_date - datetime.utcnow()).days
        result.append(LicenseExpiringSoonResponse(
            license_id=lic.id,
            license_number=lic.license_number,
            professional_name=prof_name,
            professional_email=prof_email,
            expiry_date=lic.expiry_date,
            days_until_expiry=days_until,
            license_type=lic.license_type,
            status=lic.status,
        ))
    return result


@router.get("/{license_id}", response_model=LicenseDetailResponse)
async def get_license(
    license_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = LicenseService(db)
    license = await service.get_by_id(license_id, tenant_context.tenant_id)
    return LicenseDetailResponse.model_validate(license)


@router.patch("/{license_id}", response_model=LicenseResponse)
async def update_license(
    license_id: UUID,
    data: LicenseUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = LicenseService(db)
    license = await service.update(license_id, tenant_context.tenant_id, data, current_user.id)
    return LicenseResponse.model_validate(license)


@router.post("/{license_id}/suspend", response_model=LicenseResponse)
async def suspend_license(
    license_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = LicenseService(db)
    license = await service.suspend(license_id, tenant_context.tenant_id, current_user.id, reason)
    return LicenseResponse.model_validate(license)


@router.post("/{license_id}/revoke", response_model=LicenseResponse)
async def revoke_license(
    license_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = LicenseService(db)
    license = await service.revoke(license_id, tenant_context.tenant_id, current_user.id, reason)
    return LicenseResponse.model_validate(license)


@router.delete("/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license(
    license_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = LicenseService(db)
    await service.delete(license_id, tenant_context.tenant_id)


# ============================================================================
# License Document Endpoints
# ============================================================================

@router.post("/{license_id}/documents", response_model=LicenseDocumentResponse, status_code=status.HTTP_201_CREATED)
async def attach_license_document(
    license_id: UUID,
    data: LicenseDocumentCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = LicenseDocumentService(db)
    data.license_id = license_id
    doc = await service.attach_document(data, tenant_context.tenant_id, current_user.id)
    return LicenseDocumentResponse.model_validate(doc)


@router.get("/{license_id}/documents", response_model=LicenseDocumentListResponse)
async def list_license_documents(
    license_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = LicenseDocumentService(db)
    items, total = await service.doc_repo.get_all(
        tenant_context.tenant_id, page, page_size, license_id=license_id
    )
    return LicenseDocumentListResponse(
        items=[LicenseDocumentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.delete("/{license_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_license_document(
    license_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = LicenseDocumentService(db)
    await service.detach_document(doc_id, tenant_context.tenant_id)


# ============================================================================
# License Renewal Endpoints
# ============================================================================

@router.post("/{license_id}/renewal-requests", response_model=LicenseRenewalRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_license_renewal(
    license_id: UUID,
    data: LicenseRenewalRequestCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = LicenseRenewalService(db)
    data.license_id = license_id
    renewal = await service.request_renewal(data, tenant_context.tenant_id, current_user.id)
    return LicenseRenewalRequestResponse.model_validate(renewal)


@router.get("/renewal-requests", response_model=LicenseRenewalRequestListResponse)
async def list_license_renewal_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    license_id: UUID | None = None,
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
    service = LicenseRenewalService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, license_id, requested_by_id,
        status, date_from, date_to, sort_by, sort_order
    )
    return LicenseRenewalRequestListResponse(
        items=[LicenseRenewalRequestResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/renewal-requests/{request_id}", response_model=LicenseRenewalRequestDetailResponse)
async def get_license_renewal_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = LicenseRenewalService(db)
    renewal = await service.get_by_id(request_id, tenant_context.tenant_id)
    return LicenseRenewalRequestDetailResponse.model_validate(renewal)


@router.post("/renewal-requests/{request_id}/approve", response_model=LicenseRenewalRequestResponse)
async def approve_license_renewal(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = LicenseRenewalService(db)
    renewal = await service.approve(request_id, tenant_context.tenant_id, current_user.id)
    return LicenseRenewalRequestResponse.model_validate(renewal)


@router.post("/renewal-requests/{request_id}/reject", response_model=LicenseRenewalRequestResponse)
async def reject_license_renewal(
    request_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = LicenseRenewalService(db)
    renewal = await service.reject(request_id, tenant_context.tenant_id, current_user.id, reason)
    return LicenseRenewalRequestResponse.model_validate(renewal)


@router.delete("/renewal-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license_renewal_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = LicenseRenewalService(db)
    await service.delete(request_id, tenant_context.tenant_id)