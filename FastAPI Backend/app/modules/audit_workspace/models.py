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
    from app.modules.clients.models import Client
    from app.modules.users.models import User
    from app.modules.documents.models import Document


class AuditEngagementStatus(str, PyEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class AuditEngagementType(str, PyEnum):
    STATUTORY = "statutory"
    INTERNAL = "internal"
    TAX = "tax"
    SPECIAL = "special"
    FORENSIC = "forensic"


class WorkingPaperStatus(str, PyEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    ARCHIVED = "archived"


class EvidenceStatus(str, PyEnum):
    COLLECTED = "collected"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class AuditReviewStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REWORK = "requires_rework"


class SignOffStatus(str, PyEnum):
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "rejected"


class AuditEngagement(Base, TenantBaseModelMixin):
    __tablename__ = "audit_engagements"
    __table_args__ = (
        Index("ix_audit_engagements_tenant_client", "tenant_id", "client_id"),
        Index("ix_audit_engagements_tenant_status", "tenant_id", "status"),
        Index("ix_audit_engagements_tenant_type", "tenant_id", "engagement_type"),
        Index("ix_audit_engagements_tenant_period", "tenant_id", "period_start", "period_end"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    engagement_type: Mapped[AuditEngagementType] = mapped_column(
        Enum(AuditEngagementType), nullable=False, index=True
    )

    status: Mapped[AuditEngagementStatus] = mapped_column(
        Enum(AuditEngagementStatus), default=AuditEngagementStatus.PLANNING, nullable=False, index=True
    )

    engagement_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    engagement_partner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    engagement_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    planning_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planning_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fieldwork_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fieldwork_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reporting_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    approach: Mapped[str | None] = mapped_column(Text, nullable=True)

    budget_hours: Mapped[float | None] = mapped_column(nullable=True)
    actual_hours: Mapped[float] = mapped_column(default=0.0, nullable=False)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    engagement_partner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[engagement_partner_id], lazy="selectin")
    engagement_manager: Mapped[Optional["User"]] = relationship("User", foreign_keys=[engagement_manager_id], lazy="selectin")
    working_papers: Mapped[list["AuditWorkingPaper"]] = relationship("AuditWorkingPaper", back_populates="engagement", lazy="dynamic", cascade="all, delete-orphan")
    evidence: Mapped[list["AuditEvidence"]] = relationship("AuditEvidence", back_populates="engagement", lazy="dynamic", cascade="all, delete-orphan")
    reviews: Mapped[list["AuditReview"]] = relationship("AuditReview", back_populates="engagement", lazy="dynamic", cascade="all, delete-orphan")
    sign_offs: Mapped[list["AuditSignOff"]] = relationship("AuditSignOff", back_populates="engagement", lazy="dynamic", cascade="all, delete-orphan")


class AuditWorkingPaper(Base, TenantBaseModelMixin):
    __tablename__ = "audit_working_papers"
    __table_args__ = (
        Index("ix_audit_working_papers_tenant_engagement", "tenant_id", "engagement_id"),
        Index("ix_audit_working_papers_tenant_status", "tenant_id", "status"),
        Index("ix_audit_working_papers_tenant_type", "tenant_id", "working_paper_type"),
    )

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    working_paper_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    reference: Mapped[str] = mapped_column(String(100), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[WorkingPaperStatus] = mapped_column(
        Enum(WorkingPaperStatus), default=WorkingPaperStatus.DRAFT, nullable=False, index=True
    )

    prepared_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    budget_hours: Mapped[float | None] = mapped_column(nullable=True)
    actual_hours: Mapped[float] = mapped_column(default=0.0, nullable=False)

    cross_references: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    engagement: Mapped["AuditEngagement"] = relationship("AuditEngagement", back_populates="working_papers", lazy="selectin")
    prepared_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[prepared_by_id], lazy="selectin")
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")
    evidence: Mapped[list["AuditEvidence"]] = relationship("AuditEvidence", back_populates="working_paper", lazy="dynamic", cascade="all, delete-orphan")
    reviews: Mapped[list["AuditReview"]] = relationship("AuditReview", back_populates="working_paper", lazy="dynamic", cascade="all, delete-orphan")


class AuditEvidence(Base, TenantBaseModelMixin):
    __tablename__ = "audit_evidence"
    __table_args__ = (
        Index("ix_audit_evidence_tenant_engagement", "tenant_id", "engagement_id"),
        Index("ix_audit_evidence_tenant_working_paper", "tenant_id", "working_paper_id"),
        Index("ix_audit_evidence_tenant_status", "tenant_id", "status"),
    )

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    working_paper_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_working_papers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus), default=EvidenceStatus.COLLECTED, nullable=False, index=True
    )

    source: Mapped[str] = mapped_column(String(100), nullable=False)

    collected_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reliability: Mapped[str | None] = mapped_column(String(50), nullable=True)

    relevance: Mapped[str | None] = mapped_column(String(50), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    engagement: Mapped["AuditEngagement"] = relationship("AuditEngagement", back_populates="evidence", lazy="selectin")
    working_paper: Mapped[Optional["AuditWorkingPaper"]] = relationship("AuditWorkingPaper", back_populates="evidence", lazy="selectin")
    document: Mapped[Optional["Document"]] = relationship("Document", lazy="selectin")
    collected_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[collected_by_id], lazy="selectin")
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")
    reviews: Mapped[list["AuditReview"]] = relationship("AuditReview", back_populates="evidence", lazy="dynamic", cascade="all, delete-orphan")


class AuditReview(Base, TenantBaseModelMixin):
    __tablename__ = "audit_reviews"
    __table_args__ = (
        Index("ix_audit_reviews_tenant_engagement", "tenant_id", "engagement_id"),
        Index("ix_audit_reviews_tenant_working_paper", "tenant_id", "working_paper_id"),
        Index("ix_audit_reviews_tenant_evidence", "tenant_id", "evidence_id"),
        Index("ix_audit_reviews_tenant_reviewer", "tenant_id", "reviewer_id"),
        Index("ix_audit_reviews_tenant_status", "tenant_id", "status"),
    )

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    working_paper_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_working_papers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    review_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    status: Mapped[AuditReviewStatus] = mapped_column(
        Enum(AuditReviewStatus, name="auditreviewstatus", create_type=False), default=AuditReviewStatus.PENDING, nullable=False, index=True
    )

    findings: Mapped[str | None] = mapped_column(Text, nullable=True)

    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)

    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    engagement: Mapped["AuditEngagement"] = relationship("AuditEngagement", back_populates="reviews", lazy="selectin")
    working_paper: Mapped[Optional["AuditWorkingPaper"]] = relationship("AuditWorkingPaper", back_populates="reviews", lazy="selectin")
    evidence: Mapped[Optional["AuditEvidence"]] = relationship("AuditEvidence", back_populates="reviews", lazy="selectin")
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id], lazy="selectin")


class AuditSignOff(Base, TenantBaseModelMixin):
    __tablename__ = "audit_sign_offs"
    __table_args__ = (
        Index("ix_audit_sign_offs_tenant_engagement", "tenant_id", "engagement_id"),
        Index("ix_audit_sign_offs_tenant_signer", "tenant_id", "signer_id"),
        Index("ix_audit_sign_offs_tenant_status", "tenant_id", "status"),
    )

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    signer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sign_off_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    status: Mapped[SignOffStatus] = mapped_column(
        Enum(SignOffStatus), default=SignOffStatus.PENDING, nullable=False, index=True
    )

    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    engagement: Mapped["AuditEngagement"] = relationship("AuditEngagement", back_populates="sign_offs", lazy="selectin")
    signer: Mapped["User"] = relationship("User", foreign_keys=[signer_id], lazy="selectin")