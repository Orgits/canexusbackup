from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AIModelType(str, Enum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question_answering"
    SENTIMENT = "sentiment"
    ENTITY_RECOGNITION = "entity_recognition"
    CUSTOM = "custom"


class AIModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    CUSTOM = "custom"


class AIProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    model_type: AIModelType
    provider: AIModelProvider
    model_name: str = Field(..., max_length=255)
    model_version: str | None = Field(None, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    is_default: bool = False
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    rate_limit_per_hour: int = Field(default=1000, ge=1, le=100000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIModelCreate(AIModelBase):
    pass


class AIModelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    rate_limit_per_minute: int | None = Field(None, ge=1, le=10000)
    rate_limit_per_hour: int | None = Field(None, ge=1, le=100000)
    metadata: dict[str, Any] | None = None


class AIModelResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    model_type: AIModelType
    provider: AIModelProvider
    model_name: str
    model_version: str | None
    config: dict[str, Any]
    is_active: bool
    is_default: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    metadata: dict[str, Any]
    tenant_id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIModelListResponse(BaseModel):
    items: list["AIModelResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class AIProcessingJobBase(BaseModel):
    document_id: UUID
    model_id: UUID
    prompt: str | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)


class AIProcessingJobCreate(AIProcessingJobBase):
    pass


class AIProcessingJobUpdate(BaseModel):
    prompt: str | None = None
    input_data: dict[str, Any] | None = None


class AIProcessingJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    model_id: UUID
    prompt: str | None
    input_data: dict[str, Any]
    status: str
    output_data: dict[str, Any]
    confidence_score: float | None
    processing_time_ms: int
    tokens_used: int
    cost: float | None
    currency: str
    error_message: str | None
    retry_count: int
    max_retries: int
    started_at: datetime | None
    completed_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIProcessingJobListResponse(BaseModel):
    items: list["AIProcessingJobResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class AIConfidenceThresholdBase(BaseModel):
    model_type: str = Field(..., max_length=50)
    auto_approve_threshold: float = Field(default=0.95, ge=0, le=1)
    auto_reject_threshold: float = Field(default=0.3, ge=0, le=1)
    requires_review_threshold: float = Field(default=0.7, ge=0, le=1)
    auto_approve_action: str = Field(default="approve", max_length=50)
    auto_reject_action: str = Field(default="reject", max_length=50)
    requires_review_action: str = Field(default="review", max_length=50)
    is_active: bool = True


class AIConfidenceThresholdCreate(AIConfidenceThresholdBase):
    pass


class AIConfidenceThresholdUpdate(BaseModel):
    auto_approve_threshold: float | None = Field(None, ge=0, le=1)
    auto_reject_threshold: float | None = Field(None, ge=0, le=1)
    requires_review_threshold: float | None = Field(None, ge=0, le=1)
    auto_approve_action: str | None = Field(None, max_length=50)
    auto_reject_action: str | None = Field(None, max_length=50)
    requires_review_action: str | None = Field(None, max_length=50)
    is_active: bool | None = None


class AIConfidenceThresholdResponse(BaseModel):
    id: UUID
    model_type: str
    auto_approve_threshold: float
    auto_reject_threshold: float
    requires_review_threshold: float
    auto_approve_action: str
    auto_reject_action: str
    requires_review_action: str
    is_active: bool
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIConfidenceThresholdListResponse(BaseModel):
    items: list["AIConfidenceThresholdResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class AIReviewTaskBase(BaseModel):
    job_id: UUID
    assignee_id: UUID | None = None


class AIReviewTaskCreate(AIReviewTaskBase):
    pass


class AIReviewTaskUpdate(BaseModel):
    status: str | None = None
    reviewer_notes: str | None = None
    original_confidence: float | None = Field(None, ge=0, le=1)
    final_confidence: float | None = Field(None, ge=0, le=1)
    action_taken: str | None = Field(None, max_length=50)
    action_reason: str | None = None


class AIReviewTaskResponse(BaseModel):
    id: UUID
    job_id: UUID
    assignee_id: UUID | None
    status: str
    assigned_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    reviewer_notes: str | None
    original_confidence: float | None
    final_confidence: float | None
    action_taken: str | None
    action_reason: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIReviewTaskListResponse(BaseModel):
    items: list["AIReviewTaskResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class AIProcessRequest(BaseModel):
    document_id: UUID
    model_id: UUID
    prompt: str | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)