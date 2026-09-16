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


class WebhookEventStatus(str, PyEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRY = "retry"
    DLQ = "dlq"  # Dead letter queue


class WebhookSource(str, PyEnum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    DOCUMENT = "document"
    PAYMENT = "payment"
    CUSTOM = "custom"


class WebhookEvent(Base, TenantBaseModelMixin):
    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_webhook_events_tenant_source", "tenant_id", "source"),
        Index("ix_webhook_events_tenant_status", "tenant_id", "status"),
        Index("ix_webhook_events_tenant_external_id", "tenant_id", "external_id"),
        Index("ix_webhook_events_tenant_created", "tenant_id", "created_at"),
    )

    source: Mapped[WebhookSource] = mapped_column(Enum(WebhookSource), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    headers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    query_params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="received", nullable=False, index=True)

    processing_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=3, nullable=False)

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True, unique=True)

    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")


class WebhookEndpoint(Base, TenantBaseModelMixin):
    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        Index("ix_webhook_endpoints_tenant_url", "tenant_id", "url"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    events: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    secret_verification: Mapped[bool] = mapped_column(default=True, nullable=False)

    retry_policy: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    headers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    timeout_seconds: Mapped[int] = mapped_column(default=30, nullable=False)

    success_count: Mapped[int] = mapped_column(default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    secret_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")