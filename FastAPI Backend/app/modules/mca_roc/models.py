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
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.documents.models import Document
    from app.modules.compliance.models import ComplianceCycle
    from app.modules.workflow.models import WorkflowInstance


class MCAEntityType(str, PyEnum):
    COMPANY = "company"
    LLP = "llp"


class MCAFilingType(str, PyEnum):
    # Company annual filings
    AOC_4 = "aoc_4"
    AOC_4_XBRL = "aoc_4_xbrl"
    MGT_7 = "mgt_7"
    MGT_7A = "mgt_7a"
    ADT_1 = "adt_1"
    DPT_3 = "dpt_3"
    MSME_1 = "msme_1"
    DIR_3_KYC = "dir_3_kyc"
    # LLP annual filings
    FORM_8 = "form_8"
    FORM_11 = "form_11"
    FORM_3 = "form_3"
    FORM_4 = "form_4"
    # Event-based filings
    SH_7 = "sh_7"
    SH_8 = "sh_8"
    MGT_14 = "mgt_14"
    PAS_3 = "pas_3"
    DIR_12 = "dir_12"
    INC_22 = "inc_22"
    INC_28 = "inc_28"
    # Other
    OTHER = "other"


class MCAFilingCategory(str, PyEnum):
    ANNUAL = "annual"
    EVENT_BASED = "event_based"
    OTHER = "other"


class MCAStatus(str, PyEnum):
    PENDING = "pending"
    DOCUMENT_COLLECTION = "document_collection"
    PREPARATION = "preparation"
    REVIEW = "review"
    BOARD_APPROVAL = "board_approval"
    AGM_COMPLETED = "agm_completed"
    READY_FOR_FILING = "ready_for_filing"
    FILED = "filed"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFECTIVE = "defective"
    RESUBMITTED = "resubmitted"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class MCAFilingCycle(Base, TenantBaseModelMixin):
    __tablename__ = "mca_filing_cycles"
    __table_args__ = (
        Index("ix_mca_cycles_tenant_client", "tenant_id", "client_id"),
        Index("ix_mca_cycles_tenant_filing", "tenant_id", "filing_type"),
        Index("ix_mca_cycles_tenant_fy", "tenant_id", "financial_year"),
        Index("ix_mca_cycles_tenant_status", "tenant_id", "status"),
        Index("ix_mca_cycles_tenant_due_date", "tenant_id", "due_date"),
        UniqueConstraint("tenant_id", "client_id", "filing_type", "financial_year", "event_date", name="uq_mca_client_filing_fy_event"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compliance_cycle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_cycles.id", ondelete="SET NULL"),
        nullable=True,
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

    entity_type: Mapped[MCAEntityType] = mapped_column(Enum(MCAEntityType), nullable=False, index=True)
    filing_type: Mapped[MCAFilingType] = mapped_column(Enum(MCAFilingType), nullable=False, index=True)
    filing_category: Mapped[MCAFilingCategory] = mapped_column(Enum(MCAFilingCategory), nullable=False, index=True)

    financial_year: Mapped[Optional[str]] = mapped_column(String(9), nullable=True, index=True)
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    event_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    extended_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    agm_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    filing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[MCAStatus] = mapped_column(Enum(MCAStatus), default=MCAStatus.PENDING, nullable=False, index=True)
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

    # Company/LLP specific fields
    cin_llpin: Mapped[Optional[str]] = mapped_column(String(21), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    roc_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Filing specific data
    srn: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    acknowledgment_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    challan_amount: Mapped[float] = mapped_column(default=0, nullable=False)
    additional_fee: Mapped[float] = mapped_column(default=0, nullable=False)

    # Checklist and documents
    checklist: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    document_requirements: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    workflow_stages: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    # Missing information tracking
    missing_info: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    missing_info_count: Mapped[int] = mapped_column(default=0, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    compliance_cycle: Mapped[Optional["ComplianceCycle"]] = relationship("ComplianceCycle", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    workflow_instance: Mapped[Optional["WorkflowInstance"]] = relationship("WorkflowInstance", lazy="selectin")
    assigned_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_user_id], lazy="selectin")
    assigned_team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="mca_cycle", lazy="dynamic")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="mca_cycle", lazy="dynamic")


class MCAFilingConfig(Base, TenantBaseModelMixin):
    __tablename__ = "mca_filing_configs"
    __table_args__ = (
        Index("ix_mca_configs_tenant_type", "tenant_id", "filing_type"),
        UniqueConstraint("tenant_id", "filing_type", name="uq_tenant_mca_filing_type"),
    )

    filing_type: Mapped[MCAFilingType] = mapped_column(Enum(MCAFilingType), nullable=False, index=True)
    entity_type: Mapped[MCAEntityType] = mapped_column(Enum(MCAEntityType), nullable=False)
    filing_category: Mapped[MCAFilingCategory] = mapped_column(Enum(MCAFilingCategory), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    form_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Due date rules
    due_date_rule: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    period_rule: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_annual: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Default checklist and documents
    default_checklist: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    default_document_requirements: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    default_workflow_stages: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    # Fee structure
    base_fee: Mapped[float] = mapped_column(default=0, nullable=False)
    additional_fee_per_day: Mapped[float] = mapped_column(default=0, nullable=False)
    max_additional_fee: Mapped[float] = mapped_column(default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )