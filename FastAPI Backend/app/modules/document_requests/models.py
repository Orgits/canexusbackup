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
    from app.modules.clients.models import Client
    from app.modules.users.models import User


class DocumentRequestStatus(str, PyEnum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DocumentRequestPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DocumentRequest(Base, TenantBaseModelMixin):
    __tablename__ = "document_requests"
    __table_args__ = (
        Index("ix_document_requests_tenant_client", "tenant_id", "client_id"),
        Index("ix_document_requests_tenant_status", "tenant_id", "status"),
        Index("ix_document_requests_tenant_due", "tenant_id", "due_date"),
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

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[DocumentRequestStatus] = mapped_column(
        Enum(DocumentRequestStatus), default=DocumentRequestStatus.DRAFT, nullable=False, index=True
    )
    priority: Mapped[DocumentRequestPriority] = mapped_column(
        Enum(DocumentRequestPriority), default=DocumentRequestPriority.NORMAL, nullable=False
    )

    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    required_documents: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)

    submitted_documents: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_count: Mapped[int] = mapped_column(default=0, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to], lazy="selectin")
    documents: Mapped[list["DocumentRequestDocument"]] = relationship("DocumentRequestDocument", back_populates="request", lazy="dynamic", cascade="all, delete-orphan")


class DocumentRequestDocument(Base, TenantBaseModelMixin):
    __tablename__ = "document_request_documents"
    __table_args__ = (
        Index("ix_doc_request_docs_tenant_request", "tenant_id", "request_id"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    document_name: Mapped[str] = mapped_column(String(500), nullable=False)

    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    file_size: Mapped[int | None] = mapped_column(nullable=True)

    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_required: Mapped[bool] = mapped_column(default=True, nullable=False)

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    request: Mapped["DocumentRequest"] = relationship("DocumentRequest", back_populates="documents", lazy="selectin")