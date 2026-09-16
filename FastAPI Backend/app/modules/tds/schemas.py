from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    notes: str | None = None
    metadata: dict[str, Any] = {}


class TDSChallanCreate(TDSChallanBase):
    pass


class TDSChallanUpdate(BaseModel):
    cin: str | None = Field(None, max_length=50)
    bsr_code: str | None = Field(None, max_length=7)
    deposit_date: datetime | None = None
    challan_serial: str | None = Field(None, max_length=5)
    tax_amount: float | None = Field(None, ge=0)
    surcharge: float | None = Field(None, ge=0)
    education_cess: float | None = Field(None, ge=0)
    interest: float | None = Field(None, ge=0)
    penalty: float | None = Field(None, ge=0)
    fee: float | None = Field(None, ge=0)
    total_amount: float | None = Field(None, ge=0)
    status: str | None = Field(None, max_length=20)
    verified_at: datetime | None = None
    verified_by: UUID | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class TDSChallanResponse(TDSChallanBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tds_cycle_id: UUID
    verified_at: datetime | None = None
    verified_by: UUID | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class TDSDeducteeBase(BaseModel):
    deductee_type: str = Field(..., max_length=20)
    deductee_name: str = Field(..., max_length=255)
    deductee_pan: str = Field(..., max_length=20)
    deductee_address: str | None = None
    section_code: str = Field(..., max_length=10)
    amount_paid: float = Field(..., ge=0)
    tax_deducted: float = Field(..., ge=0)
    tax_deposited: float = Field(default=0, ge=0)
    deduction_date: datetime
    deposit_date: datetime | None = None
    certificate_number: str | None = Field(None, max_length=50)
    remarks: str | None = None
    metadata: dict[str, Any] = {}


class TDSDeducteeCreate(TDSDeducteeBase):
    pass


class TDSDeducteeUpdate(BaseModel):
    deductee_type: str | None = Field(None, max_length=20)
    deductee_name: str | None = Field(None, max_length=255)
    deductee_pan: str | None = Field(None, max_length=20)
    deductee_address: str | None = None
    section_code: str | None = Field(None, max_length=10)
    amount_paid: float | None = Field(None, ge=0)
    tax_deducted: float | None = Field(None, ge=0)
    tax_deposited: float | None = Field(None, ge=0)
    deduction_date: datetime | None = None
    deposit_date: datetime | None = None
    certificate_number: str | None = Field(None, max_length=50)
    remarks: str | None = None
    metadata: dict[str, Any] | None = None


class TDSDeducteeResponse(TDSDeducteeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tds_cycle_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class TDSComplianceCycleBase(BaseModel):
    client_id: UUID
    form_type: str = Field(..., pattern="^(24q|26q|27q|27eq)$")
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    quarter: str = Field(..., pattern="^(q1|q2|q3|q4)$")
    period_start: datetime
    period_end: datetime
    due_date: datetime
    extended_due_date: datetime | None = None
    tan: str | None = Field(None, max_length=20)
    priority: str = Field(default="medium", max_length=20)
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    checklist: list[dict[str, Any]] = []
    document_requirements: list[dict[str, Any]] = []
    workflow_stages: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}


class TDSComplianceCycleCreate(TDSComplianceCycleBase):
    pass


class TDSComplianceCycleUpdate(BaseModel):
    compliance_cycle_id: UUID | None = None
    matter_id: UUID | None = None
    form_type: str | None = Field(None, pattern="^(24q|26q|27q|27eq)$")
    financial_year: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    quarter: str | None = Field(None, pattern="^(q1|q2|q3|q4)$")
    period_start: datetime | None = None
    period_end: datetime | None = None
    due_date: datetime | None = None
    extended_due_date: datetime | None = None
    filing_date: datetime | None = None
    processed_date: datetime | None = None
    status: str | None = None
    priority: str | None = Field(None, max_length=20)
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    tan: str | None = Field(None, max_length=20)
    total_deductees: int | None = Field(None, ge=0)
    total_tax_deducted: float | None = Field(None, ge=0)
    total_tax_deposited: float | None = Field(None, ge=0)
    token_number: str | None = Field(None, max_length=50)
    acknowledgment_number: str | None = Field(None, max_length=50)
    checklist: list[dict[str, Any]] | None = None
    document_requirements: list[dict[str, Any]] | None = None
    workflow_stages: list[dict[str, Any]] | None = None
    missing_info: list[dict[str, Any]] | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class TDSComplianceCycleResponse(TDSComplianceCycleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    compliance_cycle_id: UUID | None = None
    matter_id: UUID | None = None
    workflow_instance_id: UUID | None = None
    status: str
    filing_date: datetime | None = None
    processed_date: datetime | None = None
    total_deductees: int
    total_tax_deducted: float
    total_tax_deposited: float
    token_number: str | None = None
    acknowledgment_number: str | None = None
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
    challans: list[TDSChallanResponse] = []
    deductees: list[TDSDeducteeResponse] = []


class TDSComplianceCycleListResponse(BaseModel):
    items: list[TDSComplianceCycleResponse]
    total: int
    page: int
    page_size: int


class TDSChallanListResponse(BaseModel):
    items: list[TDSChallanResponse]
    total: int
    page: int
    page_size: int


class TDSDeducteeListResponse(BaseModel):
    items: list[TDSDeducteeResponse]
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
    upcoming_deadlines: list[TDSComplianceCycleResponse] = []


from app.modules.clients.schemas import ClientResponse
from app.modules.matters.schemas import MatterResponse
from app.modules.users.schemas import TeamResponse, UserResponse
