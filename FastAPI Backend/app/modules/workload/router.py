from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.security.dependencies import get_current_user
from app.core.tenancy import get_tenant_context
from app.modules.users.models import User
from app.modules.workload.models import WorkloadPeriod
from app.modules.workload.schemas import (
    TeamCapacityCreate,
    TeamCapacityResponse,
    TeamWorkloadResponse,
    UserAvailabilityCreate,
    UserAvailabilityResponse,
    UserWorkloadResponse,
    WorkloadDashboardResponse,
    WorkloadSnapshotResponse,
    WorkloadSummaryListResponse,
)
from app.modules.workload.service import WorkloadService

router = APIRouter(prefix="/workload", tags=["Workload & Capacity"])


def get_workload_service(db: AsyncSession = Depends(get_tenant_db_session)) -> WorkloadService:
    return WorkloadService(db)


# Dashboard endpoint
@router.get(
    "/dashboard",
    response_model=WorkloadDashboardResponse,
    summary="Get workload dashboard",
)
async def get_workload_dashboard(
    user_id: UUID | None = None,
    team_id: UUID | None = None,
    as_of_date: date | None = None,
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.read")),
):
    return await workload_service.get_workload_dashboard(
        tenant_context.tenant_id, user_id, team_id, as_of_date
    )


# User workload endpoint
@router.get(
    "/user/{user_id}",
    response_model=UserWorkloadResponse,
    summary="Get user workload",
)
async def get_user_workload(
    user_id: UUID,
    as_of_date: date | None = None,
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.read")),
):
    return await workload_service.calculate_user_workload(user_id, tenant_context.tenant_id, as_of_date)


# Team workload endpoint
@router.get(
    "/team/{team_id}",
    response_model=TeamWorkloadResponse,
    summary="Get team workload",
)
async def get_team_workload(
    team_id: UUID,
    as_of_date: date | None = None,
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.read")),
):
    return await workload_service.calculate_team_workload(team_id, tenant_context.tenant_id, as_of_date)


# User Availability endpoints
@router.post(
    "/availability",
    response_model=UserAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set user availability",
)
async def set_user_availability(
    data: UserAvailabilityCreate,
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.update")),
):
    return await workload_service.set_availability(
        data.user_id, data.date, data, tenant_context.tenant_id, current_user.id
    )


@router.post(
    "/availability/bulk",
    response_model=list[UserAvailabilityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk set user availability",
)
async def bulk_set_user_availability(
    user_id: UUID,
    availabilities: list[dict[str, Any]],
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.update")),
):
    return await workload_service.bulk_set_availability(user_id, tenant_context.tenant_id, availabilities, current_user.id)


@router.get(
    "/availability/user/{user_id}",
    response_model=list[UserAvailabilityResponse],
    summary="Get user availability for date range",
)
async def get_user_availability(
    user_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.read")),
):
    return await workload_service.get_user_availability(user_id, tenant_context.tenant_id, start_date, end_date)


@router.get(
    "/availability/team/{team_id}",
    response_model=list[UserAvailabilityResponse],
    summary="Get team availability for date range",
)
async def get_team_availability(
    team_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.read")),
):
    return await workload_service.get_team_availability(team_id, tenant_context.tenant_id, start_date, end_date)


# Team Capacity endpoints
@router.post(
    "/capacity",
    response_model=TeamCapacityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set team capacity",
)
async def set_team_capacity(
    data: TeamCapacityCreate,
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.update")),
):
    period_type = WorkloadPeriod(data.period_type)
    return await workload_service.set_team_capacity(
        data.team_id, period_type, data.period_start, data, tenant_context.tenant_id, current_user.id
    )


@router.get(
    "/capacity/team/{team_id}",
    response_model=list[TeamCapacityResponse],
    summary="Get team capacity",
)
async def get_team_capacity(
    team_id: UUID,
    period_type: str | None = None,
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.read")),
):
    period_type_enum = None
    if period_type:
        period_type_enum = WorkloadPeriod(period_type)
    return await workload_service.get_team_capacity(team_id, tenant_context.tenant_id, period_type_enum)


# Workload Snapshot endpoints
@router.post(
    "/snapshots/generate",
    response_model=list[WorkloadSnapshotResponse],
    summary="Generate workload snapshots",
)
async def generate_snapshots(
    snapshot_date: date | None = None,
    period_type: str = Query("daily", pattern="^(daily|weekly|monthly|quarterly)$"),
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.update")),
):
    period_type_enum = WorkloadPeriod(period_type)
    return await workload_service.generate_snapshots(
        tenant_context.tenant_id, snapshot_date, period_type_enum
    )


# Workload Summary endpoints
@router.get(
    "/summaries",
    response_model=WorkloadSummaryListResponse,
    summary="List workload summaries",
)
async def list_workload_summaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: UUID | None = None,
    team_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    workload_service: WorkloadService = Depends(get_workload_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workload.read")),
):
    items, total = await workload_service.repository.get_all_summaries(
        tenant_context.tenant_id, page, page_size, user_id, team_id, start_date, end_date
    )
    return WorkloadSummaryListResponse(items=items, total=total, page=page, page_size=page_size)


from typing import Any
