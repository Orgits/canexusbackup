from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import get_tenant_context
from app.core.security.dependencies import get_current_user
from app.core.permissions.dependencies import require_permission
from app.modules.tds.service import TDSService
from app.modules.tds.schemas import (
    TDSComplianceCycleCreate,
    TDSComplianceCycleUpdate,
    TDSComplianceCycleResponse,
    TDSComplianceCycleListResponse,
    TDSChallanCreate,
    TDSChallanUpdate,
    TDSChallanResponse,
    TDSChallanListResponse,
    TDSDeducteeCreate,
    TDSDeducteeUpdate,
    TDSDeducteeResponse,
    TDSDeducteeListResponse,
    TDSSummaryResponse,
)
from app.modules.users.models import User

router = APIRouter(prefix="/tds", tags=["TDS Compliance"])


def get_tds_service(db: AsyncSession = Depends(get_db)) -> TDSService:
    return TDSService(db)


# Summary endpoint
@router.get(
    "/summary",
    response_model=TDSSummaryResponse,
    summary="Get TDS summary",
)
async def get_tds_summary(
    financial_year: Optional[str] = None,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.read")),
):
    return await tds_service.get_summary(tenant_context.tenant_id, financial_year)


# TDS Compliance Cycle endpoints
@router.post(
    "/cycles",
    response_model=TDSComplianceCycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create TDS compliance cycle",
)
async def create_tds_cycle(
    data: TDSComplianceCycleCreate,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.create")),
):
    return await tds_service.create_cycle(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/cycles",
    response_model=TDSComplianceCycleListResponse,
    summary="List TDS compliance cycles",
)
async def list_tds_cycles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    client_id: Optional[UUID] = None,
    form_type: Optional[str] = None,
    financial_year: Optional[str] = None,
    quarter: Optional[str] = None,
    status: Optional[str] = None,
    matter_id: Optional[UUID] = None,
    due_date_from: Optional[datetime] = None,
    due_date_to: Optional[datetime] = None,
    assigned_user_id: Optional[UUID] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.read")),
):
    items, total = await tds_service.get_all_cycles(
        tenant_context.tenant_id,
        page,
        page_size,
        search,
        client_id,
        form_type,
        financial_year,
        quarter,
        status,
        matter_id,
        due_date_from,
        due_date_to,
        assigned_user_id,
        sort_by,
        sort_order,
    )
    return TDSComplianceCycleListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/cycles/{cycle_id}",
    response_model=TDSComplianceCycleResponse,
    summary="Get TDS compliance cycle by ID",
)
async def get_tds_cycle(
    cycle_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.read")),
):
    return await tds_service.get_cycle_with_details(cycle_id, tenant_context.tenant_id)


@router.patch(
    "/cycles/{cycle_id}",
    response_model=TDSComplianceCycleResponse,
    summary="Update TDS compliance cycle",
)
async def update_tds_cycle(
    cycle_id: UUID,
    data: TDSComplianceCycleUpdate,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.update")),
):
    return await tds_service.update_cycle(cycle_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/cycles/{cycle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete TDS compliance cycle",
)
async def delete_tds_cycle(
    cycle_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.delete")),
):
    await tds_service.delete_cycle(cycle_id, tenant_context.tenant_id)


# Status transition endpoints
@router.post(
    "/cycles/{cycle_id}/start-data-collection",
    response_model=TDSComplianceCycleResponse,
    summary="Start data collection",
)
async def start_tds_data_collection(
    cycle_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.transition")),
):
    return await tds_service.start_data_collection(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/start-validation",
    response_model=TDSComplianceCycleResponse,
    summary="Start validation",
)
async def start_tds_validation(
    cycle_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.transition")),
):
    return await tds_service.start_validation(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/ready-for-filing",
    response_model=TDSComplianceCycleResponse,
    summary="Mark ready for filing",
)
async def mark_tds_ready_for_filing(
    cycle_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.transition")),
):
    return await tds_service.mark_ready_for_filing(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/file",
    response_model=TDSComplianceCycleResponse,
    summary="Mark as filed",
)
async def mark_tds_filed(
    cycle_id: UUID,
    token_number: str = Query(..., description="Token number from portal"),
    acknowledgment_number: Optional[str] = Query(None, description="Acknowledgment number"),
    filing_date: Optional[datetime] = Query(None, description="Filing date"),
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.transition")),
):
    return await tds_service.mark_filed(
        cycle_id,
        tenant_context.tenant_id,
        current_user.id,
        token_number,
        acknowledgment_number,
        filing_date,
    )


@router.post(
    "/cycles/{cycle_id}/process",
    response_model=TDSComplianceCycleResponse,
    summary="Mark as processed",
)
async def mark_tds_processed(
    cycle_id: UUID,
    processed_date: Optional[datetime] = Query(None, description="Processed date"),
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.transition")),
):
    return await tds_service.mark_processed(cycle_id, tenant_context.tenant_id, current_user.id, processed_date)


# Challan endpoints
@router.post(
    "/cycles/{cycle_id}/challans",
    response_model=TDSChallanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add challan",
)
async def add_tds_challan(
    cycle_id: UUID,
    data: TDSChallanCreate,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.create")),
):
    return await tds_service.add_challan(cycle_id, data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/cycles/{cycle_id}/challans",
    response_model=List[TDSChallanResponse],
    summary="Get challans for cycle",
)
async def get_tds_challans(
    cycle_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.read")),
):
    await tds_service.get_cycle_by_id(cycle_id, tenant_context.tenant_id)
    return await tds_service.repository.get_challans_for_cycle(cycle_id, tenant_context.tenant_id)


@router.patch(
    "/challans/{challan_id}",
    response_model=TDSChallanResponse,
    summary="Update challan",
)
async def update_tds_challan(
    challan_id: UUID,
    data: TDSChallanUpdate,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.update")),
):
    return await tds_service.update_challan(challan_id, tenant_context.tenant_id, data, current_user.id)


@router.post(
    "/challans/{challan_id}/verify",
    response_model=TDSChallanResponse,
    summary="Verify challan",
)
async def verify_tds_challan(
    challan_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.update")),
):
    return await tds_service.verify_challan(challan_id, tenant_context.tenant_id, current_user.id)


@router.delete(
    "/challans/{challan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete challan",
)
async def delete_tds_challan(
    challan_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.delete")),
):
    await tds_service.delete_challan(challan_id, tenant_context.tenant_id)


# Deductee endpoints
@router.post(
    "/cycles/{cycle_id}/deductees",
    response_model=TDSDeducteeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add deductee",
)
async def add_tds_deductee(
    cycle_id: UUID,
    data: TDSDeducteeCreate,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.create")),
):
    return await tds_service.add_deductee(cycle_id, data, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/deductees/bulk",
    response_model=List[TDSDeducteeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add deductees",
)
async def bulk_add_tds_deductees(
    cycle_id: UUID,
    data_list: List[TDSDeducteeCreate],
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.create")),
):
    return await tds_service.bulk_add_deductees(cycle_id, data_list, tenant_context.tenant_id, current_user.id)


@router.get(
    "/cycles/{cycle_id}/deductees",
    response_model=TDSDeducteeListResponse,
    summary="Get deductees for cycle",
)
async def get_tds_deductees(
    cycle_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.read")),
):
    await tds_service.get_cycle_by_id(cycle_id, tenant_context.tenant_id)
    items, total = await tds_service.get_deductees_for_cycle(cycle_id, tenant_context.tenant_id, page, page_size)
    return TDSDeducteeListResponse(items=items, total=total, page=page, page_size=page_size)


@router.patch(
    "/deductees/{deductee_id}",
    response_model=TDSDeducteeResponse,
    summary="Update deductee",
)
async def update_tds_deductee(
    deductee_id: UUID,
    data: TDSDeducteeUpdate,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.update")),
):
    return await tds_service.update_deductee(deductee_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/deductees/{deductee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete deductee",
)
async def delete_tds_deductee(
    deductee_id: UUID,
    tds_service: TDSService = Depends(get_tds_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("tds.delete")),
):
    await tds_service.delete_deductee(deductee_id, tenant_context.tenant_id)