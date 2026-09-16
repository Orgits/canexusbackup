from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    BOUNCED = "bounced"


class ExpenseStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"
    PAID = "paid"


class InvoiceItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0, ge=0, le=100)
    discount: float = Field(default=0, ge=0)
    service_type: str | None = Field(None, max_length=100)
    period_start: datetime | None = None
    period_end: datetime | None = None
    time_entry_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(InvoiceItemBase):
    id: UUID
    total: float
    invoice_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    client_id: UUID
    matter_id: UUID | None = None
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: datetime
    due_date: datetime
    currency: str = "INR"
    notes: str | None = None
    terms: str | None = None
    items: list[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    matter_id: UUID | None = None
    due_date: datetime | None = None
    status: InvoiceStatus | None = None
    notes: str | None = None
    terms: str | None = None
    items: list[InvoiceItemCreate] | None = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    status: InvoiceStatus
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    paid_amount: float
    balance_amount: float
    sent_at: datetime | None = None
    paid_at: datetime | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaymentBase(BaseModel):
    client_id: UUID
    invoice_id: UUID | None = None
    payment_number: str = Field(..., min_length=1, max_length=100)
    payment_date: datetime
    amount: float = Field(..., gt=0)
    method: str | None = Field(None, max_length=50)
    reference: str | None = Field(None, max_length=100)
    notes: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: UUID
    status: PaymentStatus
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExpenseBase(BaseModel):
    client_id: UUID | None = None
    matter_id: UUID | None = None
    expense_number: str = Field(..., min_length=1, max_length=100)
    expense_date: datetime
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    category: str = Field(..., min_length=1, max_length=100)
    description: str
    vendor: str | None = Field(None, max_length=255)
    receipt_url: str | None = Field(None, max_length=500)
    is_billable: bool = False
    is_reimbursable: bool = True


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseResponse(ExpenseBase):
    id: UUID
    user_id: UUID
    status: ExpenseStatus
    is_billable: bool
    is_reimbursable: bool
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    reimbursed_at: datetime | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
