from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


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
    matter_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    compliance_cycle_id: Optional[UUID] = None
    filename: str
    original_filename: str
    file_extension: str
    mime_type: str
    file_size: int
    storage_path: str
    storage_provider: str = "azure_blob"
    storage_bucket: Optional[str] = None
    storage_key: str
    category: DocumentCategory = DocumentCategory.OTHER
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: str = "manual"
    source_communication_id: Optional[UUID] = None
    retention_policy: Optional[str] = None
    retention_until: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    matter_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    compliance_cycle_id: Optional[UUID] = None
    category: Optional[DocumentCategory] = None
    status: Optional[DocumentStatus] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    retention_policy: Optional[str] = None
    retention_until: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(DocumentBase):
    id: UUID
    version: int
    is_latest_version: bool
    previous_version_id: Optional[UUID] = None
    status: DocumentStatus
    checksum: Optional[str] = None
    ocr_text: Optional[str] = None
    extracted_data: Dict[str, Any]
    classification: Optional[str] = None
    confidence_score: Optional[float] = None
    uploaded_by: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUploadInitRequest(BaseModel):
    filename: str
    file_size: int
    mime_type: str
    client_id: UUID
    matter_id: Optional[UUID] = None
    category: DocumentCategory = DocumentCategory.OTHER
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class DocumentUploadInitResponse(BaseModel):
    upload_url: str
    document_id: UUID
    storage_key: str
    expires_at: datetime