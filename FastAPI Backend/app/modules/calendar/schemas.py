from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


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
    description: Optional[str] = None
    event_type: EventType
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    timezone: str = "Asia/Kolkata"
    location: Optional[str] = Field(None, max_length=500)
    meeting_url: Optional[str] = Field(None, max_length=500)
    client_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    compliance_cycle_id: Optional[UUID] = None
    notice_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    attendee_ids: List[UUID] = Field(default_factory=list)
    reminder_minutes: List[int] = Field(default_factory=list)
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[datetime] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CalendarEventCreate(CalendarEventBase):
    pass


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    timezone: Optional[str] = None
    location: Optional[str] = Field(None, max_length=500)
    meeting_url: Optional[str] = Field(None, max_length=500)
    client_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    compliance_cycle_id: Optional[UUID] = None
    notice_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    attendee_ids: Optional[List[UUID]] = None
    reminder_minutes: Optional[List[int]] = None
    is_recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[datetime] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    metadata: Optional[Dict[str, Any]] = None


class CalendarEventResponse(CalendarEventBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CalendarEventListResponse(BaseModel):
    items: List[CalendarEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int