from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CommunicationChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL = "call"
    NOTE = "note"
    MEETING = "meeting"
    LETTER = "letter"
    PORTAL = "portal"


class CommunicationDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class CommunicationStatus(str, Enum):
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


class CommunicationBase(BaseModel):
    client_id: UUID
    matter_id: UUID | None = None
    task_id: UUID | None = None
    campaign_id: UUID | None = None
    channel: CommunicationChannel
    direction: CommunicationDirection
    subject: str | None = Field(None, max_length=500)
    body: str
    body_html: str | None = None
    from_address: str | None = Field(None, max_length=255)
    to_addresses: list[str] = Field(default_factory=list)
    cc_addresses: list[str] = Field(default_factory=list)
    bcc_addresses: list[str] = Field(default_factory=list)
    thread_id: UUID | None = None
    parent_communication_id: UUID | None = None
    conversation_id: UUID | None = None
    provider: str | None = Field(None, max_length=50)
    provider_message_id: str | None = Field(None, max_length=255)
    attachment_ids: list[UUID] = Field(default_factory=list)
    linked_document_ids: list[UUID] = Field(default_factory=list)
    linked_task_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommunicationCreate(CommunicationBase):
    pass


class CommunicationResponse(CommunicationBase):
    id: UUID
    status: CommunicationStatus
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    provider_status: str | None = None
    provider_response: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommunicationListResponse(BaseModel):
    items: list[CommunicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
