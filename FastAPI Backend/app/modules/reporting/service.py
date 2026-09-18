from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.storage.azure_blob import get_azure_blob_service
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
from app.modules.reporting.repository import ReportingRepository
from app.modules.reporting.schemas import (
    ReportDefinitionCreate,
    ReportDefinitionUpdate,
    ReportParameterCreate,
    ReportParameterUpdate,
    ReportJobCreate,
    ReportJobUpdate,
    ReportScheduleCreate,
    ReportScheduleUpdate,
    DashboardWidgetCreate,
    DashboardWidgetUpdate,
    ReportGenerateRequest,
)


class ReportingService:
    def __init__(self, db: AsyncSession, tenant_id: UUID, user_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repository = ReportingRepository(db, tenant_id)
        self.blob_service = get_azure_blob_service()

    async def create_report_definition(self, data: ReportDefinitionCreate) -> ReportDefinition:
        if await self.repository.get_report_definition_by_name(data.name):
            raise ValidationException(f"Report definition with name '{data.name}' already exists")

        definition = ReportDefinition(
            name=data.name,
            description=data.description,
            category=data.category,
            query_config=data.query_config,
            output_format=data.output_format,
            output_config=data.output_config,
            is_active=data.is_active,
            is_system=data.is_system,
            created_by_id=self.user_id,
            tenant_id=self.tenant_id,
        )
        definition = await self.repository.create_report_definition(definition)

        for param_data in data.parameters:
            parameter = ReportParameter(
                report_definition_id=definition.id,
                name=param_data.name,
                display_name=param_data.display_name,
                param_type=param_data.param_type,
                is_required=param_data.is_required,
                default_value=param_data.default_value,
                options=param_data.options,
                validation_rules=param_data.validation_rules,
                order=param_data.order,
                tenant_id=self.tenant_id,
            )
            await self.repository.create_report_parameter(parameter)

        return definition

    async def get_report_definition(self, definition_id: UUID) -> ReportDefinition:
        definition = await self.repository.get_report_definition(definition_id)
        if not definition:
            raise NotFoundException("Report definition not found")
        return definition

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
        return await self.repository.list_report_definitions(
            category=category,
            is_active=is_active,
            is_system=is_system,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_report_definition(self, definition_id: UUID, data: ReportDefinitionUpdate) -> ReportDefinition:
        definition = await self.get_report_definition(definition_id)

        if data.name and data.name != definition.name:
            existing = await self.repository.get_report_definition_by_name(data.name)
            if existing and existing.id != definition_id:
                raise ValidationException(f"Report definition with name '{data.name}' already exists")
            definition.name = data.name

        if data.description is not None:
            definition.description = data.description
        if data.category is not None:
            definition.category = data.category
        if data.query_config is not None:
            definition.query_config = data.query_config
        if data.output_format is not None:
            definition.output_format = data.output_format
        if data.output_config is not None:
            definition.output_config = data.output_config
        if data.is_active is not None:
            definition.is_active = data.is_active

        return await self.repository.update_report_definition(definition)

    async def delete_report_definition(self, definition_id: UUID) -> bool:
        definition = await self.get_report_definition(definition_id)
        if definition.is_system:
            raise ValidationException("Cannot delete system report definition")
        return await self.repository.delete_report_definition(definition)

    async def create_report_parameter(self, definition_id: UUID, data: ReportParameterCreate) -> ReportParameter:
        definition = await self.get_report_definition(definition_id)

        existing = await self.repository.get_report_parameter_by_name(definition_id, data.name)
        if existing:
            raise ValidationException(f"Parameter with name '{data.name}' already exists for this report definition")

        parameter = ReportParameter(
            report_definition_id=definition_id,
            name=data.name,
            display_name=data.display_name,
            param_type=data.param_type,
            is_required=data.is_required,
            default_value=data.default_value,
            options=data.options,
            validation_rules=data.validation_rules,
            order=data.order,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_report_parameter(parameter)

    async def update_report_parameter(self, parameter_id: UUID, data: ReportParameterUpdate) -> ReportParameter:
        parameter = await self.repository.get_report_parameter(parameter_id)
        if not parameter:
            raise NotFoundException("Report parameter not found")

        if data.display_name is not None:
            parameter.display_name = data.display_name
        if data.param_type is not None:
            parameter.param_type = data.param_type
        if data.is_required is not None:
            parameter.is_required = data.is_required
        if data.default_value is not None:
            parameter.default_value = data.default_value
        if data.options is not None:
            parameter.options = data.options
        if data.validation_rules is not None:
            parameter.validation_rules = data.validation_rules
        if data.order is not None:
            parameter.order = data.order

        return await self.repository.update_report_parameter(parameter)

    async def delete_report_parameter(self, parameter_id: UUID) -> bool:
        parameter = await self.repository.get_report_parameter(parameter_id)
        if not parameter:
            raise NotFoundException("Report parameter not found")
        return await self.repository.delete_report_parameter(parameter)

    async def generate_report(self, data: ReportGenerateRequest) -> ReportJob:
        definition = await self.get_report_definition(data.report_definition_id)

        if data.idempotency_key:
            existing = await self.repository.get_report_job_by_idempotency_key(data.idempotency_key)
            if existing:
                return existing

        job = ReportJob(
            report_definition_id=data.report_definition_id,
            parameters=data.parameters,
            status=ReportStatus.QUEUED,
            idempotency_key=data.idempotency_key or str(uuid4()),
            tenant_id=self.tenant_id,
        )
        job = await self.repository.create_report_job(job)

        from app.workers.reporting_tasks import generate_report_task
        generate_report_task.delay(str(job.id))

        return job

    async def get_report_job(self, job_id: UUID) -> ReportJob:
        job = await self.repository.get_report_job(job_id)
        if not job:
            raise NotFoundException("Report job not found")
        return job

    async def list_report_jobs(
        self,
        report_definition_id: Optional[UUID] = None,
        status: Optional[ReportStatus] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ReportJob], int]:
        return await self.repository.list_report_jobs(
            report_definition_id=report_definition_id,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_report_job(self, job_id: UUID, data: ReportJobUpdate) -> ReportJob:
        job = await self.get_report_job(job_id)

        if data.status is not None:
            job.status = data.status
        if data.progress is not None:
            job.progress = data.progress
        if data.current_step is not None:
            job.current_step = data.current_step
        if data.result_ref is not None:
            job.result_ref = data.result_ref
        if data.result_format is not None:
            job.result_format = data.result_format
        if data.result_size is not None:
            job.result_size = data.result_size
        if data.result_checksum is not None:
            job.result_checksum = data.result_checksum
        if data.error_message is not None:
            job.error_message = data.error_message
        if data.error_details is not None:
            job.error_details = data.error_details
        if data.retry_count is not None:
            job.retry_count = data.retry_count
        if data.started_at is not None:
            job.started_at = data.started_at
        if data.completed_at is not None:
            job.completed_at = data.completed_at
        if data.expires_at is not None:
            job.expires_at = data.expires_at

        return await self.repository.update_report_job(job)

    async def get_report_output(self, output_id: UUID) -> ReportOutput:
        output = await self.repository.get_report_output(output_id)
        if not output:
            raise NotFoundException("Report output not found")
        return output

    async def download_report_output(self, output_id: UUID) -> tuple[str, datetime]:
        output = await self.get_report_output(output_id)
        download_url = await self.blob_service.generate_download_sas_url(
            storage_key=output.storage_key,
            expiry_hours=1,
        )
        output.download_count += 1
        output.downloaded_at = datetime.utcnow()
        await self.repository.update_report_output(output)
        return download_url, datetime.utcnow() + timedelta(hours=1)

    async def create_report_schedule(self, data: ReportScheduleCreate) -> ReportSchedule:
        definition = await self.get_report_definition(data.report_definition_id)

        schedule = ReportSchedule(
            report_definition_id=data.report_definition_id,
            name=data.name,
            cron_expression=data.cron_expression,
            timezone=data.timezone,
            parameters=data.parameters,
            recipients=data.recipients,
            is_active=data.is_active,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_report_schedule(schedule)

    async def get_report_schedule(self, schedule_id: UUID) -> ReportSchedule:
        schedule = await self.repository.get_report_schedule(schedule_id)
        if not schedule:
            raise NotFoundException("Report schedule not found")
        return schedule

    async def list_report_schedules(
        self,
        report_definition_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReportSchedule], int]:
        return await self.repository.list_report_schedules(
            report_definition_id=report_definition_id,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

    async def update_report_schedule(self, schedule_id: UUID, data: ReportScheduleUpdate) -> ReportSchedule:
        schedule = await self.get_report_schedule(schedule_id)

        if data.name is not None:
            schedule.name = data.name
        if data.cron_expression is not None:
            schedule.cron_expression = data.cron_expression
        if data.timezone is not None:
            schedule.timezone = data.timezone
        if data.parameters is not None:
            schedule.parameters = data.parameters
        if data.recipients is not None:
            schedule.recipients = data.recipients
        if data.is_active is not None:
            schedule.is_active = data.is_active

        return await self.repository.update_report_schedule(schedule)

    async def delete_report_schedule(self, schedule_id: UUID) -> bool:
        schedule = await self.get_report_schedule(schedule_id)
        return await self.repository.delete_report_schedule(schedule)

    async def create_dashboard_widget(self, data: DashboardWidgetCreate) -> DashboardWidget:
        widget = DashboardWidget(
            name=data.name,
            description=data.description,
            widget_type=data.widget_type,
            query_config=data.query_config,
            display_config=data.display_config,
            layout=data.layout,
            is_default=data.is_default,
            is_active=data.is_active,
            order=data.order,
            created_by_id=self.user_id,
            tenant_id=self.tenant_id,
        )
        return await self.repository.create_dashboard_widget(widget)

    async def get_dashboard_widget(self, widget_id: UUID) -> DashboardWidget:
        widget = await self.repository.get_dashboard_widget(widget_id)
        if not widget:
            raise NotFoundException("Dashboard widget not found")
        return widget

    async def list_dashboard_widgets(
        self,
        widget_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DashboardWidget], int]:
        return await self.repository.list_dashboard_widgets(
            widget_type=widget_type,
            is_active=is_active,
            is_default=is_default,
            page=page,
            page_size=page_size,
        )

    async def get_default_widgets(self, widget_type: Optional[str] = None) -> list[DashboardWidget]:
        return await self.repository.get_default_widgets(widget_type=widget_type)

    async def update_dashboard_widget(self, widget_id: UUID, data: DashboardWidgetUpdate) -> DashboardWidget:
        widget = await self.get_dashboard_widget(widget_id)

        if data.name is not None:
            widget.name = data.name
        if data.description is not None:
            widget.description = data.description
        if data.widget_type is not None:
            widget.widget_type = data.widget_type
        if data.query_config is not None:
            widget.query_config = data.query_config
        if data.display_config is not None:
            widget.display_config = data.display_config
        if data.layout is not None:
            widget.layout = data.layout
        if data.is_default is not None:
            widget.is_default = data.is_default
        if data.is_active is not None:
            widget.is_active = data.is_active
        if data.order is not None:
            widget.order = data.order

        return await self.repository.update_dashboard_widget(widget)

    async def delete_dashboard_widget(self, widget_id: UUID) -> bool:
        widget = await self.get_dashboard_widget(widget_id)
        return await self.repository.delete_dashboard_widget(widget)