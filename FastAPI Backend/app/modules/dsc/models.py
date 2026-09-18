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
from app.core.database.encryption_mixin import PIIEncryptionMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.clients.models import Client
    from app.modules.documents.models import Document


class DSCType(str, PyEnum):
    CLASS_1 = "class_1"
    CLASS_2 = "class_2"
    CLASS_3 = "class_3"
    DGFT = "dgft"


class DSCStatus(str, PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_RENEWAL = "pending_renewal"
    RENEWED = "renewed"


class DSCCertificate(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "dsc_certificates"
    __table_args__ = (
        Index("ix_dsc_certificates_tenant_holder", "tenant_id", "holder_id"),
        Index("ix_dsc_certificates_tenant_status", "tenant_id", "status"),
        Index("ix_dsc_certificates_tenant_expiry", "tenant_id", "expiry_date"),
        Index("ix_dsc_certificates_tenant_type", "tenant_id", "dsc_type"),
    )

    holder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dsc_type: Mapped[DSCType] = mapped_column(
        Enum(DSCType), nullable=False, index=True
    )

    status: Mapped[DSCStatus] = mapped_column(
        Enum(DSCStatus), default=DSCStatus.ACTIVE, nullable=False, index=True
    )

    certificate_serial_number: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    issuing_authority: Mapped[str] = mapped_column(String(200), nullable=False)

    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    custodian_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    certificate_pem: Mapped[bytes | None] = mapped_column(nullable=True)

    private_key_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)

    passphrase_hash: Mapped[str | None] = mapped_column(String(500), nullable=True)

    key_algorithm: Mapped[str] = mapped_column(String(50), default="RSA", nullable=False)

    key_size: Mapped[int] = mapped_column(default=2048, nullable=False)

    pin_hash: Mapped[str | None] = mapped_column(String(500), nullable=True)

    token_serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    token_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    renewal_reminder_sent: Mapped[bool] = mapped_column(default=False, nullable=False)

    renewal_initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    holder: Mapped["User"] = relationship("User", foreign_keys=[holder_id], lazy="selectin")
    custodian: Mapped[Optional["User"]] = relationship("User", foreign_keys=[custodian_id], lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", lazy="selectin")
    # documents: Mapped[list["Document"]] = relationship("Document", back_populates="dsc_certificate", lazy="dynamic")
    signing_logs: Mapped[list["DSCSigningLog"]] = relationship("DSCSigningLog", back_populates="certificate", lazy="dynamic", cascade="all, delete-orphan")


class DSCSigningLog(Base, TenantBaseModelMixin):
    __tablename__ = "dsc_signing_logs"
    __table_args__ = (
        Index("ix_dsc_signing_logs_tenant_certificate", "tenant_id", "certificate_id"),
        Index("ix_dsc_signing_logs_tenant_user", "tenant_id", "signed_by_id"),
        Index("ix_dsc_signing_logs_tenant_document", "tenant_id", "document_id"),
        Index("ix_dsc_signing_logs_tenant_status", "tenant_id", "status"),
        Index("ix_dsc_signing_logs_tenant_created", "tenant_id", "created_at"),
    )

    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dsc_certificates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    signed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    signing_purpose: Mapped[str] = mapped_column(String(200), nullable=False)

    signature_algorithm: Mapped[str] = mapped_column(String(100), nullable=False)

    signature_hash: Mapped[str] = mapped_column(String(200), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    certificate: Mapped["DSCCertificate"] = relationship("DSCCertificate", back_populates="signing_logs", lazy="selectin")
    document: Mapped[Optional["Document"]] = relationship("Document", lazy="selectin")
    signed_by: Mapped["User"] = relationship("User", foreign_keys=[signed_by_id], lazy="selectin")


class DSCRenewalRequest(Base, TenantBaseModelMixin):
    __tablename__ = "dsc_renewal_requests"
    __table_args__ = (
        Index("ix_dsc_renewal_requests_tenant_certificate", "tenant_id", "certificate_id"),
        Index("ix_dsc_renewal_requests_tenant_status", "tenant_id", "status"),
        Index("ix_dsc_renewal_requests_tenant_requested_by", "tenant_id", "requested_by_id"),
    )

    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dsc_certificates.id", ondelete="CASCADE"),
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

    renewal_authority: Mapped[str | None] = mapped_column(String(200), nullable=True)

    renewal_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)

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
    certificate: Mapped["DSCCertificate"] = relationship("DSCCertificate", lazy="selectin")
    requested_by: Mapped["User"] = relationship("User", foreign_keys=[requested_by_id], lazy="selectin")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id], lazy="selectin")
    rejected_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[rejected_by_id], lazy="selectin")