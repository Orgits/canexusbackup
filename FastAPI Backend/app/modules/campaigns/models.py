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
    from app.modules.clients.models import Client
    from app.modules.users.models import User


class CampaignStatus(str, PyEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class CampaignType(str, PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    MIXED = "mixed"


class Campaign(Base, TenantBaseModelMixin):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_tenant_status", "tenant_id", "status"),
        Index("ix_campaigns_tenant_type", "tenant_id", "campaign_type"),
        Index("ix_campaigns_tenant_scheduled", "tenant_id", "scheduled_at"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign_type: Mapped[CampaignType] = mapped_column(Enum(CampaignType), nullable=False, index=True)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    audience_filter: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    audience_count: Mapped[int] = mapped_column(default=0, nullable=False)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sent_count: Mapped[int] = mapped_column(default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(default=0, nullable=False)
    opened_count: Mapped[int] = mapped_column(default=0, nullable=False)
    clicked_count: Mapped[int] = mapped_column(default=0, nullable=False)
    replied_count: Mapped[int] = mapped_column(default=0, nullable=False)
    bounced_count: Mapped[int] = mapped_column(default=0, nullable=False)
    unsubscribed_count: Mapped[int] = mapped_column(default=0, nullable=False)

    total_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    cost_per_message: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    template: Mapped[Optional["Template"]] = relationship("Template", foreign_keys=[template_id], lazy="selectin")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    communications: Mapped[list["Communication"]] = relationship("app.modules.communications.models.Communication", back_populates="campaign", lazy="dynamic")


class CampaignRecipient(Base, TenantBaseModelMixin):
    __tablename__ = "campaign_recipients"
    __table_args__ = (
        Index("ix_campaign_recipients_tenant_campaign", "tenant_id", "campaign_id"),
        Index("ix_campaign_recipients_tenant_client", "tenant_id", "client_id"),
        Index("ix_campaign_recipients_tenant_status", "tenant_id", "status"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    communication_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="selectin")

# Import at bottom to resolve circular dependency
from app.modules.communications.models import Communication