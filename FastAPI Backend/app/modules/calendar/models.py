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
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.clients.models import Client
    from app.modules.compliance.models import ComplianceCycle
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.users.models import User


class EventType(str, PyEnum):
    COMPLIANCE_DEADLINE = "compliance_deadline"
    TASK_DEADLINE = "task_deadline"
    NOTICE_DEADLINE = "notice_deadline"
    CLIENT_MEETING = "client_meeting"
    INTERNAL_MEETING = "internal_meeting"
    HEARING = "hearing"
    FOLLOW_UP = "follow_up"
    REVIEW_MEETING = "review_meeting"
    TRAINING = "training"
    LEAVE = "leave"
    HOLIDAY = "holiday"
    OTHER = "other"


class CalendarEvent(Base, TenantBaseModelMixin):
    __tablename__ = "calendar_events"
    __table_args__ = (
        Index("ix_calendar_events_tenant_client", "tenant_id", "client_id"),
        Index("ix_calendar_events_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_calendar_events_tenant_user", "tenant_id", "user_id"),
        Index("ix_calendar_events_tenant_type", "tenant_id", "event_type"),
        Index("ix_calendar_events_tenant_start", "tenant_id", "start_time"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False, index=True)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)

    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
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
    compliance_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attendee_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

    reminder_minutes: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recurrence_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    task: Mapped[Optional["Task"]] = relationship("Task", lazy="selectin")
    compliance_cycle: Mapped[Optional["ComplianceCycle"]] = relationship("ComplianceCycle", lazy="selectin")
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id], lazy="selectin")
