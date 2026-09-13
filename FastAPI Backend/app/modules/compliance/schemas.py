from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class ComplianceFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    HALF_YEARLY = "half_yearly"
    EVENT_BASED = "event_based"


class ComplianceStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    REWORK = "rework"
    APPROVED = "approved"
    FILED = "filed"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ComplianceTypeBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    frequency: ComplianceFrequency
    applicability_rules: Dict[str, Any] = Field(default_factory=dict)
    due_date_rules: Dict[str, Any] = Field(default_factory=dict)
    period_rules: Dict[str, Any] = Field(default_factory=dict)
    default_checklist: List[Dict[str, Any]] = Field(default_factory=list)
    default_document_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    default_workflow_stages: List[Dict[str, Any]] = Field(default_factory=list)
    default_assignment_rules: Dict[str, Any] = Field(default_factory=dict)
    reminder_schedule: List[Dict[str, Any]] = Field(default_factory=list)
    escalation_rules: List[Dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceTypeCreate(ComplianceTypeBase):
    pass


class ComplianceTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    frequency: Optional[ComplianceFrequency] = None
    applicability_rules: Optional[Dict[str, Any]] = None
    due_date_rules: Optional[Dict[str, Any]] = None
    period_rules: Optional[Dict[str, Any]] = None
    default_checklist: Optional[List[Dict[str, Any]]] = None
    default_document_requirements: Optional[List[Dict[str, Any]]] = None
    default_workflow_stages: Optional[List[Dict[str, Any]]] = None
    default_assignment_rules: Optional[Dict[str, Any]] = None
    reminder_schedule: Optional[List[Dict[str, Any]]] = None
    escalation_rules: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceTypeResponse(ComplianceTypeBase):
    id: UUID
    is_system: bool
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceCycleBase(BaseModel):
    client_id: UUID
    compliance_type_id: UUID
    matter_id: Optional[UUID] = None
    period_start: datetime
    period_end: datetime
    due_date: datetime
    extended_due_date: Optional[datetime] = None
    priority: str = "medium"
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    checklist: List[Dict[str, Any]] = Field(default_factory=list)
    document_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    workflow_stages: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceCycleCreate(ComplianceCycleBase):
    pass


class ComplianceCycleUpdate(BaseModel):
    matter_id: Optional[UUID] = None
    extended_due_date: Optional[datetime] = None
    filing_date: Optional[datetime] = None
    status: Optional[ComplianceStatus] = None
    priority: Optional[str] = None
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    document_requirements: Optional[List[Dict[str, Any]]] = None
    workflow_stage: Optional[str] = None
    workflow_stages: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceCycleResponse(ComplianceCycleBase):
    id: UUID
    status: ComplianceStatus
    filing_date: Optional[datetime] = None
    workflow_stage: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceCycleListResponse(BaseModel):
    items: List[ComplianceCycleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ComplianceApplicabilityBase(BaseModel):
    client_id: UUID
    compliance_type_id: UUID
    is_applicable: bool = True
    applicability_reason: Optional[str] = None
    auto_generate_cycles: bool = True
    custom_frequency: Optional[ComplianceFrequency] = None
    custom_due_date_rules: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceApplicabilityCreate(ComplianceApplicabilityBase):
    pass


class ComplianceApplicabilityUpdate(BaseModel):
    is_applicable: Optional[bool] = None
    applicability_reason: Optional[str] = None
    auto_generate_cycles: Optional[bool] = None
    custom_frequency: Optional[ComplianceFrequency] = None
    custom_due_date_rules: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceApplicabilityResponse(ComplianceApplicabilityBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True