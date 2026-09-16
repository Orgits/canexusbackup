from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.tds.models import (
    TDSChallan,
    TDSComplianceCycle,
    TDSDeductee,
    TDSFormType,
    TDSQuarter,
    TDSStatus,
)


class TDSRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # TDS Compliance Cycle methods
    async def create_cycle(self, cycle: TDSComplianceCycle) -> TDSComplianceCycle:
        self.db.add(cycle)
        await self.db.flush()
        await self.db.refresh(cycle)
        return cycle

    async def get_cycle_by_id(self, cycle_id: UUID, tenant_id: UUID) -> TDSComplianceCycle | None:
        result = await self.db.execute(
            select(TDSComplianceCycle)
            .where(
                TDSComplianceCycle.id == cycle_id,
                TDSComplianceCycle.tenant_id == tenant_id,
            )
            .options(
                selectinload(TDSComplianceCycle.client),
                selectinload(TDSComplianceCycle.matter),
                selectinload(TDSComplianceCycle.assigned_user),
                selectinload(TDSComplianceCycle.assigned_team),
            )
        )
        return result.scalar_one_or_none()

    async def get_cycle_with_details(self, cycle_id: UUID, tenant_id: UUID) -> TDSComplianceCycle | None:
        result = await self.db.execute(
            select(TDSComplianceCycle)
            .where(
                TDSComplianceCycle.id == cycle_id,
                TDSComplianceCycle.tenant_id == tenant_id,
            )
            .options(
                selectinload(TDSComplianceCycle.client),
                selectinload(TDSComplianceCycle.matter),
                selectinload(TDSComplianceCycle.assigned_user),
                selectinload(TDSComplianceCycle.assigned_team),
                selectinload(TDSComplianceCycle.challans),
                selectinload(TDSComplianceCycle.deductees),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_cycles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        form_type: TDSFormType | None = None,
        financial_year: str | None = None,
        quarter: TDSQuarter | None = None,
        status: TDSStatus | None = None,
        matter_id: UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        assigned_user_id: UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[TDSComplianceCycle], int]:
        query = select(TDSComplianceCycle).where(TDSComplianceCycle.tenant_id == tenant_id)
        count_query = select(func.count(TDSComplianceCycle.id)).where(TDSComplianceCycle.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.join(TDSComplianceCycle.client).where(
                or_(
                    TDSComplianceCycle.form_type.ilike(search_term),
                    TDSComplianceCycle.financial_year.ilike(search_term),
                )
            )
            count_query = count_query.join(TDSComplianceCycle.client).where(
                or_(
                    TDSComplianceCycle.form_type.ilike(search_term),
                    TDSComplianceCycle.financial_year.ilike(search_term),
                )
            )

        if client_id:
            query = query.where(TDSComplianceCycle.client_id == client_id)
            count_query = count_query.where(TDSComplianceCycle.client_id == client_id)

        if form_type:
            query = query.where(TDSComplianceCycle.form_type == form_type)
            count_query = count_query.where(TDSComplianceCycle.form_type == form_type)

        if financial_year:
            query = query.where(TDSComplianceCycle.financial_year == financial_year)
            count_query = count_query.where(TDSComplianceCycle.financial_year == financial_year)

        if quarter:
            query = query.where(TDSComplianceCycle.quarter == quarter)
            count_query = count_query.where(TDSComplianceCycle.quarter == quarter)

        if status:
            query = query.where(TDSComplianceCycle.status == status)
            count_query = count_query.where(TDSComplianceCycle.status == status)

        if matter_id:
            query = query.where(TDSComplianceCycle.matter_id == matter_id)
            count_query = count_query.where(TDSComplianceCycle.matter_id == matter_id)

        if due_date_from:
            query = query.where(TDSComplianceCycle.due_date >= due_date_from)
            count_query = count_query.where(TDSComplianceCycle.due_date >= due_date_from)

        if due_date_to:
            query = query.where(TDSComplianceCycle.due_date <= due_date_to)
            count_query = count_query.where(TDSComplianceCycle.due_date <= due_date_to)

        if assigned_user_id:
            query = query.where(TDSComplianceCycle.assigned_user_id == assigned_user_id)
            count_query = count_query.where(TDSComplianceCycle.assigned_user_id == assigned_user_id)

        if sort_by and hasattr(TDSComplianceCycle, sort_by):
            column = getattr(TDSComplianceCycle, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(TDSComplianceCycle.due_date.asc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(TDSComplianceCycle.client),
                selectinload(TDSComplianceCycle.matter),
                selectinload(TDSComplianceCycle.assigned_user),
                selectinload(TDSComplianceCycle.assigned_team),
            )
        )
        cycles = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(cycles), total

    async def update_cycle(self, cycle: TDSComplianceCycle) -> TDSComplianceCycle:
        await self.db.flush()
        await self.db.refresh(cycle)
        return cycle

    async def delete_cycle(self, cycle: TDSComplianceCycle) -> None:
        await self.db.delete(cycle)
        await self.db.flush()

    # TDS Challan methods
    async def create_challan(self, challan: TDSChallan) -> TDSChallan:
        self.db.add(challan)
        await self.db.flush()
        await self.db.refresh(challan)
        return challan

    async def get_challan_by_id(self, challan_id: UUID, tenant_id: UUID) -> TDSChallan | None:
        result = await self.db.execute(
            select(TDSChallan).where(
                TDSChallan.id == challan_id,
                TDSChallan.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_challans_for_cycle(self, cycle_id: UUID, tenant_id: UUID) -> list[TDSChallan]:
        result = await self.db.execute(
            select(TDSChallan)
            .where(
                TDSChallan.tds_cycle_id == cycle_id,
                TDSChallan.tenant_id == tenant_id,
            )
            .order_by(TDSChallan.deposit_date)
        )
        return list(result.scalars().all())

    async def update_challan(self, challan: TDSChallan) -> TDSChallan:
        await self.db.flush()
        await self.db.refresh(challan)
        return challan

    async def delete_challan(self, challan: TDSChallan) -> None:
        await self.db.delete(challan)
        await self.db.flush()

    # TDS Deductee methods
    async def create_deductee(self, deductee: TDSDeductee) -> TDSDeductee:
        self.db.add(deductee)
        await self.db.flush()
        await self.db.refresh(deductee)
        return deductee

    async def get_deductee_by_id(self, deductee_id: UUID, tenant_id: UUID) -> TDSDeductee | None:
        result = await self.db.execute(
            select(TDSDeductee).where(
                TDSDeductee.id == deductee_id,
                TDSDeductee.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_deductees_for_cycle(
        self, cycle_id: UUID, tenant_id: UUID, page: int = 1, page_size: int = 100
    ) -> tuple[list[TDSDeductee], int]:
        query = select(TDSDeductee).where(
            TDSDeductee.tds_cycle_id == cycle_id,
            TDSDeductee.tenant_id == tenant_id,
        ).order_by(TDSDeductee.deduction_date)
        count_query = select(func.count(TDSDeductee.id)).where(
            TDSDeductee.tds_cycle_id == cycle_id,
            TDSDeductee.tenant_id == tenant_id,
        )

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        deductees = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(deductees), total

    async def bulk_create_deductees(self, deductees: list[TDSDeductee]) -> list[TDSDeductee]:
        self.db.add_all(deductees)
        await self.db.flush()
        for d in deductees:
            await self.db.refresh(d)
        return deductees

    async def update_deductee(self, deductee: TDSDeductee) -> TDSDeductee:
        await self.db.flush()
        await self.db.refresh(deductee)
        return deductee

    async def delete_deductee(self, deductee: TDSDeductee) -> None:
        await self.db.delete(deductee)
        await self.db.flush()

    async def get_summary(self, tenant_id: UUID, financial_year: str | None = None) -> dict:
        query = select(TDSComplianceCycle).where(TDSComplianceCycle.tenant_id == tenant_id)
        if financial_year:
            query = query.where(TDSComplianceCycle.financial_year == financial_year)

        result = await self.db.execute(query)
        cycles = result.scalars().all()

        total = len(cycles)
        pending = sum(1 for c in cycles if c.status == TDSStatus.PENDING)
        in_progress = sum(1 for c in cycles if c.status in [TDSStatus.DATA_COLLECTION, TDSStatus.VALIDATION, TDSStatus.READY_FOR_FILING])
        filed = sum(1 for c in cycles if c.status == TDSStatus.FILED)
        processed = sum(1 for c in cycles if c.status == TDSStatus.PROCESSED)
        overdue = sum(1 for c in cycles if c.status == TDSStatus.DEFAULTER)

        total_tax_deducted = sum(c.total_tax_deducted for c in cycles)
        total_tax_deposited = sum(c.total_tax_deposited for c in cycles)

        # Upcoming deadlines (next 30 days)
        from datetime import timedelta
        upcoming_date = datetime.now(UTC) + timedelta(days=30)
        upcoming = [
            c for c in cycles
            if c.status not in [TDSStatus.FILED, TDSStatus.PROCESSED, TDSStatus.CANCELLED]
            and c.due_date <= upcoming_date
        ]
        upcoming.sort(key=lambda x: x.due_date)

        return {
            "total_cycles": total,
            "pending": pending,
            "in_progress": in_progress,
            "filed": filed,
            "processed": processed,
            "overdue": overdue,
            "total_tax_deducted": total_tax_deducted,
            "total_tax_deposited": total_tax_deposited,
            "upcoming_deadlines": upcoming[:10],
        }


