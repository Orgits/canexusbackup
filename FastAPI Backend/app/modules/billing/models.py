import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.users.models import User


class InvoiceStatus(str, PyEnum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    BOUNCED = "bounced"


class ExpenseStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"
    PAID = "paid"


class Invoice(Base, TenantBaseModelMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_tenant_client", "tenant_id", "client_id"),
        Index("ix_invoices_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_invoices_tenant_status", "tenant_id", "status"),
        Index("ix_invoices_tenant_due_date", "tenant_id", "due_date"),
        Index("ix_invoices_tenant_number", "tenant_id", "invoice_number"),
        UniqueConstraint("tenant_id", "invoice_number", name="uq_tenant_invoice_number"),
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

    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)

    subtotal: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    paid_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    balance_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)

    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", back_populates="invoices", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", back_populates="invoices", lazy="selectin")
    items: Mapped[list["InvoiceItem"]] = relationship("InvoiceItem", back_populates="invoice", lazy="dynamic", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="invoice", lazy="dynamic")


class InvoiceItem(Base, TenantBaseModelMixin):
    __tablename__ = "invoice_items"
    __table_args__ = (
        Index("ix_invoice_items_tenant_invoice", "tenant_id", "invoice_id"),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)

    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    time_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
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
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items", lazy="selectin")


class Payment(Base, TenantBaseModelMixin):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_tenant_client", "tenant_id", "client_id"),
        Index("ix_payments_tenant_invoice", "tenant_id", "invoice_id"),
        Index("ix_payments_tenant_status", "tenant_id", "status"),
        Index("ix_payments_tenant_date", "tenant_id", "payment_date"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    payment_number: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="payments", lazy="selectin")


class Expense(Base, TenantBaseModelMixin):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_tenant_client", "tenant_id", "client_id"),
        Index("ix_expenses_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_expenses_tenant_user", "tenant_id", "user_id"),
        Index("ix_expenses_tenant_status", "tenant_id", "status"),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    expense_number: Mapped[str] = mapped_column(String(100), nullable=False)
    expense_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[ExpenseStatus] = mapped_column(Enum(ExpenseStatus), default=ExpenseStatus.DRAFT, nullable=False)

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_billable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_reimbursable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reimbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
