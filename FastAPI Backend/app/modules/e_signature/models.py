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


class ESignatureProvider(str, PyEnum):
    DOCUSIGN = "docusign"
    ADOBE_SIGN = "adobe_sign"
    HELLOSIGN = "hellosign"
    PANDA_DOC = "panda_doc"
    SIGNNOW = "signnow"
    INTERNAL = "internal"


class ESignatureRequestStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ESignerStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"


class ESignatureRequest(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "e_signature_requests"
    __table_args__ = (
        Index("ix_e_signature_requests_tenant_document", "tenant_id", "document_id"),
        Index("ix_e_signature_requests_tenant_status", "tenant_id", "status"),
        Index("ix_e_signature_requests_tenant_provider", "tenant_id", "provider"),
        Index("ix_e_signature_requests_tenant_external_id", "tenant_id", "external_request_id"),
        Index("ix_e_signature_requests_tenant_created", "tenant_id", "created_at"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    engagement_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagement_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider: Mapped[ESignatureProvider] = mapped_column(
        Enum(ESignatureProvider), nullable=False, index=True
    )

    status: Mapped[ESignatureRequestStatus] = mapped_column(
        Enum(ESignatureRequestStatus), default=ESignatureRequestStatus.DRAFT, nullable=False, index=True
    )

    external_request_id: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)

    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    signing_order: Mapped[bool] = mapped_column(default=False, nullable=False)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reminder_frequency_days: Mapped[int | None] = mapped_column(nullable=True)

    reminder_count: Mapped[int] = mapped_column(default=0, nullable=False)

    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    declined_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    webhook_events: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    document: Mapped["Document"] = relationship("Document", lazy="selectin")
    engagement_document: Mapped[Optional["EngagementDocument"]] = relationship("EngagementDocument", foreign_keys=[engagement_document_id], lazy="selectin")
    signers: Mapped[list["ESigner"]] = relationship("ESigner", back_populates="request", lazy="dynamic", cascade="all, delete-orphan")


class ESigner(Base, TenantBaseModelMixin):
    __tablename__ = "e_signers"
    __table_args__ = (
        Index("ix_e_signers_tenant_request", "tenant_id", "request_id"),
        Index("ix_e_signers_tenant_user", "tenant_id", "signer_id"),
        Index("ix_e_signers_tenant_email", "tenant_id", "email"),
        Index("ix_e_signers_tenant_status", "tenant_id", "status"),
        Index("ix_e_signers_tenant_external_id", "tenant_id", "external_signer_id"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("e_signature_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    signer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    role: Mapped[str] = mapped_column(String(100), nullable=False)

    signing_order: Mapped[int] = mapped_column(default=1, nullable=False)

    status: Mapped[ESignerStatus] = mapped_column(
        Enum(ESignerStatus), default=ESignerStatus.PENDING, nullable=False, index=True
    )

    external_signer_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    authentication_method: Mapped[str | None] = mapped_column(String(50), nullable=True)

    access_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    signature_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    provider_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    request: Mapped["ESignatureRequest"] = relationship("ESignatureRequest", back_populates="signers", lazy="selectin")
    signer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[signer_id], lazy="selectin")


class ESignatureProviderConfig(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "e_signature_provider_configs"
    __table_args__ = (
        Index("ix_e_signature_provider_configs_tenant_provider", "tenant_id", "provider", unique=True),
    )

    provider: Mapped[ESignatureProvider] = mapped_column(
        Enum(ESignatureProvider), nullable=False, index=True
    )

    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)

    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    api_base_url: Mapped[str] = mapped_column(String(500), nullable=False)

    client_id: Mapped[str] = mapped_column(String(200), nullable=False)

    client_secret_encrypted: Mapped[bytes] = mapped_column(nullable=False)

    account_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    webhook_secret_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)

    oauth_redirect_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)

    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    rate_limit_per_minute: Mapped[int] = mapped_column(default=100, nullable=False)

    timeout_seconds: Mapped[int] = mapped_column(default=30, nullable=False)

    extra_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")


class ESignatureWebhookEvent(Base, TenantBaseModelMixin):
    __tablename__ = "e_signature_webhook_events"
    __table_args__ = (
        Index("ix_e_signature_webhook_events_tenant_provider", "tenant_id", "provider"),
        Index("ix_e_signature_webhook_events_tenant_external_id", "tenant_id", "external_event_id"),
        Index("ix_e_signature_webhook_events_tenant_processed", "tenant_id", "processed"),
        Index("ix_e_signature_webhook_events_tenant_received", "tenant_id", "received_at"),
    )

    provider: Mapped[ESignatureProvider] = mapped_column(
        Enum(ESignatureProvider), nullable=False, index=True
    )

    external_event_id: Mapped[str] = mapped_column(String(200), nullable=False)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    external_request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    processed: Mapped[bool] = mapped_column(default=False, nullable=False)

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)

    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")