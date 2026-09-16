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
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.billing.models import Invoice
    from app.modules.clients.models import Client
    from app.modules.compliance.models import ComplianceCycle
    from app.modules.documents.models import Document
    from app.modules.tasks.models import Task
    from app.modules.users.models import Team, User


class MatterType(str, PyEnum):
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


class MatterStatus(str, PyEnum):
    CREATED = "created"
    INFORMATION_PENDING = "information_pending"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    REWORK = "rework"
    APPROVED = "approved"
    FILED = "filed"
    BILLING_FOLLOWUP = "billing_followup"
    CLOSED = "closed"


class MatterPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class Matter(Base, TenantBaseModelMixin):
    __tablename__ = "matters"
    __table_args__ = (
        Index("ix_matters_tenant_client", "tenant_id", "client_id"),
        Index("ix_matters_tenant_status", "tenant_id", "status"),
        Index("ix_matters_tenant_type", "tenant_id", "matter_type"),
        Index("ix_matters_tenant_due_date", "tenant_id", "due_date"),
        Index("ix_matters_tenant_responsible_user", "tenant_id", "responsible_user_id"),
        Index("ix_matters_tenant_responsible_team", "tenant_id", "responsible_team_id"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matter_type: Mapped[MatterType] = mapped_column(Enum(MatterType), nullable=False, index=True)
    status: Mapped[MatterStatus] = mapped_column(Enum(MatterStatus), default=MatterStatus.CREATED, nullable=False, index=True)
    priority: Mapped[MatterPriority] = mapped_column(Enum(MatterPriority), default=MatterPriority.MEDIUM, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    matter_number: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_services.id", ondelete="SET NULL"),
        nullable=True,
    )
    compliance_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_cycles.id", ondelete="SET NULL"),
        nullable=True,
    )

    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    responsible_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    estimated_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    actual_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, default=0)

    progress_percentage: Mapped[int] = mapped_column(default=0, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", back_populates="matters", lazy="selectin")
    service: Mapped[Optional["ClientService"]] = relationship("ClientService", lazy="selectin")
    compliance_cycle: Mapped[Optional["ComplianceCycle"]] = relationship("ComplianceCycle", foreign_keys=[compliance_cycle_id], back_populates="matters", lazy="selectin")
    responsible_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[responsible_user_id], lazy="selectin")
    responsible_team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[responsible_team_id], lazy="selectin")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="matter", lazy="dynamic")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="matter", lazy="dynamic")
    compliance_cycles: Mapped[list["ComplianceCycle"]] = relationship("ComplianceCycle", foreign_keys="ComplianceCycle.matter_id", back_populates="matter", lazy="dynamic")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="matter", lazy="dynamic")
