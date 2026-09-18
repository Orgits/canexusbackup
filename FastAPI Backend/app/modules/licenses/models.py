import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
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
from app.core.database.encryption_mixin import PIIEncryptionMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.clients.models import Client
    from app.modules.documents.models import Document


class LicenseType(str, PyEnum):
    CA_CERTIFICATE = "ca_certificate"
    CA_PRACTICE_CERTIFICATE = "ca_practice_certificate"
    GST_PRACTITIONER = "gst_practitioner"
    TAX_AUDITOR = "tax_auditor"
    COMPANY_SECRETARY = "company_secretary"
    COST_ACCOUNTANT = "cost_accountant"
    INSOLVENCY_PROFESSIONAL = "insolvency_professional"
    REGISTERED_VALUER = "registered_valuer"
    PEER_REVIEW_CERTIFICATE = "peer_review_certificate"
    QUALITY_REVIEW_CERTIFICATE = "quality_review_certificate"
    FCRA_REGISTRATION = "fcra_registration"
    INCOME_TAX_PRACTITIONER = "income_tax_practitioner"
    OTHER = "other"


class LicenseStatus(str, PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING_RENEWAL = "pending_renewal"
    RENEWED = "renewed"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    SURRENDERED = "surrendered"


class License(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "licenses"
    __table_args__ = (
        Index("ix_licenses_tenant_professional", "tenant_id", "professional_id"),
        Index("ix_licenses_tenant_status", "tenant_id", "status"),
        Index("ix_licenses_tenant_expiry", "tenant_id", "expiry_date"),
        Index("ix_licenses_tenant_type", "tenant_id", "license_type"),
        Index("ix_licenses_tenant_number", "tenant_id", "license_number", unique=True),
    )

    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    license_type: Mapped[LicenseType] = mapped_column(
        Enum(LicenseType), nullable=False, index=True
    )

    status: Mapped[LicenseStatus] = mapped_column(
        Enum(LicenseStatus), default=LicenseStatus.ACTIVE, nullable=False, index=True
    )

    license_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    issuing_authority: Mapped[str] = mapped_column(String(200), nullable=False)

    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)

    scope: Mapped[str | None] = mapped_column(Text, nullable=True)

    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)

    renewal_application_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    renewal_acknowledgment_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    renewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    renewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    suspended_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revoked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    professional: Mapped["User"] = relationship("User", foreign_keys=[professional_id], lazy="selectin")
    renewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[renewed_by_id], lazy="selectin")
    suspended_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[suspended_by_id], lazy="selectin")
    revoked_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[revoked_by_id], lazy="selectin")
    # documents: Mapped[list["Document"]] = relationship("Document", back_populates="license", lazy="dynamic")
    renewal_requests: Mapped[list["LicenseRenewalRequest"]] = relationship("LicenseRenewalRequest", back_populates="license", lazy="dynamic", cascade="all, delete-orphan")


class LicenseDocument(Base, TenantBaseModelMixin):
    __tablename__ = "license_documents"
    __table_args__ = (
        Index("ix_license_documents_tenant_license", "tenant_id", "license_id"),
        Index("ix_license_documents_tenant_document", "tenant_id", "document_id"),
    )

    license_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("licenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    license: Mapped["License"] = relationship("License", lazy="selectin")
    document: Mapped["Document"] = relationship("Document", lazy="selectin")
    uploaded_by: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by_id], lazy="selectin")


class LicenseRenewalRequest(Base, TenantBaseModelMixin):
    __tablename__ = "license_renewal_requests"
    __table_args__ = (
        Index("ix_license_renewal_requests_tenant_license", "tenant_id", "license_id"),
        Index("ix_license_renewal_requests_tenant_status", "tenant_id", "status"),
        Index("ix_license_renewal_requests_tenant_requested_by", "tenant_id", "requested_by_id"),
    )

    license_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("licenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    new_expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    application_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    application_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fees_paid: Mapped[bool] = mapped_column(default=False, nullable=False)

    fees_amount: Mapped[float | None] = mapped_column(nullable=True)

    fees_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rejected_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    license: Mapped["License"] = relationship("License", back_populates="renewal_requests", lazy="selectin")
    requested_by: Mapped["User"] = relationship("User", foreign_keys=[requested_by_id], lazy="selectin")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id], lazy="selectin")
    rejected_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[rejected_by_id], lazy="selectin")