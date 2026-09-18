from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.tenancy import get_tenant_context, TenantContext
from app.modules.reporting.schemas import (
    ReportDefinitionCreate,
    ReportDefinitionUpdate,
    ReportDefinitionResponse,
    ReportDefinitionListResponse,
    ReportParameterCreate,
    ReportParameterUpdate,
    ReportParameterResponse,
    ReportJobCreate,
    ReportJobUpdate,
    ReportJobResponse,
    ReportJobListResponse,
    ReportOutputResponse,
    ReportScheduleCreate,
    ReportScheduleUpdate,
    ReportScheduleResponse,
    ReportScheduleListResponse,
    DashboardWidgetCreate,
    DashboardWidgetUpdate,
    DashboardWidgetResponse,
    DashboardWidgetListResponse,
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportDownloadResponse,
)
from app.modules.reporting.service import ReportingService
from app.modules.reporting.models import ReportStatus, ReportFormat

router = APIRouter()


async def get_reporting_service(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> ReportingService:
    from app.modules.users.models import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == tenant_context.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    return ReportingService(db, tenant_context.tenant_id, user.id)


@router.post("/definitions", response_model=ReportDefinitionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("report.create"))])
async def create_report_definition(
    data: ReportDefinitionCreate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.create_report_definition(data)


@router.get("/definitions", response_model=list[ReportDefinitionListResponse], dependencies=[Depends(require_permission("report.read"))])
async def list_report_definitions(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_system: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    service: ReportingService = Depends(get_reporting_service),
):
    definitions, _ = await service.list_report_definitions(
        category=category,
        is_active=is_active,
        is_system=is_system,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return definitions


@router.get("/definitions/{definition_id}", response_model=ReportDefinitionResponse, dependencies=[Depends(require_permission("report.read"))])
async def get_report_definition(
    definition_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.get_report_definition(definition_id)


@router.patch("/definitions/{definition_id}", response_model=ReportDefinitionResponse, dependencies=[Depends(require_permission("report.update"))])
async def update_report_definition(
    definition_id: UUID,
    data: ReportDefinitionUpdate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.update_report_definition(definition_id, data)


@router.delete("/definitions/{definition_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("report.delete"))])
async def delete_report_definition(
    definition_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    await service.delete_report_definition(definition_id)


@router.post("/definitions/{definition_id}/parameters", response_model=ReportParameterResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("report.create"))])
async def create_report_parameter(
    definition_id: UUID,
    data: ReportParameterCreate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.create_report_parameter(definition_id, data)


@router.patch("/parameters/{parameter_id}", response_model=ReportParameterResponse, dependencies=[Depends(require_permission("report.update"))])
async def update_report_parameter(
    parameter_id: UUID,
    data: ReportParameterUpdate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.update_report_parameter(parameter_id, data)


@router.delete("/parameters/{parameter_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("report.delete"))])
async def delete_report_parameter(
    parameter_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    await service.delete_report_parameter(parameter_id)


@router.post("/generate", response_model=ReportGenerateResponse, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_permission("report.generate"))])
async def generate_report(
    data: ReportGenerateRequest,
    service: ReportingService = Depends(get_reporting_service),
):
    job = await service.generate_report(data)
    return ReportGenerateResponse(
        job_id=job.id,
        status=job.status,
        message="Report generation queued",
    )


@router.get("/jobs", response_model=list[ReportJobListResponse], dependencies=[Depends(require_permission("report.read"))])
async def list_report_jobs(
    report_definition_id: Optional[UUID] = Query(None),
    status: Optional[ReportStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    service: ReportingService = Depends(get_reporting_service),
):
    jobs, _ = await service.list_report_jobs(
        report_definition_id=report_definition_id,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return jobs


@router.get("/jobs/{job_id}", response_model=ReportJobResponse, dependencies=[Depends(require_permission("report.read"))])
async def get_report_job(
    job_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.get_report_job(job_id)


@router.patch("/jobs/{job_id}", response_model=ReportJobResponse, dependencies=[Depends(require_permission("report.generate"))])
async def update_report_job(
    job_id: UUID,
    data: ReportJobUpdate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.update_report_job(job_id, data)


@router.get("/jobs/{job_id}/outputs", response_model=list[ReportOutputResponse], dependencies=[Depends(require_permission("report.read"))])
async def list_report_outputs(
    job_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    job = await service.get_report_job(job_id)
    from app.modules.reporting.repository import ReportingRepository
    repository = ReportingRepository(service.db, service.tenant_id)
    return await repository.list_report_outputs(job_id)


@router.get("/outputs/{output_id}", response_model=ReportOutputResponse, dependencies=[Depends(require_permission("report.read"))])
async def get_report_output(
    output_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.get_report_output(output_id)


@router.get("/outputs/{output_id}/download", response_model=ReportDownloadResponse, dependencies=[Depends(require_permission("report.read"))])
async def download_report_output(
    output_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    download_url, expires_at = await service.download_report_output(output_id)
    output = await service.get_report_output(output_id)
    return ReportDownloadResponse(
        download_url=download_url,
        expires_at=expires_at,
        format=output.format,
        size_bytes=output.size_bytes,
        checksum=output.checksum,
    )


@router.post("/schedules", response_model=ReportScheduleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("report_schedule.create"))])
async def create_report_schedule(
    data: ReportScheduleCreate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.create_report_schedule(data)


@router.get("/schedules", response_model=list[ReportScheduleListResponse], dependencies=[Depends(require_permission("report_schedule.read"))])
async def list_report_schedules(
    report_definition_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ReportingService = Depends(get_reporting_service),
):
    schedules, _ = await service.list_report_schedules(
        report_definition_id=report_definition_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return schedules


@router.get("/schedules/{schedule_id}", response_model=ReportScheduleResponse, dependencies=[Depends(require_permission("report_schedule.read"))])
async def get_report_schedule(
    schedule_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.get_report_schedule(schedule_id)


@router.patch("/schedules/{schedule_id}", response_model=ReportScheduleResponse, dependencies=[Depends(require_permission("report_schedule.update"))])
async def update_report_schedule(
    schedule_id: UUID,
    data: ReportScheduleUpdate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.update_report_schedule(schedule_id, data)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("report_schedule.delete"))])
async def delete_report_schedule(
    schedule_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    await service.delete_report_schedule(schedule_id)


@router.post("/widgets", response_model=DashboardWidgetResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("analytics.read"))])
async def create_dashboard_widget(
    data: DashboardWidgetCreate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.create_dashboard_widget(data)


@router.get("/widgets", response_model=list[DashboardWidgetListResponse], dependencies=[Depends(require_permission("analytics.read"))])
async def list_dashboard_widgets(
    widget_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_default: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ReportingService = Depends(get_reporting_service),
):
    widgets, _ = await service.list_dashboard_widgets(
        widget_type=widget_type,
        is_active=is_active,
        is_default=is_default,
        page=page,
        page_size=page_size,
    )
    return widgets


@router.get("/widgets/default", response_model=list[DashboardWidgetResponse], dependencies=[Depends(require_permission("analytics.read"))])
async def get_default_widgets(
    widget_type: Optional[str] = Query(None),
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.get_default_widgets(widget_type=widget_type)


@router.get("/widgets/{widget_id}", response_model=DashboardWidgetResponse, dependencies=[Depends(require_permission("analytics.read"))])
async def get_dashboard_widget(
    widget_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.get_dashboard_widget(widget_id)


@router.patch("/widgets/{widget_id}", response_model=DashboardWidgetResponse, dependencies=[Depends(require_permission("analytics.read"))])
async def update_dashboard_widget(
    widget_id: UUID,
    data: DashboardWidgetUpdate,
    service: ReportingService = Depends(get_reporting_service),
):
    return await service.update_dashboard_widget(widget_id, data)


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("analytics.read"))])
async def delete_dashboard_widget(
    widget_id: UUID,
    service: ReportingService = Depends(get_reporting_service),
):
    await service.delete_dashboard_widget(widget_id)