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
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.documents.models import Document


class ComplianceFrequency(str, PyEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    HALF_YEARLY = "half_yearly"
    EVENT_BASED = "event_based"


class ComplianceStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    REWORK = "rework"
    APPROVED = "approved"
    FILED = "filed"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ComplianceType(Base, TenantBaseModelMixin):
    __tablename__ = "compliance_types"
    __table_args__ = (
        Index("ix_compliance_types_tenant_code", "tenant_id", "code"),
        UniqueConstraint("tenant_id", "code", name="uq_tenant_compliance_code"),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    frequency: Mapped[ComplianceFrequency] = mapped_column(Enum(ComplianceFrequency), nullable=False)

    applicability_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    due_date_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    period_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    default_checklist: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    default_document_requirements: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    default_workflow_stages: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    default_assignment_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    reminder_schedule: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    escalation_rules: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cycles: Mapped[List["ComplianceCycle"]] = relationship("ComplianceCycle", back_populates="compliance_type", lazy="dynamic")
    applicability: Mapped[List["ComplianceApplicability"]] = relationship("ComplianceApplicability", back_populates="compliance_type", lazy="dynamic")


class ComplianceCycle(Base, TenantBaseModelMixin):
    __tablename__ = "compliance_cycles"
    __table_args__ = (
        Index("ix_compliance_cycles_tenant_client", "tenant_id", "client_id"),
        Index("ix_compliance_cycles_tenant_type", "tenant_id", "compliance_type_id"),
        Index("ix_compliance_cycles_tenant_status", "tenant_id", "status"),
        Index("ix_compliance_cycles_tenant_due_date", "tenant_id", "due_date"),
        Index("ix_compliance_cycles_tenant_period", "tenant_id", "period_start", "period_end"),
        UniqueConstraint("tenant_id", "client_id", "compliance_type_id", "period_start", "period_end", name="uq_client_type_period"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compliance_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    extended_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    filing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[ComplianceStatus] = mapped_column(Enum(ComplianceStatus), default=ComplianceStatus.PENDING, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)

    assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    checklist: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    document_requirements: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    workflow_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    workflow_stages: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", back_populates="compliance_cycles", lazy="selectin")
    compliance_type: Mapped["ComplianceType"] = relationship("ComplianceType", back_populates="cycles", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", back_populates="compliance_cycles", lazy="selectin")
    assigned_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_user_id], lazy="selectin")
    assigned_team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="compliance_cycle", lazy="dynamic")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="compliance_cycle", lazy="dynamic")


class ComplianceApplicability(Base, TenantBaseModelMixin):
    __tablename__ = "compliance_applicability"
    __table_args__ = (
        Index("ix_compliance_applicability_tenant_client", "tenant_id", "client_id"),
        UniqueConstraint("tenant_id", "client_id", "compliance_type_id", name="uq_client_compliance_applicability"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compliance_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_applicable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    applicability_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auto_generate_cycles: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    custom_frequency: Mapped[Optional[ComplianceFrequency]] = mapped_column(Enum(ComplianceFrequency), nullable=True)
    custom_due_date_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    compliance_type: Mapped["ComplianceType"] = relationship("ComplianceType", back_populates="applicability", lazy="selectin")