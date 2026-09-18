from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentPipelineRequest(BaseModel):
    document_id: UUID
    ocr_engine: str = Field(default="tesseract", pattern="^(tesseract|aws_textract|google_vision|azure_form_recognizer|custom)$")
    classification_model_id: UUID | None = None
    extraction_model_id: UUID | None = None
    skip_review: bool = False


class DocumentPipelineResponse(BaseModel):
    document_id: str
    stages: dict[str, Any]
    final_status: str
    review_required: bool
    error: str | None = None


class DocumentPipelineStatusResponse(BaseModel):
    document_id: str
    document_status: str
    ocr_status: str
    ocr_job_id: str | None
    ai_jobs: list[dict[str, Any]]
    classification: str | None
    extracted_data: dict[str, Any] | None
    confidence_score: float | None