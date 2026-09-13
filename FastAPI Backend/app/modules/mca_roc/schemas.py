from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MCAFilingConfigBase(BaseModel):
    filing_type: str = Field(..., max_length=50)
    entity_type: str = Field(..., max_length=20)
    filing_category: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    form_name: str = Field(..., max_length=100)
    due_date_rule: Dict[str, Any] = {}
    period_rule: Dict[str, Any] = {}
    is_annual: bool = True
    default_checklist: List[Dict[str, Any]] = []
    default_document_requirements: List[Dict[str, Any]] = []
    default_workflow_stages: List[Dict[str, Any]] = []
    base_fee: float = Field(default=0, ge=0)
    additional_fee_per_day: float = Field(default=0, ge=0)
    max_additional_fee: float = Field(default=0, ge=0)
    is_active: bool = True
    is_system: bool = False
    metadata: Dict[str, Any] = {}


class MCAFilingConfigCreate(MCAFilingConfigBase):
    pass


class MCAFilingConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    form_name: Optional[str] = Field(None, max_length=100)
    due_date_rule: Optional[Dict[str, Any]] = None
    period_rule: Optional[Dict[str, Any]] = None
    is_annual: Optional[bool] = None
    default_checklist: Optional[List[Dict[str, Any]]] = None
    default_document_requirements: Optional[List[Dict[str, Any]]] = None
    default_workflow_stages: Optional[List[Dict[str, Any]]] = None
    base_fee: Optional[float] = Field(None, ge=0)
    additional_fee_per_day: Optional[float] = Field(None, ge=0)
    max_additional_fee: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class MCAFilingConfigResponse(MCAFilingConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class MCAFilingCycleBase(BaseModel):
    client_id: UUID
    entity_type: str = Field(..., pattern="^(company|llp)$")
    filing_type: str = Field(..., max_length=50)
    filing_category: str = Field(..., pattern="^(annual|event_based|other)$")
    financial_year: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    event_date: Optional[datetime] = None
    event_description: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: datetime
    extended_due_date: Optional[datetime] = None
    agm_date: Optional[datetime] = None
    cin_llpin: Optional[str] = Field(None, max_length=21)
    company_name: Optional[str] = Field(None, max_length=255)
    roc_code: Optional[str] = Field(None, max_length=10)
    priority: str = Field(default="medium", max_length=20)
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    checklist: List[Dict[str, Any]] = []
    document_requirements: List[Dict[str, Any]] = []
    workflow_stages: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class MCAFilingCycleCreate(MCAFilingCycleBase):
    pass


class MCAFilingCycleUpdate(BaseModel):
    compliance_cycle_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    entity_type: Optional[str] = Field(None, pattern="^(company|llp)$")
    filing_type: Optional[str] = Field(None, max_length=50)
    filing_category: Optional[str] = Field(None, pattern="^(annual|event_based|other)$")
    financial_year: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    event_date: Optional[datetime] = None
    event_description: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extended_due_date: Optional[datetime] = None
    agm_date: Optional[datetime] = None
    filing_date: Optional[datetime] = None
    approval_date: Optional[datetime] = None
    status: Optional[str] = None
    priority: Optional[str] = Field(None, max_length=20)
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    cin_llpin: Optional[str] = Field(None, max_length=21)
    company_name: Optional[str] = Field(None, max_length=255)
    roc_code: Optional[str] = Field(None, max_length=10)
    srn: Optional[str] = Field(None, max_length=50)
    acknowledgment_number: Optional[str] = Field(None, max_length=50)
    challan_amount: Optional[float] = Field(None, ge=0)
    additional_fee: Optional[float] = Field(None, ge=0)
    checklist: Optional[List[Dict[str, Any]]] = None
    document_requirements: Optional[List[Dict[str, Any]]] = None
    workflow_stages: Optional[List[Dict[str, Any]]] = None
    missing_info: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCAFilingCycleResponse(MCAFilingCycleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    compliance_cycle_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    workflow_instance_id: Optional[UUID] = None
    status: str
    filing_date: Optional[datetime] = None
    approval_date: Optional[datetime] = None
    srn: Optional[str] = None
    acknowledgment_number: Optional[str] = None
    challan_amount: float
    additional_fee: float
    missing_info: List[Dict[str, Any]] = []
    missing_info_count: int
    notes: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    client: Optional["ClientResponse"] = None
    matter: Optional["MatterResponse"] = None
    assigned_user: Optional["UserResponse"] = None
    assigned_team: Optional["TeamResponse"] = None


class MCAFilingCycleListResponse(BaseModel):
    items: List[MCAFilingCycleResponse]
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
    upcoming_deadlines: List[MCAFilingCycleResponse] = []


from app.modules.clients.schemas import ClientResponse
from app.modules.matters.schemas import MatterResponse
from app.modules.users.schemas import UserResponse, TeamResponse