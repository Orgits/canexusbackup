from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class SuppressionReason(str, Enum):
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLAINT = "complaint"
    MANUAL = "manual"
    LEGAL = "legal"
    DO_NOT_CONTACT = "do_not_contact"


class SuppressionChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL = "call"
    POST = "post"
    ALL = "all"


class SuppressionBase(BaseModel):
    value: str = Field(..., min_length=1, max_length=500)
    channel: SuppressionChannel
    reason: SuppressionReason
    description: str | None = Field(None, max_length=1000)
    source: str = Field(..., max_length=100)
    source_reference: str | None = Field(None, max_length=255)
    client_id: UUID | None = None
    is_global: bool = False
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuppressionCreate(SuppressionBase):
    pass


class SuppressionUpdate(BaseModel):
    reason: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None


class SuppressionResponse(BaseModel):
    id: UUID
    value: str
    channel: SuppressionChannel
    reason: SuppressionReason
    description: str | None
    source: str
    source_reference: str | None
    client_id: UUID | None
    is_global: bool
    expires_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SuppressionListResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class SuppressionCheckRequest(BaseModel):
    value: str = Field(..., min_length=1, max_length=500)
    channel: SuppressionChannel


class SuppressionCheckResponse(BaseModel):
    is_suppressed: bool
    reason: str | None = None
    matched_rule: dict[str, Any] | None = None