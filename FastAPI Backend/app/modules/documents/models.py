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
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.clients.models import Client
    from app.modules.communications.models import Communication
    from app.modules.compliance.models import ComplianceCycle
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.users.models import User


class DocumentStatus(str, PyEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ARCHIVED = "archived"
    QUARANTINED = "quarantined"


class DocumentCategory(str, PyEnum):
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


class Document(Base, TenantBaseModelMixin):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant_client", "tenant_id", "client_id"),
        Index("ix_documents_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_documents_tenant_status", "tenant_id", "status"),
        Index("ix_documents_tenant_category", "tenant_id", "category"),
        Index("ix_documents_tenant_uploaded_by", "tenant_id", "uploaded_by"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    compliance_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Numeric(20), nullable=False)

    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), default="azure_blob", nullable=False)
    storage_bucket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    is_latest_version: Mapped[bool] = mapped_column(default=True, nullable=False)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    category: Mapped[DocumentCategory] = mapped_column(Enum(DocumentCategory), default=DocumentCategory.OTHER, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False, index=True)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    source_communication_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communications.id", ondelete="SET NULL"),
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)

    retention_policy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    task: Mapped[Optional["Task"]] = relationship("Task", lazy="selectin")
    compliance_cycle: Mapped[Optional["ComplianceCycle"]] = relationship("ComplianceCycle", lazy="selectin")
    uploaded_by_user: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by], lazy="selectin")
    source_communication: Mapped[Optional["Communication"]] = relationship("Communication", lazy="selectin")
    previous_version: Mapped[Optional["Document"]] = relationship("Document", remote_side="Document.id", lazy="selectin")
    next_version: Mapped[Optional["Document"]] = relationship("Document", lazy="selectin")
