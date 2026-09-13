from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


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
    description: Optional[str] = None
    matter_number: Optional[str] = Field(None, max_length=100)
    service_id: Optional[UUID] = None
    compliance_cycle_id: Optional[UUID] = None
    priority: MatterPriority = MatterPriority.MEDIUM
    responsible_user_id: Optional[UUID] = None
    responsible_team_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MatterCreate(MatterBase):
    pass


class MatterUpdate(BaseModel):
    matter_type: Optional[MatterType] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    matter_number: Optional[str] = Field(None, max_length=100)
    service_id: Optional[UUID] = None
    compliance_cycle_id: Optional[UUID] = None
    status: Optional[MatterStatus] = None
    priority: Optional[MatterPriority] = None
    responsible_user_id: Optional[UUID] = None
    responsible_team_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class MatterResponse(MatterBase):
    id: UUID
    status: MatterStatus
    actual_hours: Optional[float] = None
    completed_date: Optional[datetime] = None
    progress_percentage: int
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MatterListResponse(BaseModel):
    items: List[MatterResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MatterStatusTransition(BaseModel):
    status: MatterStatus
    notes: Optional[str] = None