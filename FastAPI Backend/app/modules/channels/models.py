import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
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


class ChannelType(str, PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    VOICE = "voice"
    PUSH = "push"


class ProviderStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class ChannelProvider(Base, TenantBaseModelMixin):
    __tablename__ = "channel_providers"
    __table_args__ = (
        Index("ix_channel_providers_tenant_type", "tenant_id", "channel_type"),
        Index("ix_channel_providers_tenant_status", "tenant_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    channel_type: Mapped[ChannelType] = mapped_column(Enum(ChannelType), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[ProviderStatus] = mapped_column(Enum(ProviderStatus), default=ProviderStatus.PENDING, nullable=False, index=True)

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    credentials: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Webhook configuration
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Rate limiting
    rate_limit_per_minute: Mapped[int] = mapped_column(default=60, nullable=False)
    rate_limit_per_hour: Mapped[int] = mapped_column(default=1000, nullable=False)
    rate_limit_per_day: Mapped[int] = mapped_column(default=10000, nullable=False)

    # Health monitoring
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)

    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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


class MessageLog(Base, TenantBaseModelMixin):
    __tablename__ = "message_logs"
    __table_args__ = (
        Index("ix_message_logs_tenant_channel", "tenant_id", "channel_type"),
        Index("ix_message_logs_tenant_provider", "tenant_id", "provider_id"),
        Index("ix_message_logs_tenant_status", "tenant_id", "status"),
        Index("ix_message_logs_tenant_recipient", "tenant_id", "recipient"),
        Index("ix_message_logs_tenant_created", "tenant_id", "created_at"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    direction: Mapped[str] = mapped_column(String(20), nullable=False)

    recipient: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    cost: Mapped[float | None] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")