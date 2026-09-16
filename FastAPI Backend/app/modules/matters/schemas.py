from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MatterType(str, Enum):
    ITR = "itr"
    GST = "gst"
    TDS = "tds"
    MCA_ROC = "mca_roc"
    AUDIT = "audit"
    ACCOUNTING = "accounting"
    ADVISORY = "advisory"
    LEGAL = "legal"
    SECRETARIAL = "secretarial"
    VALUATION = "valuation"
    OTHER = "other"


class MatterStatus(str, Enum):
    CREATED = "created"
    INFORMATION_PENDING = "information_pending"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    REWORK = "rework"
    APPROVED = "approved"
    FILED = "filed"
    BILLING_FOLLOWUP = "billing_followup"
    CLOSED = "closed"


class MatterPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class MatterBase(BaseModel):
    client_id: UUID
    matter_type: MatterType
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    matter_number: str | None = Field(None, max_length=100)
    service_id: UUID | None = None
    compliance_cycle_id: UUID | None = None
    priority: MatterPriority = MatterPriority.MEDIUM
    responsible_user_id: UUID | None = None
    responsible_team_id: UUID | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None
    estimated_hours: float | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatterCreate(MatterBase):
    pass


class MatterUpdate(BaseModel):
    matter_type: MatterType | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    matter_number: str | None = Field(None, max_length=100)
    service_id: UUID | None = None
    compliance_cycle_id: UUID | None = None
    status: MatterStatus | None = None
    priority: MatterPriority | None = None
    responsible_user_id: UUID | None = None
    responsible_team_id: UUID | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None
    completed_date: datetime | None = None
    estimated_hours: float | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class MatterResponse(MatterBase):
    id: UUID
    status: MatterStatus
    actual_hours: float | None = None
    completed_date: datetime | None = None
    progress_percentage: int
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MatterListResponse(BaseModel):
    items: list[MatterResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MatterStatusTransition(BaseModel):
    status: MatterStatus
    notes: str | None = None
