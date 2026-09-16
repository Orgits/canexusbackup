import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class NotificationChannel(str, PyEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"


class NotificationPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    DISMISSED = "dismissed"


class NotificationTrigger(str, PyEnum):
    ASSIGNMENT = "assignment"
    REASSIGNMENT = "reassignment"
    DEADLINE_APPROACHING = "deadline_approaching"
    DEADLINE_OVERDUE = "deadline_overdue"
    REVIEW_REQUEST = "review_request"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    REVIEW_REWORK = "review_rework"
    MENTION = "mention"
    ESCALATION = "escalation"
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    DOCUMENT_UPLOADED = "document_uploaded"
    COMPLIANCE_DUE = "compliance_due"
    NOTICE_RECEIVED = "notice_received"
    CUSTOM = "custom"


class NotificationTemplate(Base, TenantBaseModelMixin):
    __tablename__ = "notification_templates"
    __table_args__ = (
        Index("ix_notification_templates_tenant_trigger", "tenant_id", "trigger"),
        UniqueConstraint("tenant_id", "code", name="uq_tenant_notification_template_code"),
    )

    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    trigger: Mapped[NotificationTrigger] = mapped_column(Enum(NotificationTrigger), nullable=False, index=True)

    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)

    default_priority: Mapped[NotificationPriority] = mapped_column(Enum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")


class Notification(Base, TenantBaseModelMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_tenant_recipient", "tenant_id", "recipient_id"),
        Index("ix_notifications_tenant_status", "tenant_id", "status"),
        Index("ix_notifications_tenant_trigger", "tenant_id", "trigger"),
        Index("ix_notifications_tenant_created", "tenant_id", "created_at"),
        Index("ix_notifications_recipient_read", "recipient_id", "status"),
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    trigger: Mapped[NotificationTrigger] = mapped_column(Enum(NotificationTrigger), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    priority: Mapped[NotificationPriority] = mapped_column(Enum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)

    # Related entity
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Actor who triggered the notification
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Channels and delivery status
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    channel_status: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)

    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)

    # Read tracking
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id], lazy="selectin")
    template: Mapped[Optional["NotificationTemplate"]] = relationship("NotificationTemplate", lazy="selectin")
    deliveries: Mapped[list["NotificationDelivery"]] = relationship("NotificationDelivery", back_populates="notification", lazy="dynamic")


class NotificationDelivery(Base, TenantBaseModelMixin):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        Index("ix_notification_deliveries_tenant_notification", "tenant_id", "notification_id"),
        Index("ix_notification_deliveries_tenant_channel", "tenant_id", "channel"),
        Index("ix_notification_deliveries_status", "status"),
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)

    recipient_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[Text] = mapped_column(Text, nullable=False)

    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider_response: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    notification: Mapped["Notification"] = relationship("Notification", back_populates="deliveries")


class NotificationPreference(Base, TenantBaseModelMixin):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index("ix_notification_preferences_tenant_user", "tenant_id", "user_id"),
        UniqueConstraint("tenant_id", "user_id", "trigger", "channel", name="uq_tenant_user_trigger_channel"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    trigger: Mapped[NotificationTrigger] = mapped_column(Enum(NotificationTrigger), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")
