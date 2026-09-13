from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class NotificationTemplateBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    trigger: str = Field(..., max_length=50)
    channels: List[str] = []
    subject_template: str
    body_template: str
    default_priority: str = Field(default="normal", max_length=20)
    is_active: bool = True
    is_system: bool = False
    metadata: Dict[str, Any] = {}


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    channels: Optional[List[str]] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    default_priority: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class NotificationBase(BaseModel):
    recipient_id: UUID
    trigger: str = Field(..., max_length=50)
    template_id: Optional[UUID] = None
    title: str = Field(..., max_length=500)
    message: str
    priority: str = Field(default="normal", max_length=20)
    entity_type: Optional[str] = Field(None, max_length=50)
    entity_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    channels: List[str] = []
    metadata: Dict[str, Any] = {}


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    status: Optional[str] = None
    read_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationResponse(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    channel_status: Dict[str, str] = {}
    read_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    recipient: Optional["UserResponse"] = None
    template: Optional["NotificationTemplateResponse"] = None
    deliveries: List["NotificationDeliveryResponse"] = []


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int


class NotificationDeliveryBase(BaseModel):
    channel: str = Field(..., max_length=20)
    recipient_address: Optional[str] = Field(None, max_length=500)
    subject: Optional[str] = Field(None, max_length=500)
    content: str
    status: str = Field(default="pending", max_length=20)
    provider_response: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class NotificationDeliveryCreate(NotificationDeliveryBase):
    notification_id: UUID


class NotificationDeliveryUpdate(BaseModel):
    status: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationDeliveryResponse(NotificationDeliveryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_id: UUID
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class NotificationPreferenceBase(BaseModel):
    trigger: str = Field(..., max_length=50)
    channel: str = Field(..., max_length=20)
    is_enabled: bool = True
    metadata: Dict[str, Any] = {}


class NotificationPreferenceCreate(NotificationPreferenceBase):
    pass


class NotificationPreferenceUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class NotificationPreferenceListResponse(BaseModel):
    items: List[NotificationPreferenceResponse]
    total: int
    page: int
    page_size: int


class SendNotificationRequest(BaseModel):
    recipient_ids: List[UUID]
    trigger: str = Field(..., max_length=50)
    title: str = Field(..., max_length=500)
    message: str
    priority: str = Field(default="normal", max_length=20)
    entity_type: Optional[str] = Field(None, max_length=50)
    entity_id: Optional[UUID] = None
    channels: List[str] = ["in_app"]
    template_code: Optional[str] = None
    template_variables: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class NotificationStatsResponse(BaseModel):
    total: int
    unread: int
    read: int
    pending: int
    failed: int
    by_trigger: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}


from app.modules.users.schemas import UserResponse