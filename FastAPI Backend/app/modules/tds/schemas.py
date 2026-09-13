from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TDSChallanBase(BaseModel):
    cin: str = Field(..., max_length=50)
    bsr_code: str = Field(..., max_length=7)
    deposit_date: datetime
    challan_serial: str = Field(..., max_length=5)
    tax_amount: float = Field(..., ge=0)
    surcharge: float = Field(default=0, ge=0)
    education_cess: float = Field(default=0, ge=0)
    interest: float = Field(default=0, ge=0)
    penalty: float = Field(default=0, ge=0)
    fee: float = Field(default=0, ge=0)
    total_amount: float = Field(..., ge=0)
    status: str = Field(default="pending", max_length=20)
    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TDSChallanCreate(TDSChallanBase):
    pass


class TDSChallanUpdate(BaseModel):
    cin: Optional[str] = Field(None, max_length=50)
    bsr_code: Optional[str] = Field(None, max_length=7)
    deposit_date: Optional[datetime] = None
    challan_serial: Optional[str] = Field(None, max_length=5)
    tax_amount: Optional[float] = Field(None, ge=0)
    surcharge: Optional[float] = Field(None, ge=0)
    education_cess: Optional[float] = Field(None, ge=0)
    interest: Optional[float] = Field(None, ge=0)
    penalty: Optional[float] = Field(None, ge=0)
    fee: Optional[float] = Field(None, ge=0)
    total_amount: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=20)
    verified_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TDSChallanResponse(TDSChallanBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tds_cycle_id: UUID
    verified_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class TDSDeducteeBase(BaseModel):
    deductee_type: str = Field(..., max_length=20)
    deductee_name: str = Field(..., max_length=255)
    deductee_pan: str = Field(..., max_length=20)
    deductee_address: Optional[str] = None
    section_code: str = Field(..., max_length=10)
    amount_paid: float = Field(..., ge=0)
    tax_deducted: float = Field(..., ge=0)
    tax_deposited: float = Field(default=0, ge=0)
    deduction_date: datetime
    deposit_date: Optional[datetime] = None
    certificate_number: Optional[str] = Field(None, max_length=50)
    remarks: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TDSDeducteeCreate(TDSDeducteeBase):
    pass


class TDSDeducteeUpdate(BaseModel):
    deductee_type: Optional[str] = Field(None, max_length=20)
    deductee_name: Optional[str] = Field(None, max_length=255)
    deductee_pan: Optional[str] = Field(None, max_length=20)
    deductee_address: Optional[str] = None
    section_code: Optional[str] = Field(None, max_length=10)
    amount_paid: Optional[float] = Field(None, ge=0)
    tax_deducted: Optional[float] = Field(None, ge=0)
    tax_deposited: Optional[float] = Field(None, ge=0)
    deduction_date: Optional[datetime] = None
    deposit_date: Optional[datetime] = None
    certificate_number: Optional[str] = Field(None, max_length=50)
    remarks: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TDSDeducteeResponse(TDSDeducteeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tds_cycle_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class TDSComplianceCycleBase(BaseModel):
    client_id: UUID
    form_type: str = Field(..., pattern="^(24q|26q|27q|27eq)$")
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    quarter: str = Field(..., pattern="^(q1|q2|q3|q4)$")
    period_start: datetime
    period_end: datetime
    due_date: datetime
    extended_due_date: Optional[datetime] = None
    tan: Optional[str] = Field(None, max_length=20)
    priority: str = Field(default="medium", max_length=20)
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    checklist: List[Dict[str, Any]] = []
    document_requirements: List[Dict[str, Any]] = []
    workflow_stages: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class TDSComplianceCycleCreate(TDSComplianceCycleBase):
    pass


class TDSComplianceCycleUpdate(BaseModel):
    compliance_cycle_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    form_type: Optional[str] = Field(None, pattern="^(24q|26q|27q|27eq)$")
    financial_year: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    quarter: Optional[str] = Field(None, pattern="^(q1|q2|q3|q4)$")
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extended_due_date: Optional[datetime] = None
    filing_date: Optional[datetime] = None
    processed_date: Optional[datetime] = None
    status: Optional[str] = None
    priority: Optional[str] = Field(None, max_length=20)
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    tan: Optional[str] = Field(None, max_length=20)
    total_deductees: Optional[int] = Field(None, ge=0)
    total_tax_deducted: Optional[float] = Field(None, ge=0)
    total_tax_deposited: Optional[float] = Field(None, ge=0)
    token_number: Optional[str] = Field(None, max_length=50)
    acknowledgment_number: Optional[str] = Field(None, max_length=50)
    checklist: Optional[List[Dict[str, Any]]] = None
    document_requirements: Optional[List[Dict[str, Any]]] = None
    workflow_stages: Optional[List[Dict[str, Any]]] = None
    missing_info: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TDSComplianceCycleResponse(TDSComplianceCycleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    compliance_cycle_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    workflow_instance_id: Optional[UUID] = None
    status: str
    filing_date: Optional[datetime] = None
    processed_date: Optional[datetime] = None
    total_deductees: int
    total_tax_deducted: float
    total_tax_deposited: float
    token_number: Optional[str] = None
    acknowledgment_number: Optional[str] = None
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
    challans: List[TDSChallanResponse] = []
    deductees: List[TDSDeducteeResponse] = []


class TDSComplianceCycleListResponse(BaseModel):
    items: List[TDSComplianceCycleResponse]
    total: int
    page: int
    page_size: int


class TDSChallanListResponse(BaseModel):
    items: List[TDSChallanResponse]
    total: int
    page: int
    page_size: int


class TDSDeducteeListResponse(BaseModel):
    items: List[TDSDeducteeResponse]
    total: int
    page: int
    page_size: int


class TDSSummaryResponse(BaseModel):
    total_cycles: int
    pending: int
    in_progress: int
    filed: int
    processed: int
    overdue: int
    total_tax_deducted: float
    total_tax_deposited: float
    upcoming_deadlines: List[TDSComplianceCycleResponse] = []


from app.modules.clients.schemas import ClientResponse
from app.modules.matters.schemas import MatterResponse
from app.modules.users.schemas import UserResponse, TeamResponse