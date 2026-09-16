from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.campaigns.models import Campaign, CampaignRecipient, CampaignStatus


class CampaignRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, campaign: Campaign) -> Campaign:
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def get_by_id(self, campaign_id: UUID, tenant_id: UUID) -> Campaign | None:
        result = await self.db.execute(
            select(Campaign)
            .options(selectinload(Campaign.template))
            .where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: CampaignStatus | None = None,
        campaign_type: str | None = None,
        channel: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Campaign], int]:
        query = select(Campaign).where(Campaign.tenant_id == tenant_id)
        count_query = select(func.count(Campaign.id)).where(Campaign.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                Campaign.name.ilike(f"%{search}%"),
                Campaign.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if status:
            query = query.where(Campaign.status == status)
            count_query = count_query.where(Campaign.status == status)

        if campaign_type:
            query = query.where(Campaign.campaign_type == campaign_type)
            count_query = count_query.where(Campaign.campaign_type == campaign_type)

        if date_from:
            query = query.where(Campaign.scheduled_at >= date_from)
            count_query = count_query.where(Campaign.scheduled_at >= date_from)

        if date_to:
            query = query.where(Campaign.scheduled_at <= date_to)
            count_query = count_query.where(Campaign.scheduled_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(Campaign, sort_by):
            sort_column = getattr(Campaign, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(Campaign.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_recipients(
        self,
        campaign_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
    ) -> tuple[list[CampaignRecipient], int]:
        query = select(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.tenant_id == tenant_id,
        )
        count_query = select(func.count(CampaignRecipient.id)).where(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.tenant_id == tenant_id,
        )

        if status:
            query = query.where(CampaignRecipient.status == status)
            count_query = count_query.where(CampaignRecipient.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(CampaignRecipient.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, campaign: Campaign) -> Campaign:
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def delete(self, campaign: Campaign) -> None:
        await self.db.delete(campaign)
        await self.db.flush()