from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ARCHIVED = "archived"
    QUARANTINED = "quarantined"


class DocumentCategory(str, Enum):
    KYC = "kyc"
    FINANCIAL = "financial"
    TAX = "tax"
    LEGAL = "legal"
    CORPORATE = "corporate"
    COMPLIANCE = "compliance"
    CORRESPONDENCE = "correspondence"
    CONTRACT = "contract"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"
    OTHER = "other"


class DocumentBase(BaseModel):
    client_id: UUID
    matter_id: UUID | None = None
    task_id: UUID | None = None
    compliance_cycle_id: UUID | None = None
    filename: str
    original_filename: str
    file_extension: str
    mime_type: str
    file_size: int
    storage_path: str
    storage_provider: str = "azure_blob"
    storage_bucket: str | None = None
    storage_key: str
    category: DocumentCategory = DocumentCategory.OTHER
    title: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"
    source_communication_id: UUID | None = None
    retention_policy: str | None = None
    retention_until: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    matter_id: UUID | None = None
    task_id: UUID | None = None
    compliance_cycle_id: UUID | None = None
    category: DocumentCategory | None = None
    status: DocumentStatus | None = None
    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    retention_policy: str | None = None
    retention_until: datetime | None = None
    metadata: dict[str, Any] | None = None


class DocumentResponse(DocumentBase):
    id: UUID
    version: int
    is_latest_version: bool
    previous_version_id: UUID | None = None
    status: DocumentStatus
    checksum: str | None = None
    ocr_text: str | None = None
    extracted_data: dict[str, Any]
    classification: str | None = None
    confidence_score: float | None = None
    uploaded_by: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUploadInitRequest(BaseModel):
    filename: str
    file_size: int
    mime_type: str
    client_id: UUID
    matter_id: UUID | None = None
    category: DocumentCategory = DocumentCategory.OTHER
    title: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class DocumentUploadCompleteRequest(BaseModel):
    checksum: str = Field(..., description="SHA256 checksum of the uploaded file")
    checksum_algorithm: str = Field(default="sha256", description="Checksum algorithm (sha256, md5)")


class DocumentUploadInitResponse(BaseModel):
    upload_url: str
    document_id: UUID
    storage_key: str
    expires_at: datetime


class DocumentDownloadResponse(BaseModel):
    download_url: str
    expires_at: datetime


class DocumentMetadataResponse(BaseModel):
    blob_name: str
    size: int
    etag: str | None = None
    last_modified: datetime | None = None
    content_type: str | None = None
    metadata: dict[str, str] | None = None