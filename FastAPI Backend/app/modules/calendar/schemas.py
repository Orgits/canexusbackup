from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
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


class CalendarEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    event_type: EventType
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    timezone: str = "Asia/Kolkata"
    location: str | None = Field(None, max_length=500)
    meeting_url: str | None = Field(None, max_length=500)
    client_id: UUID | None = None
    matter_id: UUID | None = None
    task_id: UUID | None = None
    compliance_cycle_id: UUID | None = None
    notice_id: UUID | None = None
    user_id: UUID | None = None
    attendee_ids: list[UUID] = Field(default_factory=list)
    reminder_minutes: list[int] = Field(default_factory=list)
    is_recurring: bool = False
    recurrence_rule: str | None = None
    recurrence_end: datetime | None = None
    color: str | None = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalendarEventCreate(CalendarEventBase):
    pass


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    event_type: EventType | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    all_day: bool | None = None
    timezone: str | None = None
    location: str | None = Field(None, max_length=500)
    meeting_url: str | None = Field(None, max_length=500)
    client_id: UUID | None = None
    matter_id: UUID | None = None
    task_id: UUID | None = None
    compliance_cycle_id: UUID | None = None
    notice_id: UUID | None = None
    user_id: UUID | None = None
    attendee_ids: list[UUID] | None = None
    reminder_minutes: list[int] | None = None
    is_recurring: bool | None = None
    recurrence_rule: str | None = None
    recurrence_end: datetime | None = None
    color: str | None = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    metadata: dict[str, Any] | None = None


class CalendarEventResponse(CalendarEventBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CalendarEventListResponse(BaseModel):
    items: list[CalendarEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
