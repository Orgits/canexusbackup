import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.documents.models import Document
    from app.modules.users.models import User


class OCRStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCREngine(str, PyEnum):
    TESSERACT = "tesseract"
    AWS_TEXTRACT = "aws_textract"
    GOOGLE_VISION = "google_vision"
    AZURE_FORM_RECOGNIZER = "azure_form_recognizer"
    CUSTOM = "custom"


class OCRJob(Base, TenantBaseModelMixin):
    __tablename__ = "ocr_jobs"
    __table_args__ = (
        Index("ix_ocr_jobs_tenant_document", "tenant_id", "document_id"),
        Index("ix_ocr_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_ocr_jobs_tenant_engine", "tenant_id", "engine"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    engine: Mapped[OCREngine] = mapped_column(Enum(OCREngine), nullable=False, index=True)

    status: Mapped[OCRStatus] = mapped_column(Enum(OCRStatus), default=OCRStatus.PENDING, nullable=False, index=True)

    language: Mapped[str] = mapped_column(String(10), default="eng", nullable=False)

    pages_processed: Mapped[int] = mapped_column(default=0, nullable=False)
    total_pages: Mapped[int] = mapped_column(default=0, nullable=False)

    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    confidence_score: Mapped[float | None] = mapped_column(nullable=True)

    processing_time_ms: Mapped[int] = mapped_column(default=0, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id], lazy="selectin")


class OCRTemplate(Base, TenantBaseModelMixin):
    __tablename__ = "ocr_templates"
    __table_args__ = (
        Index("ix_ocr_templates_tenant_name", "tenant_id", "name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    engine: Mapped[OCREngine] = mapped_column(Enum(OCREngine), nullable=False)

    language: Mapped[str] = mapped_column(String(10), default="eng", nullable=False)

    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    fields: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")