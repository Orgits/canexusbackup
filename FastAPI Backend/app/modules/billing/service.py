from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException
from app.modules.billing.models import Invoice, InvoiceItem, Payment, Expense, InvoiceStatus, PaymentStatus, ExpenseStatus
from app.modules.billing.schemas import InvoiceCreate, InvoiceUpdate, InvoiceItemCreate, PaymentCreate, ExpenseCreate
from app.modules.billing.repository import BillingRepository
from app.modules.clients.models import Client
from app.modules.matters.models import Matter
from app.modules.users.models import User


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = BillingRepository(db)

    def _calculate_invoice_totals(self, items: List[InvoiceItemCreate]) -> tuple:
        subtotal = Decimal("0")
        tax_amount = Decimal("0")
        discount_amount = Decimal("0")

        for item in items:
            line_subtotal = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
            line_discount = Decimal(str(item.discount))
            line_tax = (line_subtotal - line_discount) * Decimal(str(item.tax_rate)) / Decimal("100")

            subtotal += line_subtotal
            discount_amount += line_discount
            tax_amount += line_tax

        total_amount = subtotal + tax_amount - discount_amount
        return float(subtotal), float(tax_amount), float(discount_amount), float(total_amount)

    async def create_invoice(self, data: InvoiceCreate, tenant_id: UUID, created_by: UUID) -> Invoice:
        existing = await self.repository.get_invoice_by_number(data.invoice_number, tenant_id)
        if existing:
            raise ConflictException(detail="Invoice with this number already exists")

        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        if data.matter_id:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == data.matter_id, Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        subtotal, tax_amount, discount_amount, total_amount = self._calculate_invoice_totals(data.items)

        invoice = Invoice(
            client_id=data.client_id,
            matter_id=data.matter_id,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            currency=data.currency,
            notes=data.notes,
            terms=data.terms,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            balance_amount=total_amount,
            tenant_id=tenant_id,
            created_by=created_by,
            status=InvoiceStatus.DRAFT,
        )
        invoice = await self.repository.create_invoice(invoice)

        for item_data in data.items:
            line_subtotal = Decimal(str(item_data.quantity)) * Decimal(str(item_data.unit_price))
            line_discount = Decimal(str(item_data.discount))
            line_tax = (line_subtotal - line_discount) * Decimal(str(item_data.tax_rate)) / Decimal("100")
            line_total = line_subtotal + line_tax - line_discount

            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data.description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                tax_rate=item_data.tax_rate,
                discount=item_data.discount,
                total=float(line_total),
                service_type=item_data.service_type,
                period_start=item_data.period_start,
                period_end=item_data.period_end,
                time_entry_id=item_data.time_entry_id,
                metadata=item_data.metadata,
                tenant_id=tenant_id,
                created_by=created_by,
            )
            self.db.add(item)

        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def get_invoice_by_id(self, invoice_id: UUID, tenant_id: UUID) -> Invoice:
        invoice = await self.repository.get_invoice_by_id(invoice_id, tenant_id)
        if not invoice:
            raise NotFoundException(detail="Invoice not found")
        return invoice

    async def get_all_invoices(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        matter_id: Optional[UUID] = None,
        status: Optional[InvoiceStatus] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Invoice], int]:
        return await self.repository.get_all_invoices(
            tenant_id, page, page_size, search, client_id, matter_id, status,
            due_date_from, due_date_to, sort_by, sort_order
        )

    async def update_invoice(self, invoice_id: UUID, tenant_id: UUID, data: InvoiceUpdate, updated_by: UUID) -> Invoice:
        invoice = await self.get_invoice_by_id(invoice_id, tenant_id)

        if data.items is not None:
            subtotal, tax_amount, discount_amount, total_amount = self._calculate_invoice_totals(data.items)
            invoice.subtotal = subtotal
            invoice.tax_amount = tax_amount
            invoice.discount_amount = discount_amount
            invoice.total_amount = total_amount
            invoice.balance_amount = total_amount - invoice.paid_amount

            await self.db.execute(
                select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id).delete()
            )
            for item_data in data.items:
                line_subtotal = Decimal(str(item_data.quantity)) * Decimal(str(item_data.unit_price))
                line_discount = Decimal(str(item_data.discount))
                line_tax = (line_subtotal - line_discount) * Decimal(str(item_data.tax_rate)) / Decimal("100")
                line_total = line_subtotal + line_tax - line_discount

                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data.description,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    tax_rate=item_data.tax_rate,
                    discount=item_data.discount,
                    total=float(line_total),
                    service_type=item_data.service_type,
                    period_start=item_data.period_start,
                    period_end=item_data.period_end,
                    time_entry_id=item_data.time_entry_id,
                    metadata=item_data.metadata,
                    tenant_id=tenant_id,
                    created_by=updated_by,
                )
                self.db.add(item)

        update_data = data.model_dump(exclude_unset=True, exclude={"items"})
        for field, value in update_data.items():
            setattr(invoice, field, value)
        invoice.updated_by = updated_by

        if invoice.status == InvoiceStatus.SENT and not invoice.sent_at:
            invoice.sent_at = datetime.now(timezone.utc)
        elif invoice.status == InvoiceStatus.PAID and not invoice.paid_at:
            invoice.paid_at = datetime.now(timezone.utc)

        return await self.repository.update_invoice(invoice)

    async def delete_invoice(self, invoice_id: UUID, tenant_id: UUID) -> None:
        invoice = await self.get_invoice_by_id(invoice_id, tenant_id)
        await self.repository.delete_invoice(invoice)

    async def send_invoice(self, invoice_id: UUID, tenant_id: UUID, sent_by: UUID) -> Invoice:
        invoice = await self.get_invoice_by_id(invoice_id, tenant_id)
        if invoice.status != InvoiceStatus.DRAFT:
            raise ConflictException(detail="Only draft invoices can be sent")
        invoice.status = InvoiceStatus.SENT
        invoice.sent_at = datetime.now(timezone.utc)
        invoice.updated_by = sent_by
        return await self.repository.update_invoice(invoice)

    async def create_payment(self, data: PaymentCreate, tenant_id: UUID, created_by: UUID) -> Payment:
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        if data.invoice_id:
            invoice_result = await self.db.execute(
                select(Invoice).where(Invoice.id == data.invoice_id, Invoice.tenant_id == tenant_id)
            )
            invoice = invoice_result.scalar_one_or_none()
            if not invoice:
                raise NotFoundException(detail="Invoice not found")
            if invoice.client_id != data.client_id:
                raise ConflictException(detail="Invoice does not belong to this client")

            payment = Payment(
                client_id=data.client_id,
                invoice_id=data.invoice_id,
                payment_number=data.payment_number,
                payment_date=data.payment_date,
                amount=data.amount,
                method=data.method,
                reference=data.reference,
                notes=data.notes,
                tenant_id=tenant_id,
                created_by=created_by,
                status=PaymentStatus.COMPLETED,
            )
            payment = await self.repository.create_payment(payment)

            invoice.paid_amount += data.amount
            invoice.balance_amount = invoice.total_amount - invoice.paid_amount
            if invoice.balance_amount <= 0:
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = datetime.now(timezone.utc)
            elif invoice.paid_amount > 0:
                invoice.status = InvoiceStatus.PARTIAL
            invoice.updated_by = created_by
            await self.repository.update_invoice(invoice)

            return payment

        payment = Payment(
            client_id=data.client_id,
            payment_number=data.payment_number,
            payment_date=data.payment_date,
            amount=data.amount,
            method=data.method,
            reference=data.reference,
            notes=data.notes,
            tenant_id=tenant_id,
            created_by=created_by,
            status=PaymentStatus.COMPLETED,
        )
        return await self.repository.create_payment(payment)

    async def get_payment_by_id(self, payment_id: UUID, tenant_id: UUID) -> Payment:
        payment = await self.repository.get_payment_by_id(payment_id, tenant_id)
        if not payment:
            raise NotFoundException(detail="Payment not found")
        return payment

    async def get_all_payments(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        client_id: Optional[UUID] = None,
        invoice_id: Optional[UUID] = None,
        status: Optional[PaymentStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[Payment], int]:
        return await self.repository.get_all_payments(tenant_id, page, page_size, client_id, invoice_id, status, date_from, date_to)

    async def update_payment(self, payment_id: UUID, tenant_id: UUID, status: PaymentStatus, updated_by: UUID) -> Payment:
        payment = await self.get_payment_by_id(payment_id, tenant_id)
        payment.status = status
        payment.updated_by = updated_by
        return await self.repository.update_payment(payment)

    async def delete_payment(self, payment_id: UUID, tenant_id: UUID) -> None:
        payment = await self.get_payment_by_id(payment_id, tenant_id)
        if payment.invoice_id:
            invoice_result = await self.db.execute(
                select(Invoice).where(Invoice.id == payment.invoice_id)
            )
            invoice = invoice_result.scalar_one_or_none()
            if invoice:
                invoice.paid_amount -= payment.amount
                invoice.balance_amount = invoice.total_amount - invoice.paid_amount
                if invoice.balance_amount <= 0:
                    invoice.status = InvoiceStatus.PAID
                elif invoice.paid_amount > 0:
                    invoice.status = InvoiceStatus.PARTIAL
                else:
                    invoice.status = InvoiceStatus.SENT
                invoice.paid_at = None if invoice.balance_amount > 0 else invoice.paid_at
                await self.repository.update_invoice(invoice)

        await self.repository.delete_payment(payment)

    async def create_expense(self, data: ExpenseCreate, tenant_id: UUID, user_id: UUID) -> Expense:
        if data.client_id:
            client_result = await self.db.execute(
                select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        if data.matter_id:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == data.matter_id, Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        user_result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        if not user_result.scalar_one_or_none():
            raise NotFoundException(detail="User not found")

        expense = Expense(
            client_id=data.client_id,
            matter_id=data.matter_id,
            user_id=user_id,
            expense_number=data.expense_number,
            expense_date=data.expense_date,
            amount=data.amount,
            currency=data.currency,
            category=data.category,
            description=data.description,
            vendor=data.vendor,
            receipt_url=data.receipt_url,
            is_billable=data.is_billable,
            is_reimbursable=data.is_reimbursable,
            tenant_id=tenant_id,
            created_by=user_id,
            status=ExpenseStatus.DRAFT,
        )
        return await self.repository.create_expense(expense)

    async def get_expense_by_id(self, expense_id: UUID, tenant_id: UUID) -> Expense:
        expense = await self.repository.get_expense_by_id(expense_id, tenant_id)
        if not expense:
            raise NotFoundException(detail="Expense not found")
        return expense

    async def get_all_expenses(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        client_id: Optional[UUID] = None,
        matter_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        status: Optional[ExpenseStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[Expense], int]:
        return await self.repository.get_all_expenses(tenant_id, page, page_size, client_id, matter_id, user_id, status, date_from, date_to)

    async def update_expense(self, expense_id: UUID, tenant_id: UUID, data: ExpenseCreate, updated_by: UUID) -> Expense:
        expense = await self.get_expense_by_id(expense_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if "client_id" in update_data and update_data["client_id"]:
            client_result = await self.db.execute(
                select(Client).where(Client.id == update_data["client_id"], Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        if "matter_id" in update_data and update_data["matter_id"]:
            matter_result = await self.db.execute(
                select(Matter).where(Matter.id == update_data["matter_id"], Matter.tenant_id == tenant_id)
            )
            if not matter_result.scalar_one_or_none():
                raise NotFoundException(detail="Matter not found")

        for field, value in update_data.items():
            setattr(expense, field, value)
        expense.updated_by = updated_by
        return await self.repository.update_expense(expense)

    async def approve_expense(self, expense_id: UUID, tenant_id: UUID, approved_by: UUID) -> Expense:
        expense = await self.get_expense_by_id(expense_id, tenant_id)
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = approved_by
        expense.approved_at = datetime.now(timezone.utc)
        expense.updated_by = approved_by
        return await self.repository.update_expense(expense)

    async def reimburse_expense(self, expense_id: UUID, tenant_id: UUID, reimbursed_by: UUID) -> Expense:
        expense = await self.get_expense_by_id(expense_id, tenant_id)
        expense.status = ExpenseStatus.REIMBURSED
        expense.reimbursed_at = datetime.now(timezone.utc)
        expense.updated_by = reimbursed_by
        return await self.repository.update_expense(expense)

    async def delete_expense(self, expense_id: UUID, tenant_id: UUID) -> None:
        expense = await self.get_expense_by_id(expense_id, tenant_id)
        await self.repository.delete_expense(expense)