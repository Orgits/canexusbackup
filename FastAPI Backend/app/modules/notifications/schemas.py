from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationTemplateBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = None
    trigger: str = Field(..., max_length=50)
    channels: list[str] = []
    subject_template: str
    body_template: str
    default_priority: str = Field(default="normal", max_length=20)
    is_active: bool = True
    is_system: bool = False
    metadata: dict[str, Any] = {}


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    channels: list[str] | None = None
    subject_template: str | None = None
    body_template: str | None = None
    default_priority: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class NotificationTemplateResponse(NotificationTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class NotificationBase(BaseModel):
    recipient_id: UUID
    trigger: str = Field(..., max_length=50)
    template_id: UUID | None = None
    title: str = Field(..., max_length=500)
    message: str
    priority: str = Field(default="normal", max_length=20)
    entity_type: str | None = Field(None, max_length=50)
    entity_id: UUID | None = None
    actor_id: UUID | None = None
    channels: list[str] = []
    metadata: dict[str, Any] = {}


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    status: str | None = None
    read_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class NotificationResponse(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    channel_status: dict[str, str] = {}
    read_at: datetime | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    recipient: Optional["UserResponse"] = None
    template: Optional["NotificationTemplateResponse"] = None
    deliveries: list["NotificationDeliveryResponse"] = []


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class NotificationDeliveryBase(BaseModel):
    channel: str = Field(..., max_length=20)
    recipient_address: str | None = Field(None, max_length=500)
    subject: str | None = Field(None, max_length=500)
    content: str
    status: str = Field(default="pending", max_length=20)
    provider_response: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class NotificationDeliveryCreate(NotificationDeliveryBase):
    notification_id: UUID


class NotificationDeliveryUpdate(BaseModel):
    status: str | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    provider_response: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class NotificationDeliveryResponse(NotificationDeliveryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_id: UUID
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class NotificationPreferenceBase(BaseModel):
    trigger: str = Field(..., max_length=50)
    channel: str = Field(..., max_length=20)
    is_enabled: bool = True
    metadata: dict[str, Any] = {}


class NotificationPreferenceCreate(NotificationPreferenceBase):
    pass


class NotificationPreferenceUpdate(BaseModel):
    is_enabled: bool | None = None
    metadata: dict[str, Any] | None = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class NotificationPreferenceListResponse(BaseModel):
    items: list[NotificationPreferenceResponse]
    total: int
    page: int
    page_size: int


class SendNotificationRequest(BaseModel):
    recipient_ids: list[UUID]
    trigger: str = Field(..., max_length=50)
    title: str = Field(..., max_length=500)
    message: str
    priority: str = Field(default="normal", max_length=20)
    entity_type: str | None = Field(None, max_length=50)
    entity_id: UUID | None = None
    channels: list[str] = ["in_app"]
    template_code: str | None = None
    template_variables: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class NotificationStatsResponse(BaseModel):
    total: int
    unread: int
    read: int
    pending: int
    failed: int
    by_trigger: dict[str, int] = {}
    by_priority: dict[str, int] = {}


from app.modules.users.schemas import UserResponse
