from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.campaigns.models import Campaign, CampaignRecipient, CampaignStatus
from app.modules.campaigns.repository import CampaignRepository
from app.modules.campaigns.schemas import CampaignCreate, CampaignUpdate
from app.modules.templates.models import Template
from app.modules.users.models import User


class CampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = CampaignRepository(db)

    async def create(self, data: CampaignCreate, tenant_id: UUID, created_by: UUID) -> Campaign:
        # Validate template if provided
        if data.template_id:
            template_result = await self.db.execute(
                select(Template).where(Template.id == data.template_id, Template.tenant_id == tenant_id)
            )
            if not template_result.scalar_one_or_none():
                raise NotFoundException(detail="Template not found")

        campaign = Campaign(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by_id=created_by,
            status=CampaignStatus.DRAFT,
        )
        return await self.repository.create(campaign)

    async def get_by_id(self, campaign_id: UUID, tenant_id: UUID) -> Campaign:
        campaign = await self.repository.get_by_id(campaign_id, tenant_id)
        if not campaign:
            raise NotFoundException(detail="Campaign not found")
        return campaign

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
        campaign_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Campaign], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, status, campaign_type, date_from, date_to, sort_by, sort_order
        )

    async def update(self, campaign_id: UUID, tenant_id: UUID, data: CampaignUpdate, updated_by: UUID) -> Campaign:
        campaign = await self.get_by_id(campaign_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(campaign, field, value)

        campaign.updated_at = datetime.now()
        return await self.repository.update(campaign)

    async def delete(self, campaign_id: UUID, tenant_id: UUID) -> None:
        campaign = await self.get_by_id(campaign_id, tenant_id)
        await self.repository.delete(campaign)

    async def add_recipients(self, campaign_id: UUID, tenant_id: UUID, client_ids: list[UUID]) -> int:
        campaign = await self.get_by_id(campaign_id, tenant_id)
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise ValueError("Can only add recipients to draft or scheduled campaigns")

        added = 0
        for client_id in client_ids:
            # Check if already exists
            existing = await self.db.execute(
                select(CampaignRecipient).where(
                    CampaignRecipient.campaign_id == campaign_id,
                    CampaignRecipient.client_id == client_id,
                    CampaignRecipient.tenant_id == tenant_id,
                )
            )
            if not existing.scalar_one_or_none():
                recipient = CampaignRecipient(
                    campaign_id=campaign_id,
                    client_id=client_id,
                    tenant_id=tenant_id,
                    status="pending",
                )
                self.db.add(recipient)
                added += 1

        await self.db.flush()
        campaign.audience_count = len(client_ids)
        await self.db.flush()
        return added

    async def remove_recipients(self, campaign_id: UUID, tenant_id: UUID, client_ids: list[UUID]) -> int:
        campaign = await self.get_by_id(campaign_id, tenant_id)
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise ValueError("Can only remove recipients from draft or scheduled campaigns")

        result = await self.db.execute(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.client_id.in_(client_ids),
                CampaignRecipient.tenant_id == tenant_id,
            )
        )
        recipients = result.scalars().all()
        for recipient in recipients:
            await self.db.delete(recipient)

        await self.db.flush()
        campaign.audience_count = max(0, campaign.audience_count - len(recipients))
        await self.db.flush()
        return len(recipients)

    async def send_campaign(self, campaign_id: UUID, tenant_id: UUID, sent_by: UUID) -> Campaign:
        campaign = await self.get_by_id(campaign_id, tenant_id)

        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise ValueError("Campaign must be in draft or scheduled status to send")

        campaign.status = CampaignStatus.SENDING
        campaign.started_at = datetime.now()
        await self.db.flush()

        # TODO: Actually send messages via channel providers
        # This would be handled by a background worker

        campaign.status = CampaignStatus.SENT
        campaign.sent_at = datetime.now()
        campaign.sent_count = campaign.audience_count
        await self.db.flush()

        return campaign

    async def schedule_campaign(self, campaign_id: UUID, tenant_id: UUID, scheduled_at: datetime) -> Campaign:
        campaign = await self.get_by_id(campaign_id, tenant_id)

        if campaign.status != CampaignStatus.DRAFT:
            raise ValueError("Only draft campaigns can be scheduled")

        campaign.status = CampaignStatus.SCHEDULED
        campaign.scheduled_at = scheduled_at
        await self.db.flush()

        return campaign

    async def cancel_campaign(self, campaign_id: UUID, tenant_id: UUID) -> Campaign:
        campaign = await self.get_by_id(campaign_id, tenant_id)

        if campaign.status in [CampaignStatus.SENT, CampaignStatus.COMPLETED]:
            raise ValueError("Cannot cancel sent or completed campaign")

        campaign.status = CampaignStatus.CANCELLED
        await self.db.flush()

        return campaign

    async def get_stats(self, tenant_id: UUID) -> dict:
        from app.modules.campaigns.models import CampaignStatus

        result = await self.db.execute(
            select(
                func.count(Campaign.id).label("total"),
                func.count(Campaign.id).filter(Campaign.status == CampaignStatus.DRAFT).label("draft"),
                func.count(Campaign.id).filter(Campaign.status == CampaignStatus.SCHEDULED).label("scheduled"),
                func.count(Campaign.id).filter(Campaign.status == CampaignStatus.SENT).label("sent"),
                func.sum(Campaign.sent_count).label("total_sent"),
                func.sum(Campaign.delivered_count).label("total_delivered"),
                func.sum(Campaign.opened_count).label("total_opened"),
                func.sum(Campaign.clicked_count).label("total_clicked"),
                func.sum(Campaign.replied_count).label("total_replied"),
                func.sum(Campaign.bounced_count).label("total_bounced"),
                func.sum(Campaign.unsubscribed_count).label("total_unsubscribed"),
            ).where(Campaign.tenant_id == tenant_id)
        )
        stats = result.first()
        return {
            "total_campaigns": stats.total,
            "draft_campaigns": stats.draft,
            "scheduled_campaigns": stats.scheduled,
            "sent_campaigns": stats.sent,
            "total_sent": stats.total_sent or 0,
            "total_delivered": stats.total_delivered or 0,
            "total_opened": stats.total_opened or 0,
            "total_clicked": stats.total_clicked or 0,
            "total_replied": stats.total_replied or 0,
            "total_bounced": stats.total_bounced or 0,
            "total_unsubscribed": stats.total_unsubscribed or 0,
        }