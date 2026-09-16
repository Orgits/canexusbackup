from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions.dependencies import require_permission
from app.core.security.dependencies import get_current_user
from app.core.tenancy import get_tenant_context
from app.modules.mca_roc.schemas import (
    MCAFilingConfigCreate,
    MCAFilingConfigResponse,
    MCAFilingConfigUpdate,
    MCAFilingCycleCreate,
    MCAFilingCycleListResponse,
    MCAFilingCycleResponse,
    MCAFilingCycleUpdate,
    MCASummaryResponse,
)
from app.modules.mca_roc.service import MCAService
from app.modules.users.models import User

router = APIRouter(prefix="/mca-roc", tags=["MCA/ROC Compliance"])


def get_mca_service(db: AsyncSession = Depends(get_db)) -> MCAService:
    return MCAService(db)


# Summary endpoint
@router.get(
    "/summary",
    response_model=MCASummaryResponse,
    summary="Get MCA/ROC summary",
)
async def get_mca_summary(
    financial_year: str | None = None,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.read")),
):
    return await mca_service.get_summary(tenant_context.tenant_id, financial_year)


# MCA Filing Config endpoints
@router.post(
    "/configs",
    response_model=MCAFilingConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create MCA filing config",
)
async def create_mca_config(
    data: MCAFilingConfigCreate,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.create")),
):
    return await mca_service.create_config(data, tenant_context.tenant_id, current_user.id)


@router.post(
    "/configs/initialize",
    response_model=list[MCAFilingConfigResponse],
    summary="Initialize system MCA filing configs",
)
async def initialize_mca_configs(
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.create")),
):
    return await mca_service.initialize_system_configs(tenant_context.tenant_id)


@router.get(
    "/configs",
    response_model=list[MCAFilingConfigResponse],
    summary="List MCA filing configs",
)
async def list_mca_configs(
    entity_type: str | None = None,
    filing_category: str | None = None,
    is_active: bool | None = None,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.read")),
):
    return await mca_service.get_all_configs(
        tenant_context.tenant_id, entity_type, filing_category, is_active
    )


@router.get(
    "/configs/{config_id}",
    response_model=MCAFilingConfigResponse,
    summary="Get MCA filing config by ID",
)
async def get_mca_config(
    config_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.read")),
):
    return await mca_service.get_config_by_id(config_id, tenant_context.tenant_id)


@router.patch(
    "/configs/{config_id}",
    response_model=MCAFilingConfigResponse,
    summary="Update MCA filing config",
)
async def update_mca_config(
    config_id: UUID,
    data: MCAFilingConfigUpdate,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.update")),
):
    return await mca_service.update_config(config_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/configs/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete MCA filing config",
)
async def delete_mca_config(
    config_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.delete")),
):
    await mca_service.delete_config(config_id, tenant_context.tenant_id)


# MCA Filing Cycle endpoints
@router.post(
    "/cycles",
    response_model=MCAFilingCycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create MCA filing cycle",
)
async def create_mca_cycle(
    data: MCAFilingCycleCreate,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.create")),
):
    return await mca_service.create_cycle(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/cycles",
    response_model=MCAFilingCycleListResponse,
    summary="List MCA filing cycles",
)
async def list_mca_cycles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    client_id: UUID | None = None,
    entity_type: str | None = None,
    filing_type: str | None = None,
    filing_category: str | None = None,
    financial_year: str | None = None,
    status: str | None = None,
    matter_id: UUID | None = None,
    due_date_from: datetime | None = None,
    due_date_to: datetime | None = None,
    assigned_user_id: UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.read")),
):
    items, total = await mca_service.get_all_cycles(
        tenant_context.tenant_id,
        page,
        page_size,
        search,
        client_id,
        entity_type,
        filing_type,
        filing_category,
        financial_year,
        status,
        matter_id,
        due_date_from,
        due_date_to,
        assigned_user_id,
        sort_by,
        sort_order,
    )
    return MCAFilingCycleListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/cycles/{cycle_id}",
    response_model=MCAFilingCycleResponse,
    summary="Get MCA filing cycle by ID",
)
async def get_mca_cycle(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.read")),
):
    return await mca_service.get_cycle_by_id(cycle_id, tenant_context.tenant_id)


@router.patch(
    "/cycles/{cycle_id}",
    response_model=MCAFilingCycleResponse,
    summary="Update MCA filing cycle",
)
async def update_mca_cycle(
    cycle_id: UUID,
    data: MCAFilingCycleUpdate,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.update")),
):
    return await mca_service.update_cycle(cycle_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/cycles/{cycle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete MCA filing cycle",
)
async def delete_mca_cycle(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.delete")),
):
    await mca_service.delete_cycle(cycle_id, tenant_context.tenant_id)


# Status transition endpoints
@router.post(
    "/cycles/{cycle_id}/start-document-collection",
    response_model=MCAFilingCycleResponse,
    summary="Start document collection",
)
async def start_mca_document_collection(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.start_document_collection(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/start-preparation",
    response_model=MCAFilingCycleResponse,
    summary="Start preparation",
)
async def start_mca_preparation(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.start_preparation(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/start-review",
    response_model=MCAFilingCycleResponse,
    summary="Start review",
)
async def start_mca_review(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.start_review(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/board-approval",
    response_model=MCAFilingCycleResponse,
    summary="Complete board approval",
)
async def complete_mca_board_approval(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.complete_board_approval(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/agm",
    response_model=MCAFilingCycleResponse,
    summary="Complete AGM",
)
async def complete_mca_agm(
    cycle_id: UUID,
    agm_date: datetime = Query(..., description="AGM date"),
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.complete_agm(cycle_id, tenant_context.tenant_id, current_user.id, agm_date)


@router.post(
    "/cycles/{cycle_id}/ready-for-filing",
    response_model=MCAFilingCycleResponse,
    summary="Mark ready for filing",
)
async def mark_mca_ready_for_filing(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.mark_ready_for_filing(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/file",
    response_model=MCAFilingCycleResponse,
    summary="Mark as filed",
)
async def mark_mca_filed(
    cycle_id: UUID,
    srn: str = Query(..., description="SRN from MCA portal"),
    acknowledgment_number: str | None = Query(None, description="Acknowledgment number"),
    filing_date: datetime | None = Query(None, description="Filing date"),
    challan_amount: float = Query(0, ge=0, description="Challan amount"),
    additional_fee: float = Query(0, ge=0, description="Additional fee"),
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.mark_filed(
        cycle_id,
        tenant_context.tenant_id,
        current_user.id,
        srn,
        acknowledgment_number,
        filing_date,
        challan_amount,
        additional_fee,
    )


@router.post(
    "/cycles/{cycle_id}/approve",
    response_model=MCAFilingCycleResponse,
    summary="Mark as approved",
)
async def mark_mca_approved(
    cycle_id: UUID,
    approval_date: datetime | None = Query(None, description="Approval date"),
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.mark_approved(cycle_id, tenant_context.tenant_id, current_user.id, approval_date)


@router.post(
    "/cycles/{cycle_id}/reject",
    response_model=MCAFilingCycleResponse,
    summary="Mark as rejected",
)
async def mark_mca_rejected(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.mark_rejected(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/defective",
    response_model=MCAFilingCycleResponse,
    summary="Mark as defective",
)
async def mark_mca_defective(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.mark_defective(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/resubmit",
    response_model=MCAFilingCycleResponse,
    summary="Mark as resubmitted",
)
async def mark_mca_resubmitted(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.mark_resubmitted(cycle_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/cycles/{cycle_id}/complete",
    response_model=MCAFilingCycleResponse,
    summary="Mark as completed",
)
async def mark_mca_completed(
    cycle_id: UUID,
    mca_service: MCAService = Depends(get_mca_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("mca_roc.transition")),
):
    return await mca_service.mark_completed(cycle_id, tenant_context.tenant_id, current_user.id)
