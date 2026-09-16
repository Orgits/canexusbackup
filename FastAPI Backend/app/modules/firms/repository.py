from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.firms.models import Firm


class FirmRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, firm: Firm) -> Firm:
        self.db.add(firm)
        await self.db.flush()
        await self.db.refresh(firm)
        return firm

    async def get_by_id(self, firm_id: UUID) -> Firm | None:
        result = await self.db.execute(select(Firm).where(Firm.id == firm_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Firm | None:
        result = await self.db.execute(select(Firm).where(Firm.name == name))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Firm], int]:
        query = select(Firm)
        count_query = select(func.count(Firm.id))

        if search:
            query = query.where(Firm.name.ilike(f"%{search}%"))
            count_query = count_query.where(Firm.name.ilike(f"%{search}%"))

        if is_active is not None:
            query = query.where(Firm.is_active == is_active)
            count_query = count_query.where(Firm.is_active == is_active)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Firm.created_at.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, firm: Firm) -> Firm:
        await self.db.flush()
        await self.db.refresh(firm)
        return firm

    async def delete(self, firm: Firm) -> None:
        await self.db.delete(firm)
        await self.db.flush()
