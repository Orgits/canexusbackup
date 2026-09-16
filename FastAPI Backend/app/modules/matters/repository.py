from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.matters.models import Matter, MatterPriority, MatterStatus, MatterType


class MatterRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, matter: Matter) -> Matter:
        self.db.add(matter)
        await self.db.flush()
        await self.db.refresh(matter)
        return matter

    async def get_by_id(self, matter_id: UUID, tenant_id: UUID) -> Matter | None:
        result = await self.db.execute(
            select(Matter)
            .options(
                selectinload(Matter.client),
                selectinload(Matter.service),
                selectinload(Matter.compliance_cycle),
                selectinload(Matter.responsible_user),
                selectinload(Matter.responsible_team),
            )
            .where(Matter.id == matter_id, Matter.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, matter_number: str, tenant_id: UUID) -> Matter | None:
        result = await self.db.execute(
            select(Matter).where(Matter.matter_number == matter_number, Matter.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        matter_type: MatterType | None = None,
        status: MatterStatus | None = None,
        priority: MatterPriority | None = None,
        responsible_user_id: UUID | None = None,
        responsible_team_id: UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        tags: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Matter], int]:
        query = (
            select(Matter)
            .options(
                selectinload(Matter.client),
                selectinload(Matter.responsible_user),
                selectinload(Matter.responsible_team),
            )
            .where(Matter.tenant_id == tenant_id)
        )
        count_query = select(func.count(Matter.id)).where(Matter.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Matter.name.ilike(f"%{search}%"),
                Matter.matter_number.ilike(f"%{search}%"),
                Matter.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(Matter.client_id == client_id)
            count_query = count_query.where(Matter.client_id == client_id)

        if matter_type:
            query = query.where(Matter.matter_type == matter_type)
            count_query = count_query.where(Matter.matter_type == matter_type)

        if status:
            query = query.where(Matter.status == status)
            count_query = count_query.where(Matter.status == status)

        if priority:
            query = query.where(Matter.priority == priority)
            count_query = count_query.where(Matter.priority == priority)

        if responsible_user_id:
            query = query.where(Matter.responsible_user_id == responsible_user_id)
            count_query = count_query.where(Matter.responsible_user_id == responsible_user_id)

        if responsible_team_id:
            query = query.where(Matter.responsible_team_id == responsible_team_id)
            count_query = count_query.where(Matter.responsible_team_id == responsible_team_id)

        if due_date_from:
            query = query.where(Matter.due_date >= due_date_from)
            count_query = count_query.where(Matter.due_date >= due_date_from)

        if due_date_to:
            query = query.where(Matter.due_date <= due_date_to)
            count_query = count_query.where(Matter.due_date <= due_date_to)

        if tags:
            query = query.where(Matter.tags.contains(tags))
            count_query = count_query.where(Matter.tags.contains(tags))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Matter, sort_by):
            sort_column = getattr(Matter, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Matter.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, matter: Matter) -> Matter:
        await self.db.flush()
        await self.db.refresh(matter)
        return matter

    async def delete(self, matter: Matter) -> None:
        await self.db.delete(matter)
        await self.db.flush()
