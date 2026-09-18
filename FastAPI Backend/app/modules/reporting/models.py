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
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class ReportStatus(str, PyEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ReportFormat(str, PyEnum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class ReportDefinition(Base, TenantBaseModelMixin):
    __tablename__ = "report_definitions"
    __table_args__ = (
        Index("ix_report_definitions_tenant_category", "tenant_id", "category"),
        Index("ix_report_definitions_tenant_active", "tenant_id", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    query_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    output_format: Mapped[ReportFormat] = mapped_column(
        Enum(ReportFormat), default=ReportFormat.PDF, nullable=False
    )
    output_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)

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
    parameters: Mapped[list["ReportParameter"]] = relationship("ReportParameter", back_populates="report_definition", lazy="dynamic", cascade="all, delete-orphan")
    jobs: Mapped[list["ReportJob"]] = relationship("ReportJob", back_populates="report_definition", lazy="dynamic")
    schedules: Mapped[list["ReportSchedule"]] = relationship("ReportSchedule", back_populates="report_definition", lazy="dynamic", cascade="all, delete-orphan")


class ReportParameter(Base, TenantBaseModelMixin):
    __tablename__ = "report_parameters"
    __table_args__ = (
        Index("ix_report_parameters_tenant_definition", "tenant_id", "report_definition_id"),
    )

    report_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    param_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    validation_rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    order: Mapped[int] = mapped_column(default=0, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    report_definition: Mapped["ReportDefinition"] = relationship("ReportDefinition", back_populates="parameters", lazy="selectin")


class ReportJob(Base, TenantBaseModelMixin):
    __tablename__ = "report_jobs"
    __table_args__ = (
        Index("ix_report_jobs_tenant_definition", "tenant_id", "report_definition_id"),
        Index("ix_report_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_report_jobs_tenant_created", "tenant_id", "created_at"),
        Index("ix_report_jobs_idempotency_key", "tenant_id", "idempotency_key", unique=True),
    )

    report_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False, index=True
    )

    progress: Mapped[int] = mapped_column(default=0, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)

    result_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_format: Mapped[ReportFormat | None] = mapped_column(Enum(ReportFormat), nullable=True)
    result_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    report_definition: Mapped["ReportDefinition"] = relationship("ReportDefinition", back_populates="jobs", lazy="selectin")
    outputs: Mapped[list["ReportOutput"]] = relationship("ReportOutput", back_populates="job", lazy="dynamic", cascade="all, delete-orphan")


class ReportOutput(Base, TenantBaseModelMixin):
    __tablename__ = "report_outputs"
    __table_args__ = (
        Index("ix_report_outputs_tenant_job", "tenant_id", "job_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat), nullable=False)
    size_bytes: Mapped[int] = mapped_column(default=0, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(default=0, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    job: Mapped["ReportJob"] = relationship("ReportJob", back_populates="outputs", lazy="selectin")


class ReportSchedule(Base, TenantBaseModelMixin):
    __tablename__ = "report_schedules"
    __table_args__ = (
        Index("ix_report_schedules_tenant_definition", "tenant_id", "report_definition_id"),
        Index("ix_report_schedules_tenant_active", "tenant_id", "is_active"),
        Index("ix_report_schedules_next_run", "next_run_at"),
    )

    report_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recipients: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    report_definition: Mapped["ReportDefinition"] = relationship("ReportDefinition", back_populates="schedules", lazy="selectin")


class DashboardWidget(Base, TenantBaseModelMixin):
    __tablename__ = "dashboard_widgets"
    __table_args__ = (
        Index("ix_dashboard_widgets_tenant_type", "tenant_id", "widget_type"),
        Index("ix_dashboard_widgets_tenant_active", "tenant_id", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    query_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    display_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    layout: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    order: Mapped[int] = mapped_column(default=0, nullable=False)

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