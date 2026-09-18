from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEngagementStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class AuditEngagementType(str, Enum):
    STATUTORY = "statutory"
    INTERNAL = "internal"
    TAX = "tax"
    SPECIAL = "special"
    FORENSIC = "forensic"


class WorkingPaperStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    ARCHIVED = "archived"


class EvidenceStatus(str, Enum):
    COLLECTED = "collected"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class AuditReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REWORK = "requires_rework"


class SignOffStatus(str, Enum):
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "rejected"


class AuditEngagementBase(BaseModel):
    client_id: UUID
    engagement_type: AuditEngagementType
    engagement_number: str = Field(..., min_length=1, max_length=100)
    period_start: datetime
    period_end: datetime
    engagement_partner_id: UUID | None = None
    engagement_manager_id: UUID | None = None
    planning_start_date: datetime | None = None
    planning_end_date: datetime | None = None
    fieldwork_start_date: datetime | None = None
    fieldwork_end_date: datetime | None = None
    reporting_date: datetime | None = None
    scope: str | None = None
    objectives: str | None = None
    approach: str | None = None
    budget_hours: float | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class AuditEngagementCreate(AuditEngagementBase):
    pass


class AuditEngagementUpdate(BaseModel):
    engagement_type: AuditEngagementType | None = None
    status: str | None = None
    engagement_number: str | None = Field(None, min_length=1, max_length=100)
    period_start: datetime | None = None
    period_end: datetime | None = None
    engagement_partner_id: UUID | None = None
    engagement_manager_id: UUID | None = None
    planning_start_date: datetime | None = None
    planning_end_date: datetime | None = None
    fieldwork_start_date: datetime | None = None
    fieldwork_end_date: datetime | None = None
    reporting_date: datetime | None = None
    scope: str | None = None
    objectives: str | None = None
    approach: str | None = None
    budget_hours: float | None = None
    extra_metadata: dict[str, Any] | None = None


class AuditEngagementResponse(BaseModel):
    id: UUID
    client_id: UUID
    engagement_type: AuditEngagementType
    status: str
    engagement_number: str
    period_start: datetime
    period_end: datetime
    engagement_partner_id: UUID | None
    engagement_manager_id: UUID | None
    planning_start_date: datetime | None
    planning_end_date: datetime | None
    fieldwork_start_date: datetime | None
    fieldwork_end_date: datetime | None
    reporting_date: datetime | None
    scope: str | None
    objectives: str | None
    approach: str | None
    budget_hours: float | None
    actual_hours: float
    completed_at: datetime | None
    completed_by: UUID | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class AuditEngagementDetailResponse(AuditEngagementResponse):
    client: Any | None = None
    engagement_partner: Any | None = None
    engagement_manager: Any | None = None
    working_papers_count: int = 0
    evidence_count: int = 0
    reviews_count: int = 0
    sign_offs_count: int = 0


class AuditEngagementListResponse(BaseModel):
    items: list[AuditEngagementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditEngagementTransitionRequest(BaseModel):
    new_status: str = Field(..., pattern="^(planning|active|in_review|completed|archived|cancelled)$")
    comment: str | None = None


class WorkingPaperStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    ARCHIVED = "archived"


class AuditWorkingPaperBase(BaseModel):
    engagement_id: UUID
    working_paper_type: str = Field(..., min_length=1, max_length=100)
    reference: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    prepared_by_id: UUID | None = None
    budget_hours: float | None = None
    cross_references: list[UUID] = Field(default_factory=list)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class AuditWorkingPaperCreate(AuditWorkingPaperBase):
    pass


class AuditWorkingPaperUpdate(BaseModel):
    working_paper_type: str | None = Field(None, min_length=1, max_length=100)
    reference: str | None = Field(None, min_length=1, max_length=100)
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    prepared_by_id: UUID | None = None
    reviewed_by_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    budget_hours: float | None = None
    actual_hours: float | None = None
    cross_references: list[UUID] | None = None
    extra_metadata: dict[str, Any] | None = None


class AuditWorkingPaperResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    working_paper_type: str
    reference: str
    title: str
    description: str | None
    status: str
    prepared_by_id: UUID | None
    reviewed_by_id: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    budget_hours: float | None
    actual_hours: float
    cross_references: list[UUID]
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class AuditWorkingPaperDetailResponse(AuditWorkingPaperResponse):
    engagement: Any | None = None
    prepared_by: Any | None = None
    reviewed_by: Any | None = None
    evidence_count: int = 0
    reviews_count: int = 0


class AuditWorkingPaperListResponse(BaseModel):
    items: list[AuditWorkingPaperResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EvidenceStatus(str, Enum):
    COLLECTED = "collected"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class AuditEvidenceBase(BaseModel):
    engagement_id: UUID
    working_paper_id: UUID | None = None
    document_id: UUID | None = None
    evidence_type: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    source: str = Field(..., min_length=1, max_length=100)
    collected_by_id: UUID | None = None
    collected_at: datetime | None = None
    reliability: str | None = Field(None, max_length=50)
    relevance: str | None = Field(None, max_length=50)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class AuditEvidenceCreate(AuditEvidenceBase):
    pass


class AuditEvidenceUpdate(BaseModel):
    working_paper_id: UUID | None = None
    document_id: UUID | None = None
    evidence_type: str | None = Field(None, min_length=1, max_length=100)
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    source: str | None = Field(None, min_length=1, max_length=100)
    collected_by_id: UUID | None = None
    collected_at: datetime | None = None
    reviewed_by_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    reliability: str | None = Field(None, max_length=50)
    relevance: str | None = Field(None, max_length=50)
    extra_metadata: dict[str, Any] | None = None


class AuditEvidenceResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    working_paper_id: UUID | None
    document_id: UUID | None
    evidence_type: str
    title: str
    description: str | None
    status: str
    source: str
    collected_by_id: UUID | None
    collected_at: datetime | None
    reviewed_by_id: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    reliability: str | None
    relevance: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class AuditEvidenceDetailResponse(AuditEvidenceResponse):
    engagement: Any | None = None
    working_paper: Any | None = None
    document: Any | None = None
    collected_by: Any | None = None
    reviewed_by: Any | None = None
    reviews_count: int = 0


class AuditEvidenceListResponse(BaseModel):
    items: list[AuditEvidenceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REWORK = "requires_rework"


class AuditReviewBase(BaseModel):
    engagement_id: UUID
    working_paper_id: UUID | None = None
    evidence_id: UUID | None = None
    reviewer_id: UUID
    review_type: str = Field(..., min_length=1, max_length=50)
    findings: str | None = None
    recommendations: str | None = None
    review_notes: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class AuditReviewCreate(AuditReviewBase):
    pass


class AuditReviewUpdate(BaseModel):
    working_paper_id: UUID | None = None
    evidence_id: UUID | None = None
    reviewer_id: UUID | None = None
    review_type: str | None = Field(None, min_length=1, max_length=50)
    status: str | None = None
    findings: str | None = None
    recommendations: str | None = None
    review_notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    extra_metadata: dict[str, Any] | None = None


class AuditReviewResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    working_paper_id: UUID | None
    evidence_id: UUID | None
    reviewer_id: UUID
    review_type: str
    status: str
    findings: str | None
    recommendations: str | None
    review_notes: str | None
    started_at: datetime | None
    completed_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class AuditReviewDetailResponse(AuditReviewResponse):
    engagement: Any | None = None
    working_paper: Any | None = None
    evidence: Any | None = None
    reviewer: Any | None = None


class AuditReviewListResponse(BaseModel):
    items: list[AuditReviewResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SignOffStatus(str, Enum):
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "rejected"


class AuditSignOffBase(BaseModel):
    engagement_id: UUID
    signer_id: UUID
    sign_off_type: str = Field(..., min_length=1, max_length=50)
    comments: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class AuditSignOffCreate(AuditSignOffBase):
    pass


class AuditSignOffUpdate(BaseModel):
    signer_id: UUID | None = None
    sign_off_type: str | None = Field(None, min_length=1, max_length=50)
    status: str | None = None
    signed_at: datetime | None = None
    comments: str | None = None
    extra_metadata: dict[str, Any] | None = None


class AuditSignOffResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    signer_id: UUID
    sign_off_type: str
    status: str
    signed_at: datetime | None
    comments: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class AuditSignOffDetailResponse(AuditSignOffResponse):
    engagement: Any | None = None
    signer: Any | None = None


class AuditSignOffListResponse(BaseModel):
    items: list[AuditSignOffResponse]
    total: int
    page: int
    page_size: int
    total_pages: int