from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.billing.models import (
    Expense,
    ExpenseStatus,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
)


class BillingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_invoice(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def get_invoice_by_id(self, invoice_id: UUID, tenant_id: UUID) -> Invoice | None:
        result = await self.db.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.client),
                selectinload(Invoice.matter),
                selectinload(Invoice.items),
                selectinload(Invoice.payments),
            )
            .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_invoice_by_number(self, invoice_number: str, tenant_id: UUID) -> Invoice | None:
        result = await self.db.execute(
            select(Invoice).where(Invoice.invoice_number == invoice_number, Invoice.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all_invoices(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        status: InvoiceStatus | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Invoice], int]:
        query = (
            select(Invoice)
            .options(
                selectinload(Invoice.client),
                selectinload(Invoice.matter),
            )
            .where(Invoice.tenant_id == tenant_id)
        )
        count_query = select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Invoice.invoice_number.ilike(f"%{search}%"),
                Invoice.notes.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(Invoice.client_id == client_id)
            count_query = count_query.where(Invoice.client_id == client_id)

        if matter_id:
            query = query.where(Invoice.matter_id == matter_id)
            count_query = count_query.where(Invoice.matter_id == matter_id)

        if status:
            query = query.where(Invoice.status == status)
            count_query = count_query.where(Invoice.status == status)

        if due_date_from:
            query = query.where(Invoice.due_date >= due_date_from)
            count_query = count_query.where(Invoice.due_date >= due_date_from)

        if due_date_to:
            query = query.where(Invoice.due_date <= due_date_to)
            count_query = count_query.where(Invoice.due_date <= due_date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Invoice, sort_by):
            sort_column = getattr(Invoice, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Invoice.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update_invoice(self, invoice: Invoice) -> Invoice:
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def delete_invoice(self, invoice: Invoice) -> None:
        await self.db.delete(invoice)
        await self.db.flush()

    async def create_payment(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def get_payment_by_id(self, payment_id: UUID, tenant_id: UUID) -> Payment | None:
        result = await self.db.execute(
            select(Payment)
            .options(
                selectinload(Payment.client),
                selectinload(Payment.invoice),
            )
            .where(Payment.id == payment_id, Payment.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all_payments(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        client_id: UUID | None = None,
        invoice_id: UUID | None = None,
        status: PaymentStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[Payment], int]:
        query = (
            select(Payment)
            .options(
                selectinload(Payment.client),
                selectinload(Payment.invoice),
            )
            .where(Payment.tenant_id == tenant_id)
        )
        count_query = select(func.count(Payment.id)).where(Payment.tenant_id == tenant_id)

        if client_id:
            query = query.where(Payment.client_id == client_id)
            count_query = count_query.where(Payment.client_id == client_id)

        if invoice_id:
            query = query.where(Payment.invoice_id == invoice_id)
            count_query = count_query.where(Payment.invoice_id == invoice_id)

        if status:
            query = query.where(Payment.status == status)
            count_query = count_query.where(Payment.status == status)

        if date_from:
            query = query.where(Payment.payment_date >= date_from)
            count_query = count_query.where(Payment.payment_date >= date_from)

        if date_to:
            query = query.where(Payment.payment_date <= date_to)
            count_query = count_query.where(Payment.payment_date <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Payment.payment_date.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update_payment(self, payment: Payment) -> Payment:
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def delete_payment(self, payment: Payment) -> None:
        await self.db.delete(payment)
        await self.db.flush()

    async def create_expense(self, expense: Expense) -> Expense:
        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def get_expense_by_id(self, expense_id: UUID, tenant_id: UUID) -> Expense | None:
        result = await self.db.execute(
            select(Expense)
            .options(
                selectinload(Expense.client),
                selectinload(Expense.matter),
                selectinload(Expense.user),
            )
            .where(Expense.id == expense_id, Expense.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all_expenses(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        client_id: UUID | None = None,
        matter_id: UUID | None = None,
        user_id: UUID | None = None,
        status: ExpenseStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[Expense], int]:
        query = (
            select(Expense)
            .options(
                selectinload(Expense.client),
                selectinload(Expense.matter),
                selectinload(Expense.user),
            )
            .where(Expense.tenant_id == tenant_id)
        )
        count_query = select(func.count(Expense.id)).where(Expense.tenant_id == tenant_id)

        if client_id:
            query = query.where(Expense.client_id == client_id)
            count_query = count_query.where(Expense.client_id == client_id)

        if matter_id:
            query = query.where(Expense.matter_id == matter_id)
            count_query = count_query.where(Expense.matter_id == matter_id)

        if user_id:
            query = query.where(Expense.user_id == user_id)
            count_query = count_query.where(Expense.user_id == user_id)

        if status:
            query = query.where(Expense.status == status)
            count_query = count_query.where(Expense.status == status)

        if date_from:
            query = query.where(Expense.expense_date >= date_from)
            count_query = count_query.where(Expense.expense_date >= date_from)

        if date_to:
            query = query.where(Expense.expense_date <= date_to)
            count_query = count_query.where(Expense.expense_date <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Expense.expense_date.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update_expense(self, expense: Expense) -> Expense:
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def delete_expense(self, expense: Expense) -> None:
        await self.db.delete(expense)
        await self.db.flush()
