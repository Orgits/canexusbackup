from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.suppression.models import Suppression, SuppressionReason, SuppressionChannel


class SuppressionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, suppression: Suppression) -> Suppression:
        self.db.add(suppression)
        await self.db.flush()
        await self.db.refresh(suppression)
        return suppression

    async def get_by_id(self, suppression_id: UUID, tenant_id: UUID) -> Suppression | None:
        result = await self.db.execute(
            select(Suppression).where(Suppression.id == suppression_id, Suppression.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def check_suppression(self, value: str, channel: str, tenant_id: UUID) -> Suppression | None:
        result = await self.db.execute(
            select(Suppression).where(
                Suppression.tenant_id == tenant_id,
                Suppression.value == value,
                Suppression.channel == channel,
                Suppression.is_global == True,
            ).where(
                (Suppression.expires_at.is_(None)) | (Suppression.expires_at > datetime.utcnow())
            )
        )
        return result.scalar_one_or_none()

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
        query = select(Suppression).where(Suppression.tenant_id == tenant_id)
        count_query = select(func.count(Suppression.id)).where(Suppression.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Suppression.value.ilike(f"%{search}%"),
                Suppression.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if channel:
            query = query.where(Suppression.channel == channel)
            count_query = count_query.where(Suppression.channel == channel)

        if reason:
            query = query.where(Suppression.reason == reason)
            count_query = count_query.where(Suppression.reason == reason)

        if is_global is not None:
            query = query.where(Suppression.is_global == is_global)
            count_query = count_query.where(Suppression.is_global == is_global)

        if date_from:
            query = query.where(Suppression.created_at >= date_from)
            count_query = count_query.where(Suppression.created_at >= date_from)

        if date_to:
            query = query.where(Suppression.created_at <= date_to)
            count_query = count_query.where(Suppression.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Suppression, sort_by):
            sort_column = getattr(Suppression, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Suppression.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def bulk_check(self, values: list[str], channel: str, tenant_id: UUID) -> dict[str, bool]:
        result = await self.db.execute(
            select(Suppression.value).where(
                Suppression.tenant_id == tenant_id,
                Suppression.value.in_(values),
                Suppression.channel == channel,
                Suppression.is_global == True,
            ).where(
                (Suppression.expires_at.is_(None)) | (Suppression.expires_at > datetime.utcnow())
            )
        )
        suppressed_values = {row[0] for row in result.fetchall()}
        return {value: value in suppressed_values for value in values}

    async def update(self, suppression: Suppression) -> Suppression:
        await self.db.flush()
        await self.db.refresh(suppression)
        return suppression

    async def delete(self, suppression: Suppression) -> None:
        await self.db.delete(suppression)
        await self.db.flush()