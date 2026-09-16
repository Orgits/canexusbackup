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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin
from app.core.database.encryption_mixin import PIIEncryptionMixin, encrypted_column

if TYPE_CHECKING:
    from app.modules.clients.models import Client
    from app.modules.compliance.models import ComplianceCycle
    from app.modules.matters.models import Matter
    from app.modules.users.models import Team, User
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


class TDSComplianceCycle(Base, TenantBaseModelMixin, PIIEncryptionMixin):
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
    compliance_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    matter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_instance_id: Mapped[uuid.UUID | None] = mapped_column(
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
    extended_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[TDSStatus] = mapped_column(Enum(TDSStatus), default=TDSStatus.PENDING, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)

    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # TDS-specific fields
    _tan_encrypted: Mapped[bytes | None] = encrypted_column()
    total_deductees: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tax_deducted: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total_tax_deposited: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    token_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    acknowledgment_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Checklist and documents
    checklist: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    document_requirements: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    workflow_stages: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    # Missing information tracking
    missing_info: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    missing_info_count: Mapped[int] = mapped_column(default=0, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    compliance_cycle: Mapped[Optional["ComplianceCycle"]] = relationship("ComplianceCycle", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    workflow_instance: Mapped[Optional["WorkflowInstance"]] = relationship("WorkflowInstance", lazy="selectin")
    assigned_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_user_id], lazy="selectin")
    assigned_team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")
    challans: Mapped[list["TDSChallan"]] = relationship("TDSChallan", lazy="dynamic")
    deductees: Mapped[list["TDSDeductee"]] = relationship("TDSDeductee", lazy="dynamic")


class TDSChallan(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "tds_challans"
    __table_args__ = (
        Index("ix_tds_challans_tenant_cycle", "tenant_id", "tds_cycle_id"),
        Index("ix_tds_challans_tenant_status", "tenant_id", "status"),
        Index("ix_tds_challans_tenant_date", "tenant_id", "deposit_date"),
    )

    tds_cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tds_compliance_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    _cin_encrypted: Mapped[bytes] = encrypted_column(nullable=False)
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
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    tds_cycle: Mapped["TDSComplianceCycle"] = relationship("TDSComplianceCycle", back_populates="challans")


class TDSDeductee(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "tds_deductees"
    __table_args__ = (
        Index("ix_tds_deductees_tenant_cycle", "tenant_id", "tds_cycle_id"),
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
    _deductee_pan_encrypted: Mapped[bytes] = encrypted_column(nullable=False)
    deductee_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    section_code: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    tax_deducted: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    tax_deposited: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    deduction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deposit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    certificate_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    tds_cycle: Mapped["TDSComplianceCycle"] = relationship("TDSComplianceCycle", back_populates="deductees")
