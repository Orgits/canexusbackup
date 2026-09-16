from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.clients.models import Client
from app.modules.suppression.models import Suppression, SuppressionReason, SuppressionChannel
from app.modules.suppression.repository import SuppressionRepository
from app.modules.suppression.schemas import SuppressionCreate, SuppressionUpdate, SuppressionCheckRequest
from app.modules.users.models import User


class SuppressionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = SuppressionRepository(db)

    async def create(self, data: SuppressionCreate, tenant_id: UUID, created_by: UUID) -> Suppression:
        if data.client_id:
            client_result = await self.db.execute(
                select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
            )
            if not client_result.scalar_one_or_none():
                raise NotFoundException(detail="Client not found")

        suppression = Suppression(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create(suppression)

    async def get_by_id(self, suppression_id: UUID, tenant_id: UUID) -> Suppression:
        suppression = await self.repository.get_by_id(suppression_id, tenant_id)
        if not suppression:
            raise NotFoundException(detail="Suppression not found")
        return suppression

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        channel: str | None = None,
        reason: str | None = None,
        is_global: bool | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Suppression], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, channel, reason, is_global, date_from, date_to, sort_by, sort_order
        )

    async def update(self, suppression_id: UUID, tenant_id: UUID, data: SuppressionUpdate, updated_by: UUID) -> Suppression:
        suppression = await self.get_by_id(suppression_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(suppression, field, value)

        return await self.repository.update(suppression)

    async def delete(self, suppression_id: UUID, tenant_id: UUID) -> None:
        suppression = await self.get_by_id(suppression_id, tenant_id)
        await self.repository.delete(suppression)

    async def check_suppression(self, value: str, channel: str, tenant_id: UUID) -> dict:
        suppression = await self.repository.check_suppression(value, channel, tenant_id)
        if suppression:
            return {
                "is_suppressed": True,
                "reason": suppression.reason.value,
                "matched_rule": {
                    "id": str(suppression.id),
                    "value": suppression.value,
                    "channel": suppression.channel.value,
                    "reason": suppression.reason.value,
                }
            }
        return {"is_suppressed": False, "reason": None, "matched_rule": None}

    async def bulk_check(self, request: SuppressionCheckRequest, tenant_id: UUID) -> dict:
        results = await self.repository.bulk_check(request.values, request.channel, tenant_id)
        return results