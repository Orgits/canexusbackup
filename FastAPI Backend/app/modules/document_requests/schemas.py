from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentRequestStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DocumentRequestPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DocumentRequestBase(BaseModel):
    client_id: UUID
    matter_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: DocumentRequestPriority = DocumentRequestPriority.NORMAL
    due_date: datetime | None = None
    expires_at: datetime | None = None
    required_documents: list[dict] = Field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRequestCreate(DocumentRequestBase):
    pass


class DocumentRequestUpdate(BaseModel):
    assigned_to: UUID | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    priority: DocumentRequestPriority | None = None
    due_date: datetime | None = None
    expires_at: datetime | None = None
    required_documents: list[dict] | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class DocumentRequestDocumentBase(BaseModel):
    document_name: str = Field(..., min_length=1, max_length=500)
    document_type: str | None = Field(None, max_length=100)
    file_size: int | None = None
    mime_type: str | None = Field(None, max_length=100)
    is_required: bool = True


class DocumentRequestDocumentCreate(DocumentRequestDocumentBase):
    document_id: UUID


class DocumentRequestDocumentResponse(BaseModel):
    id: UUID
    request_id: UUID
    document_id: UUID
    document_name: str
    document_type: str | None
    file_size: int | None
    mime_type: str | None
    is_required: bool
    uploaded_by: UUID | None
    uploaded_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentRequestResponse(BaseModel):
    id: UUID
    client_id: UUID
    matter_id: UUID | None
    assigned_to: UUID | None
    title: str
    description: str | None
    status: str
    priority: DocumentRequestPriority
    due_date: datetime | None
    expires_at: datetime | None
    required_documents: list[dict]
    submitted_documents: list[dict]
    notes: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by: UUID | None
    reminder_sent_at: datetime | None
    reminder_count: int
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentRequestDetailResponse(BaseModel):
    request: "DocumentRequestResponse"
    documents: list[DocumentRequestDocumentResponse] = []


class DocumentRequestListResponse(BaseModel):
    items: list["DocumentRequestResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int