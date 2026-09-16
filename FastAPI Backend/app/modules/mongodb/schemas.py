from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RawPayloadCreate(BaseModel):
    source: str = Field(..., max_length=100)
    payload: dict[str, Any]
    document_id: UUID | None = None
    idempotency_key: str | None = Field(None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawPayloadResponse(BaseModel):
    id: str
    tenant_id: UUID
    source: str
    payload: dict[str, Any]
    document_id: UUID | None
    idempotency_key: str | None
    metadata: dict[str, Any]
    received_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RawPayloadListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentRawCreate(BaseModel):
    document_id: UUID
    content: str
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    ocr_result: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRawUpdate(BaseModel):
    content: str | None = None
    extracted_data: dict[str, Any] | None = None
    ocr_result: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class DocumentRawResponse(BaseModel):
    id: str
    tenant_id: UUID
    document_id: UUID
    content: str
    extracted_data: dict[str, Any]
    ocr_result: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIRawPayloadCreate(BaseModel):
    job_id: UUID
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIRawPayloadResponse(BaseModel):
    id: str
    tenant_id: UUID
    job_id: UUID
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    metadata: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookRawCreate(BaseModel):
    source: str = Field(..., max_length=100)
    external_id: str = Field(..., max_length=255)
    payload: dict[str, Any]
    headers: dict[str, str] = Field(default_factory=dict)
    query_params: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str | None = Field(None, max_length=255)


class WebhookRawResponse(BaseModel):
    id: str
    tenant_id: UUID
    source: str
    external_id: str
    payload: dict[str, Any]
    headers: dict[str, str]
    query_params: dict[str, str]
    idempotency_key: str | None
    received_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True