from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


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
    matter_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    channel: CommunicationChannel
    direction: CommunicationDirection
    subject: Optional[str] = Field(None, max_length=500)
    body: str
    body_html: Optional[str] = None
    from_address: Optional[str] = Field(None, max_length=255)
    to_addresses: List[str] = Field(default_factory=list)
    cc_addresses: List[str] = Field(default_factory=list)
    bcc_addresses: List[str] = Field(default_factory=list)
    thread_id: Optional[UUID] = None
    parent_communication_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    provider: Optional[str] = Field(None, max_length=50)
    provider_message_id: Optional[str] = Field(None, max_length=255)
    attachment_ids: List[UUID] = Field(default_factory=list)
    linked_document_ids: List[UUID] = Field(default_factory=list)
    linked_task_ids: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CommunicationCreate(CommunicationBase):
    pass


class CommunicationResponse(CommunicationBase):
    id: UUID
    status: CommunicationStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    provider_status: Optional[str] = None
    provider_response: Dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommunicationListResponse(BaseModel):
    items: List[CommunicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int