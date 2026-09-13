from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


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
    service_type: Optional[str] = Field(None, max_length=100)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    time_entry_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    matter_id: Optional[UUID] = None
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: datetime
    due_date: datetime
    currency: str = "INR"
    notes: Optional[str] = None
    terms: Optional[str] = None
    items: List[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    matter_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = None
    terms: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    status: InvoiceStatus
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    paid_amount: float
    balance_amount: float
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaymentBase(BaseModel):
    client_id: UUID
    invoice_id: Optional[UUID] = None
    payment_number: str = Field(..., min_length=1, max_length=100)
    payment_date: datetime
    amount: float = Field(..., gt=0)
    method: Optional[str] = Field(None, max_length=50)
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


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
    client_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    expense_number: str = Field(..., min_length=1, max_length=100)
    expense_date: datetime
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    category: str = Field(..., min_length=1, max_length=100)
    description: str
    vendor: Optional[str] = Field(None, max_length=255)
    receipt_url: Optional[str] = Field(None, max_length=500)
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
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    reimbursed_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True