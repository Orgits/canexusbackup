from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateCategory(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    DOCUMENT = "document"
    NOTIFICATION = "notification"
    GENERIC = "generic"


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: TemplateCategory
    subject: str | None = Field(None, max_length=500)
    content: str
    content_html: str | None = None
    variables: list[str] = Field(default_factory=list)
    channel: str = Field(..., max_length=50)
    language: str = Field(default="en", max_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    subject: str | None = Field(None, max_length=500)
    content: str | None = None
    content_html: str | None = None
    variables: list[str] | None = None
    channel: str | None = Field(None, max_length=50)
    language: str | None = Field(None, max_length=10)
    metadata: dict[str, Any] | None = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    category: TemplateCategory
    status: TemplateStatus
    subject: str | None
    content: str
    content_html: str | None
    variables: list[str]
    channel: str
    language: str
    version: int
    is_default: bool
    metadata: dict[str, Any]
    tenant_id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateDetailResponse(TemplateResponse):
    created_by: Any | None = None


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TemplateVersionCreate(BaseModel):
    content: str
    content_html: str | None = None
    variables: list[str] = Field(default_factory=list)
    subject: str | None = None