from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from app.core.database import get_async_db
from app.core.tenancy.dependencies import get_current_tenant
from app.core.security.dependencies import get_current_active_user
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.modules.billing.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceItemCreate,
    PaymentCreate,
    PaymentResponse,
    ExpenseCreate,
    ExpenseResponse,
)
from app.modules.billing.service import BillingService
from app.modules.billing.models import InvoiceStatus, PaymentStatus
from app.modules.users.models import User

router = APIRouter()


invoice_router = APIRouter(prefix="/invoices", tags=["Invoices"])


@invoice_router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    invoice = await service.create_invoice(data, current_tenant.id, current_user.id)
    return InvoiceResponse.model_validate(invoice)


@invoice_router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    matter_id: UUID = None,
    status: str = None,
    due_date_from: datetime = None,
    due_date_to: datetime = None,
    sort_by: str = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_READ)),
):
    service = BillingService(db)
    items, total = await service.get_all_invoices(
        current_tenant.id, page, page_size, search, client_id, matter_id, status,
        due_date_from, due_date_to, sort_by, sort_order
    )
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@invoice_router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_READ)),
):
    service = BillingService(db)
    invoice = await service.get_invoice_by_id(invoice_id, current_tenant.id)
    return InvoiceResponse.model_validate(invoice)


@invoice_router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    invoice = await service.update_invoice(invoice_id, current_tenant.id, data, current_user.id)
    return InvoiceResponse.model_validate(invoice)


@invoice_router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    invoice = await service.send_invoice(invoice_id, current_tenant.id, current_user.id)
    return InvoiceResponse.model_validate(invoice)


@invoice_router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    await service.delete_invoice(invoice_id, current_tenant.id)
    return None


payment_router = APIRouter(prefix="/payments", tags=["Payments"])


@payment_router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    payment = await service.create_payment(data, current_tenant.id, current_user.id)
    return PaymentResponse.model_validate(payment)


@payment_router.get("", response_model=list[PaymentResponse])
async def list_payments(
    page: int = 1,
    page_size: int = 20,
    client_id: UUID = None,
    invoice_id: UUID = None,
    status: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_READ)),
):
    service = BillingService(db)
    items, total = await service.get_all_payments(
        current_tenant.id, page, page_size, client_id, invoice_id, status, date_from, date_to
    )
    return [PaymentResponse.model_validate(item) for item in items]


@payment_router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_READ)),
):
    service = BillingService(db)
    payment = await service.get_payment_by_id(payment_id, current_tenant.id)
    return PaymentResponse.model_validate(payment)


@payment_router.patch("/{payment_id}/status", response_model=PaymentResponse)
async def update_payment_status(
    payment_id: UUID,
    status: PaymentStatus,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    payment = await service.update_payment(payment_id, current_tenant.id, status, current_user.id)
    return PaymentResponse.model_validate(payment)


@payment_router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    await service.delete_payment(payment_id, current_tenant.id)
    return None


expense_router = APIRouter(prefix="/expenses", tags=["Expenses"])


@expense_router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    expense = await service.create_expense(data, current_tenant.id, current_user.id)
    return ExpenseResponse.model_validate(expense)


@expense_router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
    page: int = 1,
    page_size: int = 20,
    client_id: UUID = None,
    matter_id: UUID = None,
    user_id: UUID = None,
    status: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_READ)),
):
    service = BillingService(db)
    items, total = await service.get_all_expenses(
        current_tenant.id, page, page_size, client_id, matter_id, user_id, status, date_from, date_to
    )
    return [ExpenseResponse.model_validate(item) for item in items]


@expense_router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_READ)),
):
    service = BillingService(db)
    expense = await service.get_expense_by_id(expense_id, current_tenant.id)
    return ExpenseResponse.model_validate(expense)


@expense_router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: UUID,
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    expense = await service.update_expense(expense_id, current_tenant.id, data, current_user.id)
    return ExpenseResponse.model_validate(expense)


@expense_router.post("/{expense_id}/approve", response_model=ExpenseResponse)
async def approve_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    expense = await service.approve_expense(expense_id, current_tenant.id, current_user.id)
    return ExpenseResponse.model_validate(expense)


@expense_router.post("/{expense_id}/reimburse", response_model=ExpenseResponse)
async def reimburse_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    expense = await service.reimburse_expense(expense_id, current_tenant.id, current_user.id)
    return ExpenseResponse.model_validate(expense)


@expense_router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_tenant=Depends(get_current_tenant),
    current_user: User = Depends(require_permission(Permission.BILLING_MANAGE)),
):
    service = BillingService(db)
    await service.delete_expense(expense_id, current_tenant.id)
    return None


router.include_router(invoice_router)
router.include_router(payment_router)
router.include_router(expense_router)