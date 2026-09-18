import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
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
    from app.modules.users.models import User
    from app.modules.clients.models import Client
    from app.modules.documents.models import Document
    from app.modules.matters.models import Matter


class UDINStatus(str, PyEnum):
    GENERATED = "generated"
    VERIFIED = "verified"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class UDINRecord(Base, TenantBaseModelMixin):
    __tablename__ = "udin_records"
    __table_args__ = (
        Index("ix_udin_records_tenant_udin", "tenant_id", "udin", unique=True),
        Index("ix_udin_records_tenant_professional", "tenant_id", "professional_id"),
        Index("ix_udin_records_tenant_client", "tenant_id", "client_id"),
        Index("ix_udin_records_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_udin_records_tenant_document", "tenant_id", "document_id"),
        Index("ix_udin_records_tenant_status", "tenant_id", "status"),
        Index("ix_udin_records_tenant_generated", "tenant_id", "generated_at"),
    )

    udin: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[UDINStatus] = mapped_column(
        Enum(UDINStatus), default=UDINStatus.GENERATED, nullable=False, index=True
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    matter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    financial_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    quarter: Mapped[str | None] = mapped_column(String(10), nullable=True)

    form_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cancelled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    external_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    professional: Mapped["User"] = relationship("User", foreign_keys=[professional_id], lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    document: Mapped[Optional["Document"]] = relationship("Document", lazy="selectin")
    verified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by_id], lazy="selectin")
    cancelled_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[cancelled_by_id], lazy="selectin")
    verification_logs: Mapped[list["UDINVerificationLog"]] = relationship("UDINVerificationLog", back_populates="udin_record", lazy="dynamic", cascade="all, delete-orphan")


class UDINVerificationLog(Base, TenantBaseModelMixin):
    __tablename__ = "udin_verification_logs"
    __table_args__ = (
        Index("ix_udin_verification_logs_tenant_udin", "tenant_id", "udin_record_id"),
        Index("ix_udin_verification_logs_tenant_user", "tenant_id", "verified_by_id"),
        Index("ix_udin_verification_logs_tenant_result", "tenant_id", "result"),
    )

    udin_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("udin_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    verified_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    result: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    verification_method: Mapped[str] = mapped_column(String(50), nullable=False)

    external_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    udin_record: Mapped["UDINRecord"] = relationship("UDINRecord", back_populates="verification_logs", lazy="selectin")
    verified_by: Mapped["User"] = relationship("User", foreign_keys=[verified_by_id], lazy="selectin")