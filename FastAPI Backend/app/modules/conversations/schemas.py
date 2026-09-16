from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"
    PENDING = "pending"


class ConversationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ConversationMessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class ConversationBase(BaseModel):
    client_id: UUID
    assignee_id: UUID | None = None
    subject: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: ConversationPriority = ConversationPriority.NORMAL
    channel: str | None = Field(None, max_length=50)
    participant_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    assignee_id: UUID | None = None
    subject: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    priority: ConversationPriority | None = None
    channel: str | None = Field(None, max_length=50)
    participant_ids: list[UUID] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ConversationMessageCreate(BaseModel):
    conversation_id: UUID
    channel: str = Field(..., max_length=50)
    direction: str = Field(..., max_length=20)
    content: str
    content_html: str | None = None
    subject: str | None = Field(None, max_length=500)
    from_address: str | None = Field(None, max_length=255)
    to_addresses: list[str] = Field(default_factory=list)
    cc_addresses: list[str] = Field(default_factory=list)
    bcc_addresses: list[str] = Field(default_factory=list)
    attachment_ids: list[UUID] = Field(default_factory=list)
    provider: str | None = Field(None, max_length=50)
    provider_message_id: str | None = Field(None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID | None
    sender_type: str
    channel: str
    direction: str
    content: str
    content_html: str | None
    subject: str | None
    from_address: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    bcc_addresses: list[str]
    attachment_ids: list[UUID]
    provider: str | None
    provider_message_id: str | None
    provider_status: str | None
    provider_response: dict[str, Any]
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    client_id: UUID
    assignee_id: UUID | None
    subject: str
    description: str | None
    status: str
    priority: ConversationPriority
    channel: str | None
    participant_ids: list[UUID]
    tags: list[str]
    metadata: dict[str, Any]
    closed_at: datetime | None
    closed_by: UUID | None
    last_message_at: datetime | None
    last_message_preview: str | None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    messages: list[ConversationMessageResponse] = []
    client: Any | None = None
    assignee: Any | None = None


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int