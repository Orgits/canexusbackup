from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.security.dependencies import get_current_user
from app.core.tenancy import get_tenant_context
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationPreferenceCreate,
    NotificationPreferenceListResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationStatsResponse,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
    NotificationUpdate,
    SendNotificationRequest,
)
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(db: AsyncSession = Depends(get_tenant_db_session)) -> NotificationService:
    return NotificationService(db)


# Template endpoints
@router.post(
    "/templates",
    response_model=NotificationTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification template",
)
async def create_notification_template(
    data: NotificationTemplateCreate,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.create")),
):
    return await notification_service.create_template(data, tenant_context.tenant_id, current_user.id)


@router.post(
    "/templates/initialize",
    response_model=list[NotificationTemplateResponse],
    summary="Initialize system notification templates",
)
async def initialize_notification_templates(
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.create")),
):
    return await notification_service.initialize_system_templates(tenant_context.tenant_id)


@router.get(
    "/templates",
    response_model=list[NotificationTemplateResponse],
    summary="List notification templates",
)
async def list_notification_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    trigger: str | None = None,
    is_active: bool | None = None,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    items, total = await notification_service.list_templates(
        tenant_context.tenant_id, page, page_size, trigger, is_active
    )
    return items


@router.get(
    "/templates/trigger/{trigger}",
    response_model=list[NotificationTemplateResponse],
    summary="Get templates by trigger",
)
async def get_templates_by_trigger(
    trigger: str,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    return await notification_service.get_templates_by_trigger(trigger, tenant_context.tenant_id)


@router.get(
    "/templates/{template_id}",
    response_model=NotificationTemplateResponse,
    summary="Get notification template by ID",
)
async def get_notification_template(
    template_id: UUID,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    return await notification_service.get_template(template_id, tenant_context.tenant_id)


@router.patch(
    "/templates/{template_id}",
    response_model=NotificationTemplateResponse,
    summary="Update notification template",
)
async def update_notification_template(
    template_id: UUID,
    data: NotificationTemplateUpdate,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.update")),
):
    return await notification_service.update_template(template_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification template",
)
async def delete_notification_template(
    template_id: UUID,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.delete")),
):
    await notification_service.delete_template(template_id, tenant_context.tenant_id)


# Notification endpoints
@router.post(
    "/send",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send notification",
)
async def send_notification(
    request: SendNotificationRequest,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.create")),
):
    return await notification_service.send_notification(request, tenant_context.tenant_id, current_user.id)


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    recipient_id: UUID | None = None,
    trigger: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    items, total = await notification_service.get_notifications(
        tenant_context.tenant_id,
        page,
        page_size,
        recipient_id,
        trigger,
        status,
        entity_type,
        entity_id,
        start_date,
        end_date,
        sort_by,
        sort_order,
    )
    return NotificationListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/my",
    response_model=NotificationListResponse,
    summary="Get my notifications",
)
async def get_my_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    items, total = await notification_service.get_notifications(
        tenant_context.tenant_id,
        page,
        page_size,
        current_user.id,
        None,
        status,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    return NotificationListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
    summary="Get notification statistics",
)
async def get_notification_stats(
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    return await notification_service.get_stats(tenant_context.tenant_id, current_user.id)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get notification by ID",
)
async def get_notification(
    notification_id: UUID,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    return await notification_service.get_notification(notification_id, tenant_context.tenant_id)


@router.patch(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Update notification",
)
async def update_notification(
    notification_id: UUID,
    data: NotificationUpdate,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.update")),
):
    return await notification_service.update_notification(notification_id, tenant_context.tenant_id, data, current_user.id)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
)
async def mark_notification_read(
    notification_id: UUID,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.update")),
):
    return await notification_service.mark_as_read(notification_id, tenant_context.tenant_id, current_user.id)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
)
async def mark_all_notifications_read(
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.update")),
):
    await notification_service.mark_all_as_read(tenant_context.tenant_id, current_user.id)


# Preference endpoints
@router.post(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set notification preference",
)
async def set_notification_preference(
    data: NotificationPreferenceCreate,
    trigger: str = Query(..., description="Trigger type"),
    channel: str = Query(..., description="Channel (in_app, email, sms, whatsapp, push)"),
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.update")),
):
    return await notification_service.set_preference(
        current_user.id, trigger, channel, data, tenant_context.tenant_id, current_user.id
    )


@router.get(
    "/preferences",
    response_model=NotificationPreferenceListResponse,
    summary="Get my notification preferences",
)
async def get_my_notification_preferences(
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.read")),
):
    items = await notification_service.get_preferences(current_user.id, tenant_context.tenant_id)
    return NotificationPreferenceListResponse(items=items, total=len(items), page=1, page_size=len(items))


@router.patch(
    "/preferences/{preference_id}",
    response_model=NotificationPreferenceResponse,
    summary="Update notification preference",
)
async def update_notification_preference(
    preference_id: UUID,
    data: NotificationPreferenceUpdate,
    notification_service: NotificationService = Depends(get_notification_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("notifications.update")),
):
    return await notification_service.update_preference(preference_id, tenant_context.tenant_id, data, current_user.id)
