from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    VOICE = "voice"
    PUSH = "push"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class ChannelProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    channel_type: ChannelType
    provider_name: str = Field(..., max_length=100)
    provider_id: str = Field(..., max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)
    webhook_url: str | None = Field(None, max_length=500)
    webhook_secret: str | None = Field(None, max_length=255)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    rate_limit_per_hour: int = Field(default=1000, ge=1, le=100000)
    rate_limit_per_day: int = Field(default=10000, ge=1, le=1000000)
    is_default: bool = False
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelProviderCreate(ChannelProviderBase):
    pass


class ChannelProviderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    webhook_url: str | None = Field(None, max_length=500)
    webhook_secret: str | None = Field(None, max_length=255)
    rate_limit_per_minute: int | None = Field(None, ge=1, le=10000)
    rate_limit_per_hour: int | None = Field(None, ge=1, le=100000)
    rate_limit_per_day: int | None = Field(None, ge=1, le=1000000)
    is_default: bool | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class ChannelProviderResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    channel_type: ChannelType
    provider_name: str
    provider_id: str
    status: str
    config: dict[str, Any]
    webhook_url: str | None
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    last_health_check: datetime | None
    last_error: str | None
    error_count: int
    is_default: bool
    is_active: bool
    metadata: dict[str, Any]
    tenant_id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChannelProviderListResponse(BaseModel):
    items: list["ChannelProviderResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageLogCreate(BaseModel):
    provider_id: UUID
    channel_type: str = Field(..., max_length=50)
    direction: str = Field(..., max_length=20)
    recipient: str = Field(..., max_length=500)
    subject: str | None = Field(None, max_length=500)
    body: str
    provider_message_id: str | None = Field(None, max_length=255)
    cost: float | None = None
    currency: str = Field(default="USD", max_length=3)
    scheduled_at: datetime | None = None


class MessageLogResponse(BaseModel):
    id: UUID
    provider_id: UUID
    channel_type: str
    direction: str
    recipient: str
    subject: str | None
    body: str
    status: str
    provider_message_id: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    error_code: str | None
    error_message: str | None
    cost: float | None
    currency: str
    retry_count: int
    max_retries: int
    scheduled_at: datetime | None
    sent_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageLogListResponse(BaseModel):
    items: list[MessageLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SendMessageRequest(BaseModel):
    provider_id: UUID
    channel_type: str = Field(..., max_length=50)
    recipient: str = Field(..., max_length=500)
    subject: str | None = Field(None, max_length=500)
    body: str
    scheduled_at: datetime | None = None