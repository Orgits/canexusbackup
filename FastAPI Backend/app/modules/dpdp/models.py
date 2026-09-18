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
from app.modules.clients.models import Client
from app.modules.users.models import User

if TYPE_CHECKING:
    pass


class DataAccessStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPILING = "compiling"
    READY = "ready"
    DELIVERED = "delivered"
    EXPIRED = "expired"
    FAILED = "failed"


class DataCorrectionStatus(str, PyEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


class DataErasureStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class RetentionAction(str, PyEnum):
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"


class DataAccessRequest(Base, TenantBaseModelMixin):
    __tablename__ = "data_access_requests"
    __table_args__ = (
        Index("ix_data_access_requests_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_data_access_requests_tenant_status", "tenant_id", "status"),
        Index("ix_data_access_requests_tenant_client", "tenant_id", "client_id"),
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    scope: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[DataAccessStatus] = mapped_column(
        Enum(DataAccessStatus), default=DataAccessStatus.PENDING, nullable=False, index=True
    )

    compiled_data_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    compiled_size: Mapped[int | None] = mapped_column(nullable=True)
    compiled_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    subject: Mapped["User"] = relationship("User", foreign_keys=[subject_id], lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", foreign_keys=[client_id], lazy="selectin")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id], lazy="selectin")


class DataCorrectionRequest(Base, TenantBaseModelMixin):
    __tablename__ = "data_correction_requests"
    __table_args__ = (
        Index("ix_data_correction_requests_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_data_correction_requests_tenant_status", "tenant_id", "status"),
        Index("ix_data_correction_requests_tenant_client", "tenant_id", "client_id"),
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[DataCorrectionStatus] = mapped_column(
        Enum(DataCorrectionStatus), default=DataCorrectionStatus.PENDING, nullable=False, index=True
    )

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    subject: Mapped["User"] = relationship("User", foreign_keys=[subject_id], lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", foreign_keys=[client_id], lazy="selectin")
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")
    applied_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[applied_by_id], lazy="selectin")


class DataErasureRequest(Base, TenantBaseModelMixin):
    __tablename__ = "data_erasure_requests"
    __table_args__ = (
        Index("ix_data_erasure_requests_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_data_erasure_requests_tenant_status", "tenant_id", "status"),
        Index("ix_data_erasure_requests_tenant_client", "tenant_id", "client_id"),
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    scope: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_refs: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    status: Mapped[DataErasureStatus] = mapped_column(
        Enum(DataErasureStatus), default=DataErasureStatus.PENDING, nullable=False, index=True
    )

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entities_affected: Mapped[int] = mapped_column(default=0, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    subject: Mapped["User"] = relationship("User", foreign_keys=[subject_id], lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", foreign_keys=[client_id], lazy="selectin")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id], lazy="selectin")


class RetentionPolicy(Base, TenantBaseModelMixin):
    __tablename__ = "retention_policies"
    __table_args__ = (
        Index("ix_retention_policies_tenant_entity", "tenant_id", "entity_type"),
        Index("ix_retention_policies_tenant_active", "tenant_id", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    criteria: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    retention_days: Mapped[int] = mapped_column(default=2555, nullable=False)
    action: Mapped[RetentionAction] = mapped_column(Enum(RetentionAction), default=RetentionAction.DELETE, nullable=False)

    protected: Mapped[bool] = mapped_column(default=False, nullable=False)
    protection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    executions: Mapped[list["RetentionExecution"]] = relationship("RetentionExecution", back_populates="policy", lazy="dynamic")


class RetentionExecution(Base, TenantBaseModelMixin):
    __tablename__ = "retention_executions"
    __table_args__ = (
        Index("ix_retention_executions_tenant_policy", "tenant_id", "policy_id"),
        Index("ix_retention_executions_tenant_status", "tenant_id", "status"),
        Index("ix_retention_executions_executed_at", "executed_at"),
    )

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retention_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    entities_affected: Mapped[int] = mapped_column(default=0, nullable=False)
    entities_processed: Mapped[int] = mapped_column(default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    policy: Mapped["RetentionPolicy"] = relationship("RetentionPolicy", back_populates="executions", lazy="selectin")


class DataResidencyRecord(Base, TenantBaseModelMixin):
    __tablename__ = "data_residency_records"
    __table_args__ = (
        Index("ix_data_residency_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_data_residency_tenant_region", "tenant_id", "region"),
    )

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    legal_basis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_categories: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    verified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by_id], lazy="selectin")