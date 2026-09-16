from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MCAFilingConfigBase(BaseModel):
    filing_type: str = Field(..., max_length=50)
    entity_type: str = Field(..., max_length=20)
    filing_category: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    description: str | None = None
    form_name: str = Field(..., max_length=100)
    due_date_rule: dict[str, Any] = {}
    period_rule: dict[str, Any] = {}
    is_annual: bool = True
    default_checklist: list[dict[str, Any]] = []
    default_document_requirements: list[dict[str, Any]] = []
    default_workflow_stages: list[dict[str, Any]] = []
    base_fee: float = Field(default=0, ge=0)
    additional_fee_per_day: float = Field(default=0, ge=0)
    max_additional_fee: float = Field(default=0, ge=0)
    is_active: bool = True
    is_system: bool = False
    metadata: dict[str, Any] = {}


class MCAFilingConfigCreate(MCAFilingConfigBase):
    pass


class MCAFilingConfigUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    form_name: str | None = Field(None, max_length=100)
    due_date_rule: dict[str, Any] | None = None
    period_rule: dict[str, Any] | None = None
    is_annual: bool | None = None
    default_checklist: list[dict[str, Any]] | None = None
    default_document_requirements: list[dict[str, Any]] | None = None
    default_workflow_stages: list[dict[str, Any]] | None = None
    base_fee: float | None = Field(None, ge=0)
    additional_fee_per_day: float | None = Field(None, ge=0)
    max_additional_fee: float | None = Field(None, ge=0)
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class MCAFilingConfigResponse(MCAFilingConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class MCAFilingCycleBase(BaseModel):
    client_id: UUID
    entity_type: str = Field(..., pattern="^(company|llp)$")
    filing_type: str = Field(..., max_length=50)
    filing_category: str = Field(..., pattern="^(annual|event_based|other)$")
    financial_year: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    event_date: datetime | None = None
    event_description: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    due_date: datetime
    extended_due_date: datetime | None = None
    agm_date: datetime | None = None
    cin_llpin: str | None = Field(None, max_length=21)
    company_name: str | None = Field(None, max_length=255)
    roc_code: str | None = Field(None, max_length=10)
    priority: str = Field(default="medium", max_length=20)
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    checklist: list[dict[str, Any]] = []
    document_requirements: list[dict[str, Any]] = []
    workflow_stages: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}


class MCAFilingCycleCreate(MCAFilingCycleBase):
    pass


class MCAFilingCycleUpdate(BaseModel):
    compliance_cycle_id: UUID | None = None
    matter_id: UUID | None = None
    entity_type: str | None = Field(None, pattern="^(company|llp)$")
    filing_type: str | None = Field(None, max_length=50)
    filing_category: str | None = Field(None, pattern="^(annual|event_based|other)$")
    financial_year: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    event_date: datetime | None = None
    event_description: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    due_date: datetime | None = None
    extended_due_date: datetime | None = None
    agm_date: datetime | None = None
    filing_date: datetime | None = None
    approval_date: datetime | None = None
    status: str | None = None
    priority: str | None = Field(None, max_length=20)
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    cin_llpin: str | None = Field(None, max_length=21)
    company_name: str | None = Field(None, max_length=255)
    roc_code: str | None = Field(None, max_length=10)
    srn: str | None = Field(None, max_length=50)
    acknowledgment_number: str | None = Field(None, max_length=50)
    challan_amount: float | None = Field(None, ge=0)
    additional_fee: float | None = Field(None, ge=0)
    checklist: list[dict[str, Any]] | None = None
    document_requirements: list[dict[str, Any]] | None = None
    workflow_stages: list[dict[str, Any]] | None = None
    missing_info: list[dict[str, Any]] | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class MCAFilingCycleResponse(MCAFilingCycleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    compliance_cycle_id: UUID | None = None
    matter_id: UUID | None = None
    workflow_instance_id: UUID | None = None
    status: str
    filing_date: datetime | None = None
    approval_date: datetime | None = None
    srn: str | None = None
    acknowledgment_number: str | None = None
    challan_amount: float
    additional_fee: float
    missing_info: list[dict[str, Any]] = []
    missing_info_count: int
    notes: str | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    client: Optional["ClientResponse"] = None
    matter: Optional["MatterResponse"] = None
    assigned_user: Optional["UserResponse"] = None
    assigned_team: Optional["TeamResponse"] = None


class MCAFilingCycleListResponse(BaseModel):
    items: list[MCAFilingCycleResponse]
    total: int
    page: int
    page_size: int


class MCASummaryResponse(BaseModel):
    total_filings: int
    pending: int
    in_progress: int
    ready_for_filing: int
    filed: int
    approved: int
    rejected: int
    overdue: int
    upcoming_deadlines: list[MCAFilingCycleResponse] = []


from app.modules.clients.schemas import ClientResponse
from app.modules.matters.schemas import MatterResponse
from app.modules.users.schemas import TeamResponse, UserResponse
