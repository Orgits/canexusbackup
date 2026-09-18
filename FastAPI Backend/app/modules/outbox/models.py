import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, BaseModelMixin


class OutboxEventType(str, PyEnum):
    COMPLIANCE_CYCLE_CREATED = "compliance.cycle_created"
    COMPLIANCE_CYCLE_UPDATED = "compliance.cycle_updated"
    COMPLIANCE_DUE_DATE_CHANGED = "compliance.due_date_changed"
    COMPLIANCE_REMINDER_SENT = "compliance.reminder_sent"

    INVOICE_CREATED = "invoice.created"
    INVOICE_UPDATED = "invoice.updated"
    INVOICE_SENT = "invoice.sent"
    INVOICE_PAID = "invoice.paid"
    INVOICE_VOIDED = "invoice.voided"

    PAYMENT_CREATED = "payment.created"
    PAYMENT_ALLOCATED = "payment.allocated"
    PAYMENT_REFUNDED = "payment.refunded"

    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"
    TASK_STATUS_CHANGED = "task.status_changed"

    WORKFLOW_TRANSITIONED = "workflow.transitioned"
    WORKFLOW_INSTANCE_CREATED = "workflow.instance_created"
    WORKFLOW_INSTANCE_COMPLETED = "workflow.instance_completed"

    NOTIFICATION_CREATED = "notification.created"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_DELIVERED = "notification.delivered"
    NOTIFICATION_FAILED = "notification.failed"

    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_CLASSIFIED = "document.classified"

    ASSIGNMENT_CREATED = "assignment.created"
    ASSIGNMENT_REASSIGNED = "assignment.reassigned"
    ASSIGNMENT_ESCALATED = "assignment.escalated"

    # Phase 5 - Reporting
    REPORT_COMPLETED = "report.completed"
    REPORT_FAILED = "report.failed"

    # Phase 5 - DPDP
    DATA_CORRECTION_APPLIED = "data_correction.applied"
    DATA_ERASURE_COMPLETED = "data_erasure.completed"
    RETENTION_EXECUTED = "retention.executed"


class OutboxStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class OutboxEvent(Base, BaseModelMixin):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_outbox_events_tenant_status", "tenant_id", "status"),
        Index("ix_outbox_events_tenant_type", "tenant_id", "event_type"),
        Index("ix_outbox_events_tenant_aggregate", "tenant_id", "aggregate_type", "aggregate_id"),
        Index("ix_outbox_events_created", "created_at"),
        Index("ix_outbox_events_status_retry", "status", "retry_count"),
    )

    event_type: Mapped[OutboxEventType] = mapped_column(Enum(OutboxEventType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)

    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    status: Mapped[OutboxStatus] = mapped_column(Enum(OutboxStatus, values_callable=lambda x: [e.value for e in x]), default=OutboxStatus.PENDING, nullable=False, index=True)

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
