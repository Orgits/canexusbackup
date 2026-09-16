from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy.dependencies import get_current_tenant
from app.modules.compliance.schemas import (
    ComplianceApplicabilityCreate,
    ComplianceApplicabilityResponse,
    ComplianceApplicabilityUpdate,
    ComplianceCycleCreate,
    ComplianceCycleListResponse,
    ComplianceCycleResponse,
    ComplianceCycleUpdate,
    ComplianceTypeCreate,
    ComplianceTypeResponse,
    ComplianceTypeUpdate,
)
from app.modules.compliance.service import ComplianceService
from app.modules.users.models import User

router = APIRouter()


type_router = APIRouter(prefix="/types", tags=["Compliance Types"])


@type_router.post("", response_model=ComplianceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_compliance_type(
    data: ComplianceTypeCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_CREATE)),
):
    service = ComplianceService(db)
    compliance_type = await service.create_type(data, current_tenant.id, current_user.id)
    return ComplianceTypeResponse.model_validate(compliance_type)


@type_router.get("", response_model=list[ComplianceTypeResponse])
async def list_compliance_types(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    category: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_READ)),
):
    service = ComplianceService(db)
    items, total = await service.get_all_types(current_tenant.id, page, page_size, search, category, is_active)
    return [ComplianceTypeResponse.model_validate(item) for item in items]


@type_router.get("/{type_id}", response_model=ComplianceTypeResponse)
async def get_compliance_type(
    type_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_READ)),
):
    service = ComplianceService(db)
    compliance_type = await service.get_type_by_id(type_id, current_tenant.id)
    return ComplianceTypeResponse.model_validate(compliance_type)


@type_router.patch("/{type_id}", response_model=ComplianceTypeResponse)
async def update_compliance_type(
    type_id: UUID,
    data: ComplianceTypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_UPDATE)),
):
    service = ComplianceService(db)
    compliance_type = await service.update_type(type_id, current_tenant.id, data, current_user.id)
    return ComplianceTypeResponse.model_validate(compliance_type)


@type_router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compliance_type(
    type_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_DELETE)),
):
    service = ComplianceService(db)
    await service.delete_type(type_id, current_tenant.id)


@type_router.post("/initialize", response_model=list[ComplianceTypeResponse])
async def initialize_system_types(
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.ADMIN_FIRM_MANAGE)),
):
    service = ComplianceService(db)
    types = await service.initialize_system_types(current_tenant.id)
    return [ComplianceTypeResponse.model_validate(t) for t in types]


cycle_router = APIRouter(prefix="/cycles", tags=["Compliance Cycles"])


@cycle_router.post("", response_model=ComplianceCycleResponse, status_code=status.HTTP_201_CREATED)
async def create_compliance_cycle(
    data: ComplianceCycleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_CREATE)),
):
    service = ComplianceService(db)
    cycle = await service.create_cycle(data, current_tenant.id, current_user.id)
    return ComplianceCycleResponse.model_validate(cycle)


@cycle_router.get("", response_model=ComplianceCycleListResponse)
async def list_compliance_cycles(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    compliance_type_id: UUID = None,
    status: str = None,
    matter_id: UUID = None,
    due_date_from: datetime = None,
    due_date_to: datetime = None,
    period_start: datetime = None,
    period_end: datetime = None,
    assigned_user_id: UUID = None,
    sort_by: str = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_READ)),
):
    service = ComplianceService(db)
    items, total = await service.get_all_cycles(
        current_tenant.id, page, page_size, search, client_id, compliance_type_id,
        status, matter_id, due_date_from, due_date_to, period_start, period_end,
        assigned_user_id, sort_by, sort_order
    )
    return ComplianceCycleListResponse(
        items=[ComplianceCycleResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@cycle_router.get("/{cycle_id}", response_model=ComplianceCycleResponse)
async def get_compliance_cycle(
    cycle_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_READ)),
):
    service = ComplianceService(db)
    cycle = await service.get_cycle_by_id(cycle_id, current_tenant.id)
    return ComplianceCycleResponse.model_validate(cycle)


@cycle_router.patch("/{cycle_id}", response_model=ComplianceCycleResponse)
async def update_compliance_cycle(
    cycle_id: UUID,
    data: ComplianceCycleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_UPDATE)),
):
    service = ComplianceService(db)
    cycle = await service.update_cycle(cycle_id, current_tenant.id, data, current_user.id)
    return ComplianceCycleResponse.model_validate(cycle)


@cycle_router.delete("/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compliance_cycle(
    cycle_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_DELETE)),
):
    service = ComplianceService(db)
    await service.delete_cycle(cycle_id, current_tenant.id)


applicability_router = APIRouter(prefix="/applicability", tags=["Compliance Applicability"])


@applicability_router.post("", response_model=ComplianceApplicabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_applicability(
    data: ComplianceApplicabilityCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_CREATE)),
):
    service = ComplianceService(db)
    applicability = await service.create_applicability(data, current_tenant.id, current_user.id)
    return ComplianceApplicabilityResponse.model_validate(applicability)


@applicability_router.get("", response_model=list[ComplianceApplicabilityResponse])
async def list_applicability(
    client_id: UUID = None,
    compliance_type_id: UUID = None,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_READ)),
):
    service = ComplianceService(db)
    items = await service.get_all_applicability(current_tenant.id, client_id, compliance_type_id)
    return [ComplianceApplicabilityResponse.model_validate(item) for item in items]


@applicability_router.get("/{client_id}/{compliance_type_id}", response_model=ComplianceApplicabilityResponse)
async def get_applicability(
    client_id: UUID,
    compliance_type_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_READ)),
):
    service = ComplianceService(db)
    applicability = await service.get_applicability(client_id, compliance_type_id, current_tenant.id)
    return ComplianceApplicabilityResponse.model_validate(applicability)


@applicability_router.patch("/{client_id}/{compliance_type_id}", response_model=ComplianceApplicabilityResponse)
async def update_applicability(
    client_id: UUID,
    compliance_type_id: UUID,
    data: ComplianceApplicabilityUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_UPDATE)),
):
    service = ComplianceService(db)
    applicability = await service.update_applicability(client_id, compliance_type_id, current_tenant.id, data, current_user.id)
    return ComplianceApplicabilityResponse.model_validate(applicability)


@applicability_router.delete("/{client_id}/{compliance_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_applicability(
    client_id: UUID,
    compliance_type_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.COMPLIANCE_DELETE)),
):
    service = ComplianceService(db)
    await service.delete_applicability(client_id, compliance_type_id, current_tenant.id)


router.include_router(type_router)
router.include_router(cycle_router)
router.include_router(applicability_router)
