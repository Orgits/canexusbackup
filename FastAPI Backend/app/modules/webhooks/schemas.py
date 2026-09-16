from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookEventStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRY = "retry"
    DLQ = "dlq"


class WebhookSource(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    DOCUMENT = "document"
    PAYMENT = "payment"
    CUSTOM = "custom"


class WebhookEventBase(BaseModel):
    source: str = Field(..., max_length=50)
    external_id: str = Field(..., max_length=255)
    event_type: str = Field(..., max_length=100)
    event_category: str | None = Field(None, max_length=100)
    payload: dict[str, Any]
    headers: dict[str, Any] = Field(default_factory=dict)
    query_params: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebhookEventCreate(WebhookEventBase):
    pass


class WebhookEventResponse(BaseModel):
    id: UUID
    source: str
    external_id: str
    event_type: str
    event_category: str | None
    payload: dict[str, Any]
    headers: dict[str, Any]
    query_params: dict[str, Any]
    status: str
    processing_attempts: int
    max_attempts: int
    last_error: str | None
    last_attempt_at: datetime | None
    processed_at: datetime | None
    processed_by: UUID | None
    idempotency_key: str | None
    retry_after: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookEventListResponse(BaseModel):
    items: list["WebhookEventResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class WebhookEndpointBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    url: str = Field(..., max_length=500)
    secret: str | None = Field(None, max_length=255)
    events: list[str] = Field(default_factory=list)
    is_active: bool = True
    secret_verification: bool = True
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class WebhookEndpointCreate(WebhookEndpointBase):
    pass


class WebhookEndpointUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    url: str | None = Field(None, max_length=500)
    secret: str | None = Field(None, max_length=255)
    events: list[str] | None = None
    is_active: bool | None = None
    secret_verification: bool | None = None
    retry_policy: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)


class WebhookEndpointResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    url: str
    secret: str | None
    events: list[str]
    is_active: bool
    secret_verification: bool
    retry_policy: dict[str, Any]
    headers: dict[str, str]
    timeout_seconds: int
    success_count: int
    failure_count: int
    last_success_at: datetime | None
    last_failure_at: datetime | None
    tenant_id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookEndpointListResponse(BaseModel):
    items: list["WebhookEndpointResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class WebhookEventResponse(BaseModel):
    id: UUID
    source: str
    external_id: str
    event_type: str
    event_category: str | None
    payload: dict[str, Any]
    raw_payload: str | None
    headers: dict[str, Any]
    query_params: dict[str, Any]
    status: str
    processing_attempts: int
    max_attempts: int
    last_error: str | None
    last_attempt_at: datetime | None
    processed_at: datetime | None
    processed_by: UUID | None
    idempotency_key: str | None
    retry_after: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookEventListResponse(BaseModel):
    items: list["WebhookEventResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int