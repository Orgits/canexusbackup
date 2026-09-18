from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database.base import TenantBaseModelMixin
from app.modules.reporting.models import (
    ReportDefinition,
    ReportParameter,
    ReportJob,
    ReportOutput,
    ReportSchedule,
    DashboardWidget,
    ReportStatus,
    ReportFormat,
)


class ReportingRepository:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self, model):
        return select(model).where(model.tenant_id == self.tenant_id)

    async def get_report_definition(self, definition_id: UUID) -> Optional[ReportDefinition]:
        query = self._base_query(ReportDefinition).where(ReportDefinition.id == definition_id).options(
            selectinload(ReportDefinition.parameters)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_report_definition_by_name(self, name: str) -> Optional[ReportDefinition]:
        query = self._base_query(ReportDefinition).where(ReportDefinition.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_report_definitions(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_system: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ReportDefinition], int]:
        query = self._base_query(ReportDefinition).options(selectinload(ReportDefinition.parameters))

        if category:
            query = query.where(ReportDefinition.category == category)
        if is_active is not None:
            query = query.where(ReportDefinition.is_active == is_active)
        if is_system is not None:
            query = query.where(ReportDefinition.is_system == is_system)
        if search:
            query = query.where(
                or_(
                    ReportDefinition.name.ilike(f"%{search}%"),
                    ReportDefinition.description.ilike(f"%{search}%"),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # Sorting
        sort_column = getattr(ReportDefinition, sort_by, ReportDefinition.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_report_definition(self, definition: ReportDefinition) -> ReportDefinition:
        self.db.add(definition)
        await self.db.flush()
        await self.db.refresh(definition)
        return definition

    async def update_report_definition(self, definition: ReportDefinition) -> ReportDefinition:
        await self.db.flush()
        await self.db.refresh(definition)
        return definition

    async def delete_report_definition(self, definition: ReportDefinition) -> bool:
        await self.db.delete(definition)
        await self.db.flush()
        return True

    async def get_report_parameter(self, parameter_id: UUID) -> Optional[ReportParameter]:
        query = self._base_query(ReportParameter).where(ReportParameter.id == parameter_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_report_parameters(self, definition_id: UUID) -> list[ReportParameter]:
        query = self._base_query(ReportParameter).where(ReportParameter.report_definition_id == definition_id).order_by(ReportParameter.order)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_report_parameter(self, parameter: ReportParameter) -> ReportParameter:
        self.db.add(parameter)
        await self.db.flush()
        await self.db.refresh(parameter)
        return parameter

    async def update_report_parameter(self, parameter: ReportParameter) -> ReportParameter:
        await self.db.flush()
        await self.db.refresh(parameter)
        return parameter

    async def delete_report_parameter(self, parameter: ReportParameter) -> bool:
        await self.db.delete(parameter)
        await self.db.flush()
        return True

    async def get_report_job(self, job_id: UUID) -> Optional[ReportJob]:
        query = self._base_query(ReportJob).where(ReportJob.id == job_id).options(
            selectinload(ReportJob.report_definition),
            selectinload(ReportJob.outputs)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_report_job_by_idempotency_key(self, idempotency_key: str) -> Optional[ReportJob]:
        query = self._base_query(ReportJob).where(ReportJob.idempotency_key == idempotency_key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_report_jobs(
        self,
        report_definition_id: Optional[UUID] = None,
        status: Optional[ReportStatus] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ReportJob], int]:
        query = self._base_query(ReportJob).options(selectinload(ReportJob.report_definition))

        if report_definition_id:
            query = query.where(ReportJob.report_definition_id == report_definition_id)
        if status:
            query = query.where(ReportJob.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        sort_column = getattr(ReportJob, sort_by, ReportJob.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_report_job(self, job: ReportJob) -> ReportJob:
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def update_report_job(self, job: ReportJob) -> ReportJob:
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_report_output(self, output_id: UUID) -> Optional[ReportOutput]:
        query = self._base_query(ReportOutput).where(ReportOutput.id == output_id).options(
            selectinload(ReportOutput.job)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_report_outputs(self, job_id: UUID) -> list[ReportOutput]:
        query = self._base_query(ReportOutput).where(ReportOutput.job_id == job_id).order_by(desc(ReportOutput.created_at))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_report_output(self, output: ReportOutput) -> ReportOutput:
        self.db.add(output)
        await self.db.flush()
        await self.db.refresh(output)
        return output

    async def get_report_schedule(self, schedule_id: UUID) -> Optional[ReportSchedule]:
        query = self._base_query(ReportSchedule).where(ReportSchedule.id == schedule_id).options(
            selectinload(ReportSchedule.report_definition)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_report_schedules(
        self,
        report_definition_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReportSchedule], int]:
        query = self._base_query(ReportSchedule).options(selectinload(ReportSchedule.report_definition))

        if report_definition_id:
            query = query.where(ReportSchedule.report_definition_id == report_definition_id)
        if is_active is not None:
            query = query.where(ReportSchedule.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = query.order_by(desc(ReportSchedule.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_due_schedules(self, before: datetime) -> list[ReportSchedule]:
        query = self._base_query(ReportSchedule).where(
            and_(
                ReportSchedule.is_active == True,
                ReportSchedule.next_run_at <= before,
            )
        ).options(selectinload(ReportSchedule.report_definition))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_report_schedule(self, schedule: ReportSchedule) -> ReportSchedule:
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    async def update_report_schedule(self, schedule: ReportSchedule) -> ReportSchedule:
        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    async def delete_report_schedule(self, schedule: ReportSchedule) -> bool:
        await self.db.delete(schedule)
        await self.db.flush()
        return True

    async def get_dashboard_widget(self, widget_id: UUID) -> Optional[DashboardWidget]:
        query = self._base_query(DashboardWidget).where(DashboardWidget.id == widget_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_dashboard_widgets(
        self,
        widget_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DashboardWidget], int]:
        query = self._base_query(DashboardWidget)

        if widget_type:
            query = query.where(DashboardWidget.widget_type == widget_type)
        if is_active is not None:
            query = query.where(DashboardWidget.is_active == is_active)
        if is_default is not None:
            query = query.where(DashboardWidget.is_default == is_default)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = query.order_by(DashboardWidget.order, desc(DashboardWidget.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_default_widgets(self, widget_type: Optional[str] = None) -> list[DashboardWidget]:
        query = self._base_query(DashboardWidget).where(
            and_(
                DashboardWidget.is_default == True,
                DashboardWidget.is_active == True,
            )
        )
        if widget_type:
            query = query.where(DashboardWidget.widget_type == widget_type)
        query = query.order_by(DashboardWidget.order)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_dashboard_widget(self, widget: DashboardWidget) -> DashboardWidget:
        self.db.add(widget)
        await self.db.flush()
        await self.db.refresh(widget)
        return widget

    async def update_dashboard_widget(self, widget: DashboardWidget) -> DashboardWidget:
        await self.db.flush()
        await self.db.refresh(widget)
        return widget

    async def delete_dashboard_widget(self, widget: DashboardWidget) -> bool:
        await self.db.delete(widget)
        await self.db.flush()
        return True