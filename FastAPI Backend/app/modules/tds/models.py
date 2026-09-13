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
    Numeric,
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


class TDSFormType(str, PyEnum):
    FORM_24Q = "24q"
    FORM_26Q = "26q"
    FORM_27Q = "27q"
    FORM_27EQ = "27eq"


class TDSQuarter(str, PyEnum):
    Q1 = "q1"
    Q2 = "q2"
    Q3 = "q3"
    Q4 = "q4"


class TDSDeducteeType(str, PyEnum):
    SALARY = "salary"
    NON_SALARY = "non_salary"
    NRI = "nri"
    TCS = "tcs"


class TDSStatus(str, PyEnum):
    PENDING = "pending"
    DATA_COLLECTION = "data_collection"
    VALIDATION = "validation"
    READY_FOR_FILING = "ready_for_filing"
    FILED = "filed"
    PROCESSED = "processed"
    DEFAULTER = "defaulter"
    CANCELLED = "cancelled"


class TDSChallanStatus(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    VERIFIED = "verified"
    MISMATCH = "mismatch"


class TDSComplianceCycle(Base, TenantBaseModelMixin):
    __tablename__ = "tds_compliance_cycles"
    __table_args__ = (
        Index("ix_tds_cycles_tenant_client", "tenant_id", "client_id"),
        Index("ix_tds_cycles_tenant_form", "tenant_id", "form_type"),
        Index("ix_tds_cycles_tenant_quarter", "tenant_id", "financial_year", "quarter"),
        Index("ix_tds_cycles_tenant_status", "tenant_id", "status"),
        Index("ix_tds_cycles_tenant_due_date", "tenant_id", "due_date"),
        UniqueConstraint("tenant_id", "client_id", "form_type", "financial_year", "quarter", name="uq_tds_client_form_fy_quarter"),
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

    form_type: Mapped[TDSFormType] = mapped_column(Enum(TDSFormType), nullable=False, index=True)
    financial_year: Mapped[str] = mapped_column(String(9), nullable=False, index=True)
    quarter: Mapped[TDSQuarter] = mapped_column(Enum(TDSQuarter), nullable=False, index=True)

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    extended_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    filing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[TDSStatus] = mapped_column(Enum(TDSStatus), default=TDSStatus.PENDING, nullable=False, index=True)
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

    # TDS-specific fields
    tan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    total_deductees: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tax_deducted: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total_tax_deposited: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    token_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    acknowledgment_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

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
    challans: Mapped[List["TDSChallan"]] = relationship("TDSChallan", back_populates="tds_cycle", lazy="dynamic")
    deductees: Mapped[List["TDSDeductee"]] = relationship("TDSDeductee", back_populates="tds_cycle", lazy="dynamic")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="tds_cycle", lazy="dynamic")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="tds_cycle", lazy="dynamic")


class TDSChallan(Base, TenantBaseModelMixin):
    __tablename__ = "tds_challans"
    __table_args__ = (
        Index("ix_tds_challans_tenant_cycle", "tenant_id", "tds_cycle_id"),
        Index("ix_tds_challans_tenant_cin", "tenant_id", "cin"),
        Index("ix_tds_challans_tenant_status", "tenant_id", "status"),
        Index("ix_tds_challans_tenant_date", "tenant_id", "deposit_date"),
    )

    tds_cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tds_compliance_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cin: Mapped[str] = mapped_column(String(50), nullable=False)
    bsr_code: Mapped[str] = mapped_column(String(7), nullable=False)
    deposit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    challan_serial: Mapped[str] = mapped_column(String(5), nullable=False)

    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    surcharge: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    education_cess: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    interest: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    penalty: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    fee: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)

    status: Mapped[TDSChallanStatus] = mapped_column(Enum(TDSChallanStatus), default=TDSChallanStatus.PENDING, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tds_cycle: Mapped["TDSComplianceCycle"] = relationship("TDSComplianceCycle", back_populates="challans")


class TDSDeductee(Base, TenantBaseModelMixin):
    __tablename__ = "tds_deductees"
    __table_args__ = (
        Index("ix_tds_deductees_tenant_cycle", "tenant_id", "tds_cycle_id"),
        Index("ix_tds_deductees_tenant_pan", "tenant_id", "deductee_pan"),
        Index("ix_tds_deductees_tenant_type", "tenant_id", "deductee_type"),
    )

    tds_cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tds_compliance_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deductee_type: Mapped[TDSDeducteeType] = mapped_column(Enum(TDSDeducteeType), nullable=False, index=True)
    deductee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deductee_pan: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    deductee_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    section_code: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    tax_deducted: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    tax_deposited: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    deduction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deposit_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    certificate_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tds_cycle: Mapped["TDSComplianceCycle"] = relationship("TDSComplianceCycle", back_populates="deductees")