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
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task


class CommunicationChannel(str, PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL = "call"
    NOTE = "note"
    MEETING = "meeting"
    LETTER = "letter"
    PORTAL = "portal"


class CommunicationDirection(str, PyEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class CommunicationStatus(str, PyEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    REPLIED = "replied"
    FAILED = "failed"
    BOUNCED = "bounced"
    SPAM = "spam"
    ARCHIVED = "archived"


class Communication(Base, TenantBaseModelMixin):
    __tablename__ = "communications"
    __table_args__ = (
        Index("ix_communications_tenant_client", "tenant_id", "client_id"),
        Index("ix_communications_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_communications_tenant_thread", "tenant_id", "thread_id"),
        Index("ix_communications_tenant_status", "tenant_id", "status"),
        Index("ix_communications_tenant_sent_at", "tenant_id", "sent_at"),
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
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    channel: Mapped[CommunicationChannel] = mapped_column(Enum(CommunicationChannel), nullable=False, index=True)
    direction: Mapped[CommunicationDirection] = mapped_column(Enum(CommunicationDirection), nullable=False)
    status: Mapped[CommunicationStatus] = mapped_column(Enum(CommunicationStatus), default=CommunicationStatus.DRAFT, nullable=False, index=True)

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    bcc_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    parent_communication_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communications.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_response: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    attachment_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)
    linked_document_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)
    linked_task_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

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
    task: Mapped[Optional["Task"]] = relationship("Task", foreign_keys=[task_id], lazy="selectin")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", foreign_keys=[campaign_id], back_populates="communications", lazy="selectin")
    parent_communication: Mapped[Optional["Communication"]] = relationship("Communication", remote_side="Communication.id", back_populates="replies", lazy="selectin")
    replies: Mapped[list["Communication"]] = relationship("Communication", back_populates="parent_communication", lazy="dynamic")

# Import at bottom to resolve circular dependency
from app.modules.campaigns.models import Campaign
