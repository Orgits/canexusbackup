from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.compliance.models import ComplianceType, ComplianceCycle, ComplianceApplicability, ComplianceStatus, ComplianceFrequency


class ComplianceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_type(self, compliance_type: ComplianceType) -> ComplianceType:
        self.db.add(compliance_type)
        await self.db.flush()
        await self.db.refresh(compliance_type)
        return compliance_type

    async def get_type_by_id(self, type_id: UUID, tenant_id: UUID) -> Optional[ComplianceType]:
        result = await self.db.execute(
            select(ComplianceType).where(ComplianceType.id == type_id, ComplianceType.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_type_by_code(self, code: str, tenant_id: UUID) -> Optional[ComplianceType]:
        result = await self.db.execute(
            select(ComplianceType).where(ComplianceType.code == code, ComplianceType.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all_types(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[ComplianceType], int]:
        query = select(ComplianceType).where(ComplianceType.tenant_id == tenant_id)
        count_query = select(func.count(ComplianceType.id)).where(ComplianceType.tenant_id == tenant_id)

        if search:
            query = query.where(
                or_(
                    ComplianceType.code.ilike(f"%{search}%"),
                    ComplianceType.name.ilike(f"%{search}%"),
                    ComplianceType.description.ilike(f"%{search}%"),
                )
            )
            count_query = count_query.where(
                or_(
                    ComplianceType.code.ilike(f"%{search}%"),
                    ComplianceType.name.ilike(f"%{search}%"),
                    ComplianceType.description.ilike(f"%{search}%"),
                )
            )

        if category:
            query = query.where(ComplianceType.category == category)
            count_query = count_query.where(ComplianceType.category == category)

        if is_active is not None:
            query = query.where(ComplianceType.is_active == is_active)
            count_query = count_query.where(ComplianceType.is_active == is_active)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(ComplianceType.created_at.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update_type(self, compliance_type: ComplianceType) -> ComplianceType:
        await self.db.flush()
        await self.db.refresh(compliance_type)
        return compliance_type

    async def delete_type(self, compliance_type: ComplianceType) -> None:
        await self.db.delete(compliance_type)
        await self.db.flush()

    async def create_cycle(self, cycle: ComplianceCycle) -> ComplianceCycle:
        self.db.add(cycle)
        await self.db.flush()
        await self.db.refresh(cycle)
        return cycle

    async def get_cycle_by_id(self, cycle_id: UUID, tenant_id: UUID) -> Optional[ComplianceCycle]:
        result = await self.db.execute(
            select(ComplianceCycle)
            .options(
                selectinload(ComplianceCycle.client),
                selectinload(ComplianceCycle.compliance_type),
                selectinload(ComplianceCycle.matter),
                selectinload(ComplianceCycle.assigned_user),
                selectinload(ComplianceCycle.assigned_team),
            )
            .where(ComplianceCycle.id == cycle_id, ComplianceCycle.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all_cycles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        compliance_type_id: Optional[UUID] = None,
        status: Optional[ComplianceStatus] = None,
        matter_id: Optional[UUID] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        assigned_user_id: Optional[UUID] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[ComplianceCycle], int]:
        from datetime import datetime
        query = (
            select(ComplianceCycle)
            .options(
                selectinload(ComplianceCycle.client),
                selectinload(ComplianceCycle.compliance_type),
                selectinload(ComplianceCycle.matter),
                selectinload(ComplianceCycle.assigned_user),
                selectinload(ComplianceCycle.assigned_team),
            )
            .where(ComplianceCycle.tenant_id == tenant_id)
        )
        count_query = select(func.count(ComplianceCycle.id)).where(ComplianceCycle.tenant_id == tenant_id)

        if search:
            query = query.join(ComplianceCycle.client).where(
                or_(
                    ComplianceCycle.client.has(name=search),
                )
            )
            # Simplified search - would need proper join for production
            count_query = count_query.join(ComplianceCycle.client).where(
                or_(
                    ComplianceCycle.client.has(name=search),
                )
            )

        if client_id:
            query = query.where(ComplianceCycle.client_id == client_id)
            count_query = count_query.where(ComplianceCycle.client_id == client_id)

        if compliance_type_id:
            query = query.where(ComplianceCycle.compliance_type_id == compliance_type_id)
            count_query = count_query.where(ComplianceCycle.compliance_type_id == compliance_type_id)

        if status:
            query = query.where(ComplianceCycle.status == status)
            count_query = count_query.where(ComplianceCycle.status == status)

        if matter_id:
            query = query.where(ComplianceCycle.matter_id == matter_id)
            count_query = count_query.where(ComplianceCycle.matter_id == matter_id)

        if due_date_from:
            query = query.where(ComplianceCycle.due_date >= due_date_from)
            count_query = count_query.where(ComplianceCycle.due_date >= due_date_from)

        if due_date_to:
            query = query.where(ComplianceCycle.due_date <= due_date_to)
            count_query = count_query.where(ComplianceCycle.due_date <= due_date_to)

        if period_start:
            query = query.where(ComplianceCycle.period_start >= period_start)
            count_query = count_query.where(ComplianceCycle.period_start >= period_start)

        if period_end:
            query = query.where(ComplianceCycle.period_end <= period_end)
            count_query = count_query.where(ComplianceCycle.period_end <= period_end)

        if assigned_user_id:
            query = query.where(ComplianceCycle.assigned_user_id == assigned_user_id)
            count_query = count_query.where(ComplianceCycle.assigned_user_id == assigned_user_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(ComplianceCycle, sort_by):
            sort_column = getattr(ComplianceCycle, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(ComplianceCycle.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update_cycle(self, cycle: ComplianceCycle) -> ComplianceCycle:
        await self.db.flush()
        await self.db.refresh(cycle)
        return cycle

    async def delete_cycle(self, cycle: ComplianceCycle) -> None:
        await self.db.delete(cycle)
        await self.db.flush()

    async def create_applicability(self, applicability: ComplianceApplicability) -> ComplianceApplicability:
        self.db.add(applicability)
        await self.db.flush()
        await self.db.refresh(applicability)
        return applicability

    async def get_applicability(self, client_id: UUID, compliance_type_id: UUID, tenant_id: UUID) -> Optional[ComplianceApplicability]:
        result = await self.db.execute(
            select(ComplianceApplicability)
            .where(
                ComplianceApplicability.client_id == client_id,
                ComplianceApplicability.compliance_type_id == compliance_type_id,
                ComplianceApplicability.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_applicability_by_id(self, app_id: UUID, tenant_id: UUID) -> Optional[ComplianceApplicability]:
        result = await self.db.execute(
            select(ComplianceApplicability).where(ComplianceApplicability.id == app_id, ComplianceApplicability.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all_applicability(
        self,
        tenant_id: UUID,
        client_id: Optional[UUID] = None,
        compliance_type_id: Optional[UUID] = None,
    ) -> List[ComplianceApplicability]:
        query = select(ComplianceApplicability).where(ComplianceApplicability.tenant_id == tenant_id)
        if client_id:
            query = query.where(ComplianceApplicability.client_id == client_id)
        if compliance_type_id:
            query = query.where(ComplianceApplicability.compliance_type_id == compliance_type_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_applicability(self, applicability: ComplianceApplicability) -> ComplianceApplicability:
        await self.db.flush()
        await self.db.refresh(applicability)
        return applicability

    async def delete_applicability(self, applicability: ComplianceApplicability) -> None:
        await self.db.delete(applicability)
        await self.db.flush()