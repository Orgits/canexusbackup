from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ConflictException
from app.modules.firms.models import Firm
from app.modules.firms.schemas import FirmCreate, FirmUpdate
from app.modules.firms.repository import FirmRepository


class FirmService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = FirmRepository(db)

    async def create(self, data: FirmCreate) -> Firm:
        existing = await self.repository.get_by_name(data.name)
        if existing:
            raise ConflictException(detail="Firm with this name already exists")
        firm = Firm(**data.model_dump())
        return await self.repository.create(firm)

    async def get_by_id(self, firm_id: UUID) -> Firm:
        firm = await self.repository.get_by_id(firm_id)
        if not firm:
            raise NotFoundException(detail="Firm not found")
        return firm

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Firm], int]:
        return await self.repository.get_all(page, page_size, search, is_active)

    async def update(self, firm_id: UUID, data: FirmUpdate) -> Firm:
        firm = await self.get_by_id(firm_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(firm, field, value)
        return await self.repository.update(firm)

    async def delete(self, firm_id: UUID) -> None:
        firm = await self.get_by_id(firm_id)
        await self.repository.delete(firm)

    async def activate(self, firm_id: UUID) -> Firm:
        firm = await self.get_by_id(firm_id)
        firm.is_active = True
        return await self.repository.update(firm)

    async def deactivate(self, firm_id: UUID) -> Firm:
        firm = await self.get_by_id(firm_id)
        firm.is_active = False
        return await self.repository.update(firm)