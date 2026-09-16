from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.campaigns.schemas import (
    CampaignCreate,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignRecipientResponse,
    CampaignResponse,
    CampaignStatsResponse,
    CampaignUpdate,
)
from app.modules.campaigns.service import CampaignService
from app.modules.users.models import User

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_CREATE)),
):
    service = CampaignService(db)
    campaign = await service.create(data, tenant_context.tenant_id, current_user.id)
    return CampaignResponse.model_validate(campaign)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = None,
    status: str = None,
    campaign_type: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    sort_by: str = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_READ)),
):
    service = CampaignService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, status, campaign_type, date_from, date_to, sort_by, sort_order
    )
    return CampaignListResponse(
        items=[CampaignResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/stats", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_READ)),
):
    service = CampaignService(db)
    stats = await service.get_stats(tenant_context.tenant_id)
    return CampaignStatsResponse(**stats)


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_READ)),
):
    service = CampaignService(db)
    campaign = await service.get_by_id(campaign_id, tenant_context.tenant_id)
    return CampaignDetailResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_UPDATE)),
):
    service = CampaignService(db)
    campaign = await service.update(campaign_id, tenant_context.tenant_id, data, current_user.id)
    return CampaignResponse.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_DELETE)),
):
    service = CampaignService(db)
    await service.delete(campaign_id, tenant_context.tenant_id)


@router.post("/{campaign_id}/recipients", status_code=status.HTTP_201_CREATED)
async def add_campaign_recipients(
    campaign_id: UUID,
    client_ids: list[UUID],
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_UPDATE)),
):
    service = CampaignService(db)
    added = await service.add_recipients(campaign_id, tenant_context.tenant_id, client_ids)
    return {"added": added}


@router.delete("/{campaign_id}/recipients", status_code=status.HTTP_200_OK)
async def remove_campaign_recipients(
    campaign_id: UUID,
    client_ids: list[UUID],
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_UPDATE)),
):
    service = CampaignService(db)
    removed = await service.remove_recipients(campaign_id, tenant_context.tenant_id, client_ids)
    return {"removed": removed}


@router.post("/{campaign_id}/send", response_model=CampaignResponse)
async def send_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_SEND)),
):
    service = CampaignService(db)
    campaign = await service.send_campaign(campaign_id, tenant_context.tenant_id, current_user.id)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/schedule", response_model=CampaignResponse)
async def schedule_campaign(
    campaign_id: UUID,
    scheduled_at: datetime,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_UPDATE)),
):
    service = CampaignService(db)
    campaign = await service.schedule_campaign(campaign_id, tenant_context.tenant_id, scheduled_at)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/cancel", response_model=CampaignResponse)
async def cancel_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_UPDATE)),
):
    service = CampaignService(db)
    campaign = await service.cancel_campaign(campaign_id, tenant_context.tenant_id)
    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}/recipients", response_model=list[CampaignRecipientResponse])
async def list_campaign_recipients(
    campaign_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.CAMPAIGNS_READ)),
):
    service = CampaignService(db)
    items, total = await service.repository.get_recipients(campaign_id, tenant_context.tenant_id, page, page_size, status)
    return [CampaignRecipientResponse.model_validate(item) for item in items]