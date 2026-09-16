from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OCRStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCREngine(str, Enum):
    TESSERACT = "tesseract"
    AWS_TEXTRACT = "aws_textract"
    GOOGLE_VISION = "google_vision"
    AZURE_FORM_RECOGNIZER = "azure_form_recognizer"
    CUSTOM = "custom"


class OCRJobBase(BaseModel):
    document_id: UUID
    engine: OCREngine
    language: str = Field(default="eng", max_length=10)


class OCRJobCreate(OCRJobBase):
    pass


class OCRJobUpdate(BaseModel):
    language: str | None = Field(None, max_length=10)
    status: str | None = None


class OCRJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    engine: OCREngine
    status: str
    language: str
    pages_processed: int
    total_pages: int
    extracted_text: str | None
    structured_data: dict[str, Any]
    confidence_score: float | None
    processing_time_ms: int
    error_message: str | None
    retry_count: int
    max_retries: int
    started_at: datetime | None
    completed_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OCRJobListResponse(BaseModel):
    items: list["OCRJobResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class OCRTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    engine: OCREngine
    language: str = Field(default="eng", max_length=10)
    config: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict] = Field(default_factory=list)
    is_active: bool = True
    is_default: bool = False


class OCRTemplateCreate(OCRTemplateBase):
    pass


class OCRTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    engine: OCREngine | None = None
    language: str | None = Field(None, max_length=10)
    config: dict[str, Any] | None = None
    fields: list[dict] | None = None
    is_active: bool | None = None
    is_default: bool | None = None


class OCRTemplateResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    engine: OCREngine
    language: str
    config: dict[str, Any]
    fields: list[dict]
    is_active: bool
    is_default: bool
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OCRTemplateListResponse(BaseModel):
    items: list[OCRTemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OCRProcessRequest(BaseModel):
    document_id: UUID
    engine: OCREngine | None = None
    language: str = Field(default="eng", max_length=10)
    template_id: UUID | None = None