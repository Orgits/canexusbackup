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
    from app.modules.users.models import User
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.documents.models import Document


class EngagementDocumentType(str, PyEnum):
    ENGAGEMENT_LETTER = "engagement_letter"
    REPRESENTATION_LETTER = "representation_letter"
    MANAGEMENT_LETTER = "management_letter"
    CONFIRMATION_LETTER = "confirmation_letter"
    INDEPENDENCE_DECLARATION = "independence_declaration"
    TERMS_OF_BUSINESS = "terms_of_business"
    SCOPE_OF_WORK = "scope_of_work"
    FEE_AGREEMENT = "fee_agreement"
    NDA = "nda"
    OTHER = "other"


class EngagementDocumentStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_SIGNATURE = "pending_signature"
    PARTIALLY_SIGNED = "partially_signed"
    FULLY_SIGNED = "fully_signed"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EngagementDocument(Base, TenantBaseModelMixin):
    __tablename__ = "engagement_documents"
    __table_args__ = (
        Index("ix_engagement_documents_tenant_client", "tenant_id", "client_id"),
        Index("ix_engagement_documents_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_engagement_documents_tenant_status", "tenant_id", "status"),
        Index("ix_engagement_documents_tenant_type", "tenant_id", "document_type"),
        Index("ix_engagement_documents_tenant_number", "tenant_id", "document_number", unique=True),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    matter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_type: Mapped[EngagementDocumentType] = mapped_column(
        Enum(EngagementDocumentType), nullable=False, index=True
    )

    status: Mapped[EngagementDocumentStatus] = mapped_column(
        Enum(EngagementDocumentStatus), default=EngagementDocumentStatus.DRAFT, nullable=False, index=True
    )

    document_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    template_version: Mapped[int | None] = mapped_column(nullable=True)

    document_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    variables: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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

    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fee_estimate: Mapped[float | None] = mapped_column(nullable=True)
    fee_terms: Mapped[str | None] = mapped_column(Text, nullable=True)

    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    e_signature_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("e_signature_requests.id", ondelete="SET NULL"),
        nullable=True,
    )

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    engagement_partner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[engagement_partner_id], lazy="selectin")
    engagement_manager: Mapped[Optional["User"]] = relationship("User", foreign_keys=[engagement_manager_id], lazy="selectin")
    signers: Mapped[list["EngagementDocumentSigner"]] = relationship("EngagementDocumentSigner", back_populates="engagement_document", lazy="dynamic", cascade="all, delete-orphan")
    versions: Mapped[list["EngagementDocumentVersion"]] = relationship("EngagementDocumentVersion", back_populates="engagement_document", lazy="dynamic", cascade="all, delete-orphan")
    e_signature_request: Mapped[Optional["ESignatureRequest"]] = relationship("ESignatureRequest", foreign_keys=[e_signature_request_id], lazy="selectin")


class EngagementDocumentSigner(Base, TenantBaseModelMixin):
    __tablename__ = "engagement_document_signers"
    __table_args__ = (
        Index("ix_engagement_document_signers_tenant_document", "tenant_id", "engagement_document_id"),
        Index("ix_engagement_document_signers_tenant_user", "tenant_id", "signer_id"),
        Index("ix_engagement_document_signers_tenant_status", "tenant_id", "status"),
    )

    engagement_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagement_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    signer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    signer_role: Mapped[str] = mapped_column(String(100), nullable=False)

    signing_order: Mapped[int] = mapped_column(default=1, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signature_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reminder_count: Mapped[int] = mapped_column(default=0, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    engagement_document: Mapped["EngagementDocument"] = relationship("EngagementDocument", back_populates="signers", lazy="selectin")
    signer: Mapped["User"] = relationship("User", foreign_keys=[signer_id], lazy="selectin")


class EngagementDocumentVersion(Base, TenantBaseModelMixin):
    __tablename__ = "engagement_document_versions"
    __table_args__ = (
        Index("ix_engagement_document_versions_tenant_document", "tenant_id", "engagement_document_id"),
    )

    engagement_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagement_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(nullable=False)

    document_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    variables: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    engagement_document: Mapped["EngagementDocument"] = relationship("EngagementDocument", back_populates="versions", lazy="selectin")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")


class EngagementDocumentTemplate(Base, TenantBaseModelMixin):
    __tablename__ = "engagement_document_templates"
    __table_args__ = (
        Index("ix_engagement_document_templates_tenant_type", "tenant_id", "document_type"),
        Index("ix_engagement_document_templates_tenant_active", "tenant_id", "is_active"),
    )

    document_type: Mapped[EngagementDocumentType] = mapped_column(
        Enum(EngagementDocumentType), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_template: Mapped[str] = mapped_column(Text, nullable=False)

    html_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    default_variables: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    required_variables: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    version: Mapped[int] = mapped_column(default=1, nullable=False)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")