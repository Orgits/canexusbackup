from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConsentStatus(str, Enum):
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class ConsentChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL = "call"
    POST = "post"
    ALL = "all"


class ConsentBase(BaseModel):
    client_id: UUID
    channel: ConsentChannel
    source: str = Field(..., max_length=100)
    source_reference: str | None = Field(None, max_length=255)
    consent_text: str
    version: str = Field(default="1.0", max_length=50)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConsentCreate(ConsentBase):
    pass


class ConsentUpdate(BaseModel):
    status: ConsentStatus | None = None
    consent_text: str | None = None
    version: str | None = Field(None, max_length=50)
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class ConsentResponse(BaseModel):
    id: UUID
    client_id: UUID
    channel: ConsentChannel
    status: ConsentStatus
    source: str
    source_reference: str | None
    ip_address: str | None
    user_agent: str | None
    consent_text: str
    version: str
    given_at: datetime | None
    withdrawn_at: datetime | None
    expires_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConsentListResponse(BaseModel):
    items: list[ConsentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConsentTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    channel: ConsentChannel
    consent_text: str
    version: str = Field(default="1.0", max_length=50)
    is_active: bool = True
    is_default: bool = False
    language: str = Field(default="en", max_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConsentTemplateCreate(ConsentTemplateBase):
    pass


class ConsentTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    language: str | None = Field(None, max_length=10)
    metadata: dict[str, Any] | None = None


class ConsentTemplateResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    channel: ConsentChannel
    consent_text: str
    version: str
    is_active: bool
    is_default: bool
    language: str
    metadata: dict[str, Any]
    tenant_id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConsentTemplateListResponse(BaseModel):
    items: list[ConsentTemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConsentStatsResponse(BaseModel):
    total_consents: int
    given_consents: int
    withdrawn_consents: int
    pending_consents: int
    expired_consents: int
    by_channel: dict[str, int]