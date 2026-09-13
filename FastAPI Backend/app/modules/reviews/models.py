import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import (
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    func,
    Enum,
    ARRAY,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User, Team
    from app.modules.workflow.models import WorkflowInstance


class ReviewStage(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REWORK = "rework"
    ESCALATED = "escalated"


class ReviewStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReviewType(str, PyEnum):
    MATTER = "matter"
    COMPLIANCE = "compliance"
    NOTICE = "notice"
    DOCUMENT = "document"
    AUDIT_WORKPAPER = "audit_workpaper"
    TASK = "task"
    CUSTOM = "custom"


class ReviewRequest(Base, TenantBaseModelMixin):
    __tablename__ = "review_requests"
    __table_args__ = (
        Index("ix_review_requests_tenant_source", "tenant_id", "source_object_type", "source_object_id"),
        Index("ix_review_requests_tenant_reviewer", "tenant_id", "reviewer_id"),
        Index("ix_review_requests_tenant_status", "tenant_id", "status"),
        Index("ix_review_requests_tenant_stage", "tenant_id", "stage"),
        UniqueConstraint("tenant_id", "source_object_type", "source_object_id", "stage", name="uq_tenant_source_stage"),
    )

    source_object_type: Mapped[ReviewType] = mapped_column(Enum(ReviewType), nullable=False, index=True)
    source_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    workflow_instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_instances.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    stage: Mapped[ReviewStage] = mapped_column(Enum(ReviewStage), default=ReviewStage.DRAFT, nullable=False, index=True)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)

    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewer_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    submitted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewer_id], lazy="selectin")
    reviewer_team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")
    submitted_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[submitted_by_id], lazy="selectin")
    workflow_instance: Mapped[Optional["WorkflowInstance"]] = relationship("WorkflowInstance", lazy="selectin")
    comments: Mapped[List["ReviewComment"]] = relationship("ReviewComment", back_populates="review_request", lazy="dynamic")
    history: Mapped[List["ReviewHistory"]] = relationship("ReviewHistory", back_populates="review_request", lazy="dynamic")


class ReviewComment(Base, TenantBaseModelMixin):
    __tablename__ = "review_comments"
    __table_args__ = (
        Index("ix_review_comments_tenant_review", "tenant_id", "review_request_id"),
        Index("ix_review_comments_tenant_author", "tenant_id", "author_id"),
    )

    review_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mentions: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_comments.id", ondelete="SET NULL"),
        nullable=True,
    )

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    review_request: Mapped["ReviewRequest"] = relationship("ReviewRequest", back_populates="comments")
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], lazy="selectin")
    parent_comment: Mapped[Optional["ReviewComment"]] = relationship("ReviewComment", remote_side="ReviewComment.id", back_populates="replies", lazy="selectin")
    replies: Mapped[List["ReviewComment"]] = relationship("ReviewComment", back_populates="parent_comment", lazy="dynamic")


class ReviewHistory(Base, TenantBaseModelMixin):
    __tablename__ = "review_history"
    __table_args__ = (
        Index("ix_review_history_tenant_review", "tenant_id", "review_request_id"),
        Index("ix_review_history_tenant_actor", "tenant_id", "actor_id"),
        Index("ix_review_history_created_at", "created_at"),
    )

    review_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    from_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    review_request: Mapped["ReviewRequest"] = relationship("ReviewRequest", back_populates="history")
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id], lazy="selectin")