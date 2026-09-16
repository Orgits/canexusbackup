from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OpenSearchDocumentCreate(BaseModel):
    document_id: str
    title: str
    content: str
    extracted_text: str | None = None
    structured_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    status: str | None = None
    created_by: str | None = None
    client_id: str | None = None
    matter_id: str | None = None


class OpenSearchDocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    extracted_text: str | None = None
    structured_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    tags: list[str] | None = None
    category: str | None = None
    status: str | None = None


class OpenSearchDocumentResponse(BaseModel):
    id: str
    document_id: str
    title: str
    content: str
    extracted_text: str | None
    structured_data: dict[str, Any] | None
    metadata: dict[str, Any] | None
    tags: list[str]
    category: str | None
    status: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    client_id: str | None
    matter_id: str | None

    class Config:
        from_attributes = True


class OpenSearchSearchRequest(BaseModel):
    query: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str | None = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class OpenSearchSearchResponse(BaseModel):
    hits: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
    took_ms: int


class OpenSearchBulkIndexRequest(BaseModel):
    documents: list[dict[str, Any]]


class OpenSearchBulkIndexResponse(BaseModel):
    errors: bool
    items: list[dict]


class CommunicationSearchRequest(BaseModel):
    query: str | None = None
    channel: str | None = None
    direction: str | None = None
    status: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CommunicationSearchResponse(BaseModel):
    hits: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
    took_ms: int


class AIProcessingJobSearchRequest(BaseModel):
    query: str | None = None
    model_type: str | None = None
    status: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AIProcessingJobSearchResponse(BaseModel):
    hits: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
    took_ms: int


class OpenSearchHealthResponse(BaseModel):
    status: str
    cluster_name: str
    number_of_nodes: int
    active_primary_shards: int
    active_shards: int
    relocating_shards: int
    initializing_shards: int
    unassigned_shards: int
    number_of_pending_tasks: int