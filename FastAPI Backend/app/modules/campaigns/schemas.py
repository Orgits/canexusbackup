from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class CampaignType(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    MIXED = "mixed"


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    campaign_type: CampaignType
    channel: str = Field(..., max_length=50)
    template_id: UUID | None = None
    audience_filter: dict[str, Any] = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    audience_filter: dict[str, Any] | None = None
    scheduled_at: datetime | None = None
    settings: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class CampaignRecipientBase(BaseModel):
    campaign_id: UUID
    client_id: UUID


class CampaignRecipientCreate(CampaignRecipientBase):
    pass


class CampaignRecipientResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    client_id: UUID
    status: str
    communication_id: UUID | None
    sent_at: datetime | None
    delivered_at: datetime | None
    opened_at: datetime | None
    clicked_at: datetime | None
    replied_at: datetime | None
    bounced_at: datetime | None
    unsubscribed_at: datetime | None
    error_message: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    campaign_type: CampaignType
    status: CampaignStatus
    channel: str
    template_id: UUID | None
    audience_filter: dict[str, Any]
    audience_count: int
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    sent_count: int
    delivered_count: int
    failed_count: int
    opened_count: int
    clicked_count: int
    replied_count: int
    bounced_count: int
    unsubscribed_count: int
    total_cost: float | None
    cost_per_message: float | None
    settings: dict[str, Any]
    metadata: dict[str, Any]
    created_by_id: UUID | None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignDetailResponse(CampaignResponse):
    recipients: list[CampaignRecipientResponse] = []


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CampaignStatsResponse(BaseModel):
    total_campaigns: int
    draft_campaigns: int
    scheduled_campaigns: int
    sent_campaigns: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_replied: int
    total_bounced: int
    total_unsubscribed: int