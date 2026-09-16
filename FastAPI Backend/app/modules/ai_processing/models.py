import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.documents.models import Document
    from app.modules.users.models import User


class AIModelType(str, PyEnum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question_answering"
    SENTIMENT = "sentiment"
    ENTITY_RECOGNITION = "entity_recognition"
    CUSTOM = "custom"


class AIModelProvider(str, PyEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    CUSTOM = "custom"


class AIProcessingStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIModel(Base, TenantBaseModelMixin):
    __tablename__ = "ai_models"
    __table_args__ = (
        Index("ix_ai_models_tenant_type", "tenant_id", "model_type"),
        Index("ix_ai_models_tenant_provider", "tenant_id", "provider"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_type: Mapped[AIModelType] = mapped_column(Enum(AIModelType), nullable=False, index=True)
    provider: Mapped[AIModelProvider] = mapped_column(Enum(AIModelProvider), nullable=False, index=True)

    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    credentials: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    rate_limit_per_minute: Mapped[int] = mapped_column(default=60, nullable=False)
    rate_limit_per_hour: Mapped[int] = mapped_column(default=1000, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    processing_jobs: Mapped[list["AIProcessingJob"]] = relationship("AIProcessingJob", back_populates="model", lazy="dynamic")


class AIProcessingJob(Base, TenantBaseModelMixin):
    __tablename__ = "ai_processing_jobs"
    __table_args__ = (
        Index("ix_ai_processing_jobs_tenant_document", "tenant_id", "document_id"),
        Index("ix_ai_processing_jobs_tenant_model", "tenant_id", "model_id"),
        Index("ix_ai_processing_jobs_tenant_status", "tenant_id", "status"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    status: Mapped[AIProcessingStatus] = mapped_column(
        Enum(AIProcessingStatus), default=AIProcessingStatus.PENDING, nullable=False, index=True
    )

    output_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)

    processing_time_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    tokens_used: Mapped[int] = mapped_column(default=0, nullable=False)
    cost: Mapped[float | None] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id], lazy="selectin")
    model: Mapped["AIModel"] = relationship("AIModel", foreign_keys=[model_id], lazy="selectin")


class AIConfidenceThreshold(Base, TenantBaseModelMixin):
    __tablename__ = "ai_confidence_thresholds"
    __table_args__ = (
        Index("ix_ai_confidence_thresholds_tenant_type", "tenant_id", "model_type"),
    )

    model_type: Mapped[AIModelType] = mapped_column(Enum(AIModelType), nullable=False, index=True)

    auto_approve_threshold: Mapped[float] = mapped_column(default=0.95, nullable=False)
    auto_reject_threshold: Mapped[float] = mapped_column(default=0.3, nullable=False)
    requires_review_threshold: Mapped[float] = mapped_column(default=0.7, nullable=False)

    auto_approve_action: Mapped[str] = mapped_column(String(50), default="approve", nullable=False)
    auto_reject_action: Mapped[str] = mapped_column(String(50), default="reject", nullable=False)
    requires_review_action: Mapped[str] = mapped_column(String(50), default="review", nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")


class AIReviewTask(Base, TenantBaseModelMixin):
    __tablename__ = "ai_review_tasks"
    __table_args__ = (
        Index("ix_ai_review_tasks_tenant_job", "tenant_id", "job_id"),
        Index("ix_ai_review_tasks_tenant_assignee", "tenant_id", "assignee_id"),
        Index("ix_ai_review_tasks_tenant_status", "tenant_id", "status"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_confidence: Mapped[float | None] = mapped_column(nullable=True)
    final_confidence: Mapped[float | None] = mapped_column(nullable=True)

    action_taken: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    job: Mapped["AIProcessingJob"] = relationship("AIProcessingJob", foreign_keys=[job_id], lazy="selectin")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id], lazy="selectin")