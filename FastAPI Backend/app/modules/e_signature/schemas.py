from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ESignatureProvider(str, Enum):
    DOCUSIGN = "docusign"
    ADOBE_SIGN = "adobe_sign"
    HELLOSIGN = "hellosign"
    PANDA_DOC = "panda_doc"
    SIGNNOW = "signnow"
    INTERNAL = "internal"


class ESignatureRequestStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ESignerStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"


class ESignatureRequestBase(BaseModel):
    document_id: UUID
    engagement_document_id: UUID | None = None
    provider: ESignatureProvider
    title: str = Field(..., min_length=1, max_length=500)
    subject: str | None = Field(None, max_length=500)
    message: str | None = None
    signing_order: bool = False
    expires_at: datetime | None = None
    reminder_frequency_days: int | None = Field(None, ge=1, le=30)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class ESignatureRequestCreate(ESignatureRequestBase):
    pass


class ESignatureRequestUpdate(BaseModel):
    provider: ESignatureProvider | None = None
    status: str | None = None
    title: str | None = Field(None, min_length=1, max_length=500)
    subject: str | None = Field(None, max_length=500)
    message: str | None = None
    signing_order: bool | None = None
    expires_at: datetime | None = None
    reminder_frequency_days: int | None = Field(None, ge=1, le=30)
    extra_metadata: dict[str, Any] | None = None


class ESignatureRequestResponse(BaseModel):
    id: UUID
    document_id: UUID
    engagement_document_id: UUID | None
    provider: ESignatureProvider
    status: str
    external_request_id: str | None
    title: str
    subject: str | None
    message: str | None
    signing_order: bool
    expires_at: datetime | None
    reminder_frequency_days: int | None
    reminder_count: int
    last_reminder_sent_at: datetime | None
    completed_at: datetime | None
    declined_at: datetime | None
    declined_by_id: UUID | None
    decline_reason: str | None
    provider_response: dict | None
    webhook_events: list[dict]
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class ESignatureRequestDetailResponse(ESignatureRequestResponse):
    document: Any | None = None
    engagement_document: Any | None = None
    signers: list[Any] = Field(default_factory=list)
    declined_by: Any | None = None


class ESignatureRequestListResponse(BaseModel):
    items: list[ESignatureRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ESignerBase(BaseModel):
    request_id: UUID
    signer_id: UUID | None = None
    email: str = Field(..., max_length=320)
    name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=100)
    signing_order: int = Field(default=1, ge=1)
    authentication_method: str | None = Field(None, max_length=50)
    access_code: str | None = Field(None, max_length=100)
    phone_number: str | None = Field(None, max_length=50)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class ESignerCreate(ESignerBase):
    pass


class ESignerUpdate(BaseModel):
    signer_id: UUID | None = None
    email: str | None = Field(None, max_length=320)
    name: str | None = Field(None, min_length=1, max_length=200)
    role: str | None = Field(None, min_length=1, max_length=100)
    signing_order: int | None = Field(None, ge=1)
    status: str | None = None
    authentication_method: str | None = Field(None, max_length=50)
    access_code: str | None = Field(None, max_length=100)
    phone_number: str | None = Field(None, max_length=50)
    signature_data: dict[str, Any] | None = None
    decline_reason: str | None = None
    extra_metadata: dict[str, Any] | None = None


class ESignerResponse(BaseModel):
    id: UUID
    request_id: UUID
    signer_id: UUID | None
    email: str
    name: str
    role: str
    signing_order: int
    status: str
    external_signer_id: str | None
    authentication_method: str | None
    access_code: str | None
    phone_number: str | None
    sent_at: datetime | None
    viewed_at: datetime | None
    signed_at: datetime | None
    declined_at: datetime | None
    decline_reason: str | None
    signature_data: dict | None
    provider_response: dict | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class ESignerDetailResponse(ESignerResponse):
    signer: Any | None = None


class ESignerListResponse(BaseModel):
    items: list[ESignerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ESignatureProviderConfigBase(BaseModel):
    provider: ESignatureProvider
    is_active: bool = False
    is_default: bool = False
    api_base_url: str = Field(..., min_length=1, max_length=500)
    client_id: str = Field(..., min_length=1, max_length=200)
    client_secret: str = Field(..., min_length=1)
    account_id: str | None = Field(None, max_length=200)
    webhook_secret: str | None = None
    oauth_redirect_uri: str | None = Field(None, max_length=500)
    scopes: list[str] = Field(default_factory=list)
    rate_limit_per_minute: int = Field(default=100, ge=1, le=1000)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    extra_config: dict[str, Any] = Field(default_factory=dict)


class ESignatureProviderConfigCreate(ESignatureProviderConfigBase):
    pass


class ESignatureProviderConfigUpdate(BaseModel):
    is_active: bool | None = None
    is_default: bool | None = None
    api_base_url: str | None = Field(None, min_length=1, max_length=500)
    client_id: str | None = Field(None, min_length=1, max_length=200)
    client_secret: str | None = None
    account_id: str | None = Field(None, max_length=200)
    webhook_secret: str | None = None
    oauth_redirect_uri: str | None = Field(None, max_length=500)
    scopes: list[str] | None = None
    rate_limit_per_minute: int | None = Field(None, ge=1, le=1000)
    timeout_seconds: int | None = Field(None, ge=5, le=300)
    extra_config: dict[str, Any] | None = None


class ESignatureProviderConfigResponse(BaseModel):
    id: UUID
    provider: ESignatureProvider
    is_active: bool
    is_default: bool
    api_base_url: str
    client_id: str
    account_id: str | None
    oauth_redirect_uri: str | None
    scopes: list[str]
    rate_limit_per_minute: int
    timeout_seconds: int
    extra_config: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class ESignatureProviderConfigDetailResponse(ESignatureProviderConfigResponse):
    pass


class ESignatureProviderConfigListResponse(BaseModel):
    items: list[ESignatureProviderConfigResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ESignatureSendRequest(BaseModel):
    request_id: UUID
    signers: list[ESignerCreate] | None = None
    idempotency_key: str | None = Field(None, max_length=200)


class ESignatureCancelRequest(BaseModel):
    request_id: UUID
    reason: str | None = None


class ESignatureWebhookEventBase(BaseModel):
    provider: ESignatureProvider
    external_event_id: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(..., min_length=1, max_length=100)
    external_request_id: str | None = Field(None, max_length=200)
    payload: dict[str, Any]
    idempotency_key: str | None = Field(None, max_length=200)


class ESignatureWebhookEventCreate(ESignatureWebhookEventBase):
    pass


class ESignatureWebhookEventResponse(BaseModel):
    id: UUID
    provider: ESignatureProvider
    external_event_id: str
    event_type: str
    external_request_id: str | None
    payload: dict
    processed: bool
    processed_at: datetime | None
    processing_error: str | None
    retry_count: int
    idempotency_key: str | None
    received_at: datetime
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class ESignatureWebhookEventListResponse(BaseModel):
    items: list[ESignatureWebhookEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int