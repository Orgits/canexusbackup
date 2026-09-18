from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.udin.schemas import (
    UDINGenerationRequest,
    UDINGenerationResponse,
    UDINRecordCreate,
    UDINRecordDetailResponse,
    UDINRecordListResponse,
    UDINRecordResponse,
    UDINRecordUpdate,
    UDINVerificationLogListResponse,
    UDINVerificationLogResponse,
    UDINVerificationRequest,
    UDINVerificationResponse,
)
from app.modules.udin.service import UDINService
from app.modules.users.models import User

router = APIRouter(prefix="/udin", tags=["UDIN (Unique Document Identification Number)"])


# ============================================================================
# UDIN Record Endpoints
# ============================================================================

@router.post("/generate", response_model=UDINGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_udin(
    data: UDINGenerationRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = UDINService(db)
    record = await service.generate_udin(data, tenant_context.tenant_id, current_user.id)
    return UDINGenerationResponse(
        udin=record.udin,
        generated_at=record.generated_at,
        record_id=record.id,
    )


@router.post("/records", response_model=UDINRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_udin_record(
    data: UDINRecordCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_CREATE)),
):
    service = UDINService(db)
    # For manual creation, we still generate UDIN
    udin_record = UDINGenerationRequest(
        professional_id=data.professional_id,
        financial_year=data.financial_year,
        quarter=data.quarter,
        form_type=data.form_type,
        client_id=data.client_id,
        matter_id=data.matter_id,
        document_id=data.document_id,
        description=data.description,
        external_reference=data.external_reference,
        extra_metadata=data.extra_metadata,
    )
    record = await service.generate_udin(udin_record, tenant_context.tenant_id, current_user.id)
    return UDINRecordResponse.model_validate(record)


@router.get("/records", response_model=UDINRecordListResponse)
async def list_udin_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    professional_id: UUID | None = None,
    status: str | None = None,
    client_id: UUID | None = None,
    matter_id: UUID | None = None,
    document_id: UUID | None = None,
    financial_year: str | None = None,
    quarter: str | None = None,
    form_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = UDINService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, professional_id, status,
        client_id, matter_id, document_id, financial_year, quarter, form_type,
        date_from, date_to, sort_by, sort_order
    )
    return UDINRecordListResponse(
        items=[UDINRecordResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/records/{record_id}", response_model=UDINRecordDetailResponse)
async def get_udin_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = UDINService(db)
    record = await service.get_by_id(record_id, tenant_context.tenant_id)
    return UDINRecordDetailResponse.model_validate(record)


@router.get("/lookup/{udin}", response_model=UDINRecordDetailResponse)
async def lookup_udin(
    udin: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = UDINService(db)
    record = await service.get_by_udin(udin, tenant_context.tenant_id)
    return UDINRecordDetailResponse.model_validate(record)


@router.patch("/records/{record_id}", response_model=UDINRecordResponse)
async def update_udin_record(
    record_id: UUID,
    data: UDINRecordUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = UDINService(db)
    record = await service.update(record_id, tenant_context.tenant_id, data, current_user.id)
    return UDINRecordResponse.model_validate(record)


@router.post("/records/{record_id}/cancel", response_model=UDINRecordResponse)
async def cancel_udin_record(
    record_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_UPDATE)),
):
    service = UDINService(db)
    record = await service.cancel_udin(record_id, tenant_context.tenant_id, current_user.id, reason)
    return UDINRecordResponse.model_validate(record)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_udin_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_DELETE)),
):
    service = UDINService(db)
    await service.delete(record_id, tenant_context.tenant_id)


# ============================================================================
# UDIN Verification Endpoints
# ============================================================================

@router.post("/verify", response_model=UDINVerificationResponse)
async def verify_udin(
    data: UDINVerificationRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = UDINService(db)
    log = await service.verify_udin(data, tenant_context.tenant_id, current_user.id)

    # Build response
    record = None
    if log.udin_record_id:
        record = await service.get_by_id(log.udin_record_id, tenant_context.tenant_id)

    return UDINVerificationResponse(
        udin=data.udin,
        status=record.status if record else "not_found",
        verified=log.result == "verified",
        verified_at=log.created_at if log.result == "verified" else None,
        professional_name=record.professional.full_name if record and record.professional else None,
        client_name=record.client.name if record and record.client else None,
        matter_name=record.matter.matter_name if record and record.matter else None,
        document_name=record.document.filename if record and record.document else None,
        financial_year=record.financial_year if record else None,
        form_type=record.form_type if record else None,
        external_response=log.external_response,
    )


@router.get("/verification-logs", response_model=UDINVerificationLogListResponse)
async def list_verification_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    udin_record_id: UUID | None = None,
    verified_by_id: UUID | None = None,
    result: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.REGISTER_READ)),
):
    service = UDINService(db)
    items, total = await service.get_verification_logs(
        tenant_context.tenant_id, page, page_size, udin_record_id, verified_by_id,
        result, date_from, date_to, sort_by, sort_order
    )
    return UDINVerificationLogListResponse(
        items=[UDINVerificationLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )