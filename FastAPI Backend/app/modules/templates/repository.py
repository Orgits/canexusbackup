from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.templates.models import Template, TemplateStatus


class TemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, template: Template) -> Template:
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_by_id(self, template_id: UUID, tenant_id: UUID) -> Template | None:
        result = await self.db.execute(
            select(Template)
            .where(Template.id == template_id, Template.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, tenant_id: UUID) -> Template | None:
        result = await self.db.execute(
            select(Template).where(Template.name == name, Template.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: TemplateStatus | None = None,
        category: str | None = None,
        channel: str | None = None,
        is_default: bool | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Template], int]:
        query = select(Template).where(Template.tenant_id == tenant_id)
        count_query = select(func.count(Template.id)).where(Template.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Template.name.ilike(f"%{search}%"),
                Template.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if status:
            query = query.where(Template.status == status)
            count_query = count_query.where(Template.status == status)

        if channel:
            query = query.where(Template.channel == channel)
            count_query = count_query.where(Template.channel == channel)

        if is_default is not None:
            query = query.where(Template.is_default == is_default)
            count_query = count_query.where(Template.is_default == is_default)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Template, sort_by):
            sort_column = getattr(Template, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Template.updated_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, template: Template) -> Template:
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete(self, template: Template) -> None:
        await self.db.delete(template)
        await self.db.flush()