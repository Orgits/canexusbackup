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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User, Team
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.documents.models import Document
    from app.modules.workflow.models import WorkflowInstance
    from app.modules.reviews.models import ReviewRequest


class NoticeAuthority(str, PyEnum):
    INCOME_TAX = "income_tax"
    GST = "gst"
    MCA = "mca"
    ROC = "roc"
    CUSTOMS = "customs"
    PROVIDENT_FUND = "provident_fund"
    ESI = "esi"
    LABOUR = "labour"
    POLLUTION_CONTROL = "pollution_control"
    FIRE_DEPT = "fire_dept"
    MUNICIPAL = "municipal"
    POLICE = "police"
    COURT = "court"
    TRIBUNAL = "tribunal"
    OTHER = "other"


class NoticeType(str, PyEnum):
    SHOW_CAUSE = "show_cause"
    DEMAND = "demand"
    SCRUTINY = "scrutiny"
    ASSESSMENT = "assessment"
    PENALTY = "penalty"
    PROSECUTION = "prosecution"
    SUMMONS = "summons"
    INQUIRY = "inquiry"
    SURVEY = "survey"
    SEARCH = "search"
    SEIZURE = "seizure"
    RECTIFICATION = "rectification"
    APPEAL = "appeal"
    REVISION = "revision"
    REFUND = "refund"
    INTIMATION = "intimation"
    COMPLIANCE = "compliance"
    OTHER = "other"


class NoticeStatus(str, PyEnum):
    RECEIVED = "received"
    ACKNOWLEDGED = "acknowledged"
    UNDER_REVIEW = "under_review"
    RESPONSE_DRAFTING = "response_drafting"
    RESPONSE_REVIEW = "response_review"
    RESPONSE_APPROVED = "response_approved"
    RESPONDED = "responded"
    HEARING_SCHEDULED = "hearing_scheduled"
    HEARING_COMPLETED = "hearing_completed"
    ORDER_RECEIVED = "order_received"
    APPEAL_FILED = "appeal_filed"
    CLOSED = "closed"
    ESCALATED = "escalated"


class NoticePriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class Notice(Base, TenantBaseModelMixin):
    __tablename__ = "notices"
    __table_args__ = (
        Index("ix_notices_tenant_client", "tenant_id", "client_id"),
        Index("ix_notices_tenant_authority", "tenant_id", "authority"),
        Index("ix_notices_tenant_status", "tenant_id", "status"),
        Index("ix_notices_tenant_due_date", "tenant_id", "response_deadline"),
        Index("ix_notices_tenant_ref_number", "tenant_id", "reference_number"),
        Index("ix_notices_tenant_assignee", "tenant_id", "assignee_id"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_instances.id", ondelete="SET NULL"),
        nullable=True,
    )

    authority: Mapped[NoticeAuthority] = mapped_column(Enum(NoticeAuthority), nullable=False, index=True)
    authority_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    notice_type: Mapped[NoticeType] = mapped_column(Enum(NoticeType), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    received_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    notice_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    response_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    extended_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[NoticeStatus] = mapped_column(Enum(NoticeStatus), default=NoticeStatus.RECEIVED, nullable=False, index=True)
    priority: Mapped[NoticePriority] = mapped_column(Enum(NoticePriority), default=NoticePriority.MEDIUM, nullable=False)

    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    escalated_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Financial impact
    demand_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    penalty_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    interest_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Response tracking
    response_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_filed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    response_acknowledgment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    response_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Outcome
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    order_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    appeal_filed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    appeal_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Closure
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    closure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    workflow_instance: Mapped[Optional["WorkflowInstance"]] = relationship("WorkflowInstance", lazy="selectin")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id], lazy="selectin")
    team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")
    escalated_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[escalated_to_id], lazy="selectin")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="notice", lazy="dynamic")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="notice", lazy="dynamic")
    review_request: Mapped[Optional["ReviewRequest"]] = relationship("ReviewRequest", lazy="selectin")
    escalation_history: Mapped[List["NoticeEscalation"]] = relationship("NoticeEscalation", back_populates="notice", lazy="dynamic")


class NoticeEscalation(Base, TenantBaseModelMixin):
    __tablename__ = "notice_escalations"
    __table_args__ = (
        Index("ix_notice_escalations_tenant_notice", "tenant_id", "notice_id"),
        Index("ix_notice_escalations_tenant_from", "tenant_id", "escalated_from_id"),
        Index("ix_notice_escalations_tenant_to", "tenant_id", "escalated_to_id"),
    )

    notice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    escalated_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    escalated_to_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    escalated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    new_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    notice: Mapped["Notice"] = relationship("Notice", back_populates="escalation_history")
    escalated_from: Mapped[Optional["User"]] = relationship("User", foreign_keys=[escalated_from_id], lazy="selectin")
    escalated_to: Mapped["User"] = relationship("User", foreign_keys=[escalated_to_id], lazy="selectin")
    escalated_by: Mapped["User"] = relationship("User", foreign_keys=[escalated_by_id], lazy="selectin")