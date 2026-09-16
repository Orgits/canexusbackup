from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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
    description: str | None = None
    category: str = Field(..., min_length=1, max_length=100)
    frequency: ComplianceFrequency
    applicability_rules: dict[str, Any] = Field(default_factory=dict)
    due_date_rules: dict[str, Any] = Field(default_factory=dict)
    period_rules: dict[str, Any] = Field(default_factory=dict)
    default_checklist: list[dict[str, Any]] = Field(default_factory=list)
    default_document_requirements: list[dict[str, Any]] = Field(default_factory=list)
    default_workflow_stages: list[dict[str, Any]] = Field(default_factory=list)
    default_assignment_rules: dict[str, Any] = Field(default_factory=dict)
    reminder_schedule: list[dict[str, Any]] = Field(default_factory=list)
    escalation_rules: list[dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComplianceTypeCreate(ComplianceTypeBase):
    pass


class ComplianceTypeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(None, min_length=1, max_length=100)
    frequency: ComplianceFrequency | None = None
    applicability_rules: dict[str, Any] | None = None
    due_date_rules: dict[str, Any] | None = None
    period_rules: dict[str, Any] | None = None
    default_checklist: list[dict[str, Any]] | None = None
    default_document_requirements: list[dict[str, Any]] | None = None
    default_workflow_stages: list[dict[str, Any]] | None = None
    default_assignment_rules: dict[str, Any] | None = None
    reminder_schedule: list[dict[str, Any]] | None = None
    escalation_rules: list[dict[str, Any]] | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


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
    matter_id: UUID | None = None
    period_start: datetime
    period_end: datetime
    due_date: datetime
    extended_due_date: datetime | None = None
    priority: str = "medium"
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    document_requirements: list[dict[str, Any]] = Field(default_factory=list)
    workflow_stages: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComplianceCycleCreate(ComplianceCycleBase):
    pass


class ComplianceCycleUpdate(BaseModel):
    matter_id: UUID | None = None
    extended_due_date: datetime | None = None
    filing_date: datetime | None = None
    status: ComplianceStatus | None = None
    priority: str | None = None
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    checklist: list[dict[str, Any]] | None = None
    document_requirements: list[dict[str, Any]] | None = None
    workflow_stage: str | None = None
    workflow_stages: list[dict[str, Any]] | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class ComplianceCycleResponse(ComplianceCycleBase):
    id: UUID
    status: ComplianceStatus
    filing_date: datetime | None = None
    workflow_stage: str | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceCycleListResponse(BaseModel):
    items: list[ComplianceCycleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ComplianceApplicabilityBase(BaseModel):
    client_id: UUID
    compliance_type_id: UUID
    is_applicable: bool = True
    applicability_reason: str | None = None
    auto_generate_cycles: bool = True
    custom_frequency: ComplianceFrequency | None = None
    custom_due_date_rules: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComplianceApplicabilityCreate(ComplianceApplicabilityBase):
    pass


class ComplianceApplicabilityUpdate(BaseModel):
    is_applicable: bool | None = None
    applicability_reason: str | None = None
    auto_generate_cycles: bool | None = None
    custom_frequency: ComplianceFrequency | None = None
    custom_due_date_rules: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ComplianceApplicabilityResponse(ComplianceApplicabilityBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
