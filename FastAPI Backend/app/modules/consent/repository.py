from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.consent.models import Consent, ConsentTemplate, ConsentStatus


class ConsentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, consent: Consent) -> Consent:
        self.db.add(consent)
        await self.db.flush()
        await self.db.refresh(consent)
        return consent

    async def get_by_id(self, consent_id: UUID, tenant_id: UUID) -> Consent | None:
        result = await self.db.execute(
            select(Consent)
            .options(selectinload(Consent.client))
            .where(Consent.id == consent_id, Consent.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_client_and_channel(self, client_id: UUID, channel: str, tenant_id: UUID) -> Consent | None:
        result = await self.db.execute(
            select(Consent).where(
                Consent.client_id == client_id,
                Consent.channel == channel,
                Consent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        channel: str | None = None,
        status: ConsentStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Consent], int]:
        query = select(Consent).options(selectinload(Consent.client)).where(Consent.tenant_id == tenant_id)
        count_query = select(func.count(Consent.id)).where(Consent.tenant_id == tenant_id)

        if search:
            search_filter = or_(Consent.source.ilike(f"%{search}%"))
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(Consent.client_id == client_id)
            count_query = count_query.where(Consent.client_id == client_id)

        if channel:
            query = query.where(Consent.channel == channel)
            count_query = count_query.where(Consent.channel == channel)

        if status:
            query = query.where(Consent.status == status)
            count_query = count_query.where(Consent.status == status)

        if date_from:
            query = query.where(Consent.given_at >= date_from)
            count_query = count_query.where(Consent.given_at >= date_from)

        if date_to:
            query = query.where(Consent.given_at <= date_to)
            count_query = count_query.where(Consent.given_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Consent, sort_by):
            sort_column = getattr(Consent, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Consent.given_at.desc().nullslast())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create_template(self, template: ConsentTemplate) -> ConsentTemplate:
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_template_by_id(self, template_id: UUID, tenant_id: UUID) -> ConsentTemplate | None:
        result = await self.db.execute(
            select(ConsentTemplate).where(ConsentTemplate.id == template_id, ConsentTemplate.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_template_by_channel(self, channel: str, tenant_id: UUID) -> ConsentTemplate | None:
        result = await self.db.execute(
            select(ConsentTemplate).where(
                ConsentTemplate.channel == channel,
                ConsentTemplate.tenant_id == tenant_id,
                ConsentTemplate.is_active == True,
            ).order_by(ConsentTemplate.is_default.desc(), ConsentTemplate.version.desc())
        )
        return result.scalar_one_or_none()

    async def get_all_templates(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        channel: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[ConsentTemplate], int]:
        query = select(ConsentTemplate).where(ConsentTemplate.tenant_id == tenant_id)
        count_query = select(func.count(ConsentTemplate.id)).where(ConsentTemplate.tenant_id == tenant_id)

        if channel:
            query = query.where(ConsentTemplate.channel == channel)
            count_query = count_query.where(ConsentTemplate.channel == channel)

        if is_active is not None:
            query = query.where(ConsentTemplate.is_active == is_active)
            count_query = count_query.where(ConsentTemplate.is_active == is_active)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(ConsentTemplate.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, obj) -> Consent | ConsentTemplate:
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj) -> None:
        await self.db.delete(obj)
        await self.db.flush()