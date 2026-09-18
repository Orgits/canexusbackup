from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.modules.reporting.models import ReportStatus, ReportFormat


class ReportParameterBase(BaseModel):
    name: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=255)
    param_type: str = Field(..., max_length=50)
    is_required: bool = False
    default_value: Optional[str] = None
    options: Optional[list[str]] = None
    validation_rules: dict = Field(default_factory=dict)
    order: int = 0


class ReportParameterCreate(ReportParameterBase):
    pass


class ReportParameterUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    param_type: Optional[str] = Field(None, max_length=50)
    is_required: Optional[bool] = None
    default_value: Optional[str] = None
    options: Optional[list[str]] = None
    validation_rules: Optional[dict] = None
    order: Optional[int] = None


class ReportParameterResponse(ReportParameterBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_definition_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ReportDefinitionBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    category: str = Field(..., max_length=100)
    query_config: dict = Field(default_factory=dict)
    output_format: ReportFormat = ReportFormat.PDF
    output_config: dict = Field(default_factory=dict)
    is_active: bool = True
    is_system: bool = False


class ReportDefinitionCreate(ReportDefinitionBase):
    parameters: list[ReportParameterCreate] = Field(default_factory=list)


class ReportDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    query_config: Optional[dict] = None
    output_format: Optional[ReportFormat] = None
    output_config: Optional[dict] = None
    is_active: Optional[bool] = None


class ReportDefinitionResponse(ReportDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    parameters: list[ReportParameterResponse] = Field(default_factory=list)


class ReportDefinitionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    output_format: ReportFormat
    is_active: bool
    is_system: bool
    tenant_id: UUID
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ReportJobBase(BaseModel):
    parameters: dict = Field(default_factory=dict)


class ReportJobCreate(ReportJobBase):
    report_definition_id: UUID
    idempotency_key: Optional[str] = Field(None, max_length=255)


class ReportJobUpdate(BaseModel):
    status: Optional[ReportStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    current_step: Optional[str] = Field(None, max_length=100)
    result_ref: Optional[str] = Field(None, max_length=500)
    result_format: Optional[ReportFormat] = None
    result_size: Optional[int] = None
    result_checksum: Optional[str] = Field(None, max_length=64)
    error_message: Optional[str] = None
    error_details: Optional[dict] = None
    retry_count: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ReportJobResponse(ReportJobBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_definition_id: UUID
    status: ReportStatus
    progress: int
    current_step: Optional[str] = None
    result_ref: Optional[str] = None
    result_format: Optional[ReportFormat] = None
    result_size: Optional[int] = None
    result_checksum: Optional[str] = None
    error_message: Optional[str] = None
    error_details: dict = Field(default_factory=dict)
    retry_count: int
    max_retries: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ReportJobListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_definition_id: UUID
    status: ReportStatus
    progress: int
    current_step: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ReportOutputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    storage_key: str
    format: ReportFormat
    size_bytes: int
    checksum: str
    expires_at: Optional[datetime] = None
    downloaded_at: Optional[datetime] = None
    download_count: int
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ReportScheduleBase(BaseModel):
    name: str = Field(..., max_length=255)
    cron_expression: str = Field(..., max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    parameters: dict = Field(default_factory=dict)
    recipients: list[str] = Field(default_factory=list)
    is_active: bool = True


class ReportScheduleCreate(ReportScheduleBase):
    report_definition_id: UUID


class ReportScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    cron_expression: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    parameters: Optional[dict] = None
    recipients: Optional[list[str]] = None
    is_active: Optional[bool] = None


class ReportScheduleResponse(ReportScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_definition_id: UUID
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    extra_metadata: dict = Field(default_factory=dict)
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ReportScheduleListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_definition_id: UUID
    name: str
    cron_expression: str
    timezone: str
    is_active: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DashboardWidgetBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    widget_type: str = Field(..., max_length=50)
    query_config: dict = Field(default_factory=dict)
    display_config: dict = Field(default_factory=dict)
    layout: dict = Field(default_factory=dict)
    is_default: bool = False
    is_active: bool = True
    order: int = 0


class DashboardWidgetCreate(DashboardWidgetBase):
    pass


class DashboardWidgetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    widget_type: Optional[str] = Field(None, max_length=50)
    query_config: Optional[dict] = None
    display_config: Optional[dict] = None
    layout: Optional[dict] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class DashboardWidgetResponse(DashboardWidgetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class DashboardWidgetListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    widget_type: str
    is_default: bool
    is_active: bool
    order: int
    tenant_id: UUID
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ReportGenerateRequest(BaseModel):
    report_definition_id: UUID
    parameters: dict = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(None, max_length=255)


class ReportGenerateResponse(BaseModel):
    job_id: UUID
    status: ReportStatus
    message: str


class ReportDownloadResponse(BaseModel):
    download_url: str
    expires_at: datetime
    format: ReportFormat
    size_bytes: int
    checksum: str