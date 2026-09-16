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
    from app.modules.users.models import User


class ConversationStatus(str, PyEnum):
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"
    PENDING = "pending"


class ConversationPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Conversation(Base, TenantBaseModelMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_tenant_client", "tenant_id", "client_id"),
        Index("ix_conversations_tenant_status", "tenant_id", "status"),
        Index("ix_conversations_tenant_assignee", "tenant_id", "assignee_id"),
        Index("ix_conversations_tenant_updated", "tenant_id", "updated_at"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.OPEN, nullable=False, index=True
    )
    priority: Mapped[ConversationPriority] = mapped_column(
        Enum(ConversationPriority), default=ConversationPriority.NORMAL, nullable=False
    )

    channel: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    participant_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=False
    )

    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_message_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id], lazy="selectin")
    messages: Mapped[list["ConversationMessage"]] = relationship("ConversationMessage", back_populates="conversation", lazy="dynamic", cascade="all, delete-orphan")


class ConversationMessage(Base, TenantBaseModelMixin):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        Index("ix_conversation_messages_tenant_conversation", "tenant_id", "conversation_id"),
        Index("ix_conversation_messages_tenant_sender", "tenant_id", "sender_id"),
        Index("ix_conversation_messages_tenant_created", "tenant_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sender_type: Mapped[str] = mapped_column(String(50), nullable=False, default="user")

    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    direction: Mapped[str] = mapped_column(String(20), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)

    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    bcc_addresses: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    attachment_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_response: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages", lazy="selectin")
    sender: Mapped[Optional["User"]] = relationship("User", foreign_keys=[sender_id], lazy="selectin")