from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.modules.notifications.models import (
    Notification,
    NotificationTemplate,
    NotificationDelivery,
    NotificationPreference,
    NotificationTrigger,
    NotificationChannel,
    NotificationStatus,
    NotificationPriority,
)
from app.modules.notifications.schemas import (
    NotificationCreate,
    NotificationUpdate,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    NotificationDeliveryCreate,
    NotificationDeliveryUpdate,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
)


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Notification Template methods
    async def create_template(self, template: NotificationTemplate) -> NotificationTemplate:
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_template_by_id(self, template_id: UUID, tenant_id: UUID) -> Optional[NotificationTemplate]:
        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.id == template_id,
                NotificationTemplate.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_template_by_code(self, code: str, tenant_id: UUID) -> Optional[NotificationTemplate]:
        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.code == code,
                NotificationTemplate.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_templates_by_trigger(self, trigger: NotificationTrigger, tenant_id: UUID) -> List[NotificationTemplate]:
        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.trigger == trigger,
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_all_templates(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        trigger: Optional[NotificationTrigger] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[NotificationTemplate], int]:
        query = select(NotificationTemplate).where(NotificationTemplate.tenant_id == tenant_id)
        count_query = select(func.count(NotificationTemplate.id)).where(NotificationTemplate.tenant_id == tenant_id)

        if trigger:
            query = query.where(NotificationTemplate.trigger == trigger)
            count_query = count_query.where(NotificationTemplate.trigger == trigger)

        if is_active is not None:
            query = query.where(NotificationTemplate.is_active == is_active)
            count_query = count_query.where(NotificationTemplate.is_active == is_active)

        query = query.order_by(NotificationTemplate.created_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        templates = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(templates), total

    async def update_template(self, template: NotificationTemplate) -> NotificationTemplate:
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template: NotificationTemplate) -> None:
        await self.db.delete(template)
        await self.db.flush()

    # Notification methods
    async def create_notification(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def bulk_create_notifications(self, notifications: List[Notification]) -> List[Notification]:
        self.db.add_all(notifications)
        await self.db.flush()
        for n in notifications:
            await self.db.refresh(n)
        return notifications

    async def get_notification_by_id(self, notification_id: UUID, tenant_id: UUID) -> Optional[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
            )
            .options(
                selectinload(Notification.recipient),
                selectinload(Notification.template),
                selectinload(Notification.deliveries),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_notifications(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        recipient_id: Optional[UUID] = None,
        trigger: Optional[NotificationTrigger] = None,
        status: Optional[NotificationStatus] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Notification], int]:
        query = select(Notification).where(Notification.tenant_id == tenant_id)
        count_query = select(func.count(Notification.id)).where(Notification.tenant_id == tenant_id)

        if recipient_id:
            query = query.where(Notification.recipient_id == recipient_id)
            count_query = count_query.where(Notification.recipient_id == recipient_id)

        if trigger:
            query = query.where(Notification.trigger == trigger)
            count_query = count_query.where(Notification.trigger == trigger)

        if status:
            query = query.where(Notification.status == status)
            count_query = count_query.where(Notification.status == status)

        if entity_type:
            query = query.where(Notification.entity_type == entity_type)
            count_query = count_query.where(Notification.entity_type == entity_type)

        if entity_id:
            query = query.where(Notification.entity_id == entity_id)
            count_query = count_query.where(Notification.entity_id == entity_id)

        if start_date:
            query = query.where(Notification.created_at >= start_date)
            count_query = count_query.where(Notification.created_at >= start_date)

        if end_date:
            query = query.where(Notification.created_at <= end_date)
            count_query = count_query.where(Notification.created_at <= end_date)

        if sort_by and hasattr(Notification, sort_by):
            column = getattr(Notification, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(Notification.created_at.desc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(Notification.recipient),
                selectinload(Notification.template),
            )
        )
        notifications = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(notifications), total

    async def get_unread_count(self, recipient_id: UUID, tenant_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
                Notification.status != NotificationStatus.READ,
            )
        )
        return result.scalar() or 0

    async def mark_as_read(self, notification_id: UUID, tenant_id: UUID) -> Notification:
        notification = await self.get_notification_by_id(notification_id, tenant_id)
        if notification:
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(notification)
        return notification

    async def mark_all_as_read(self, recipient_id: UUID, tenant_id: UUID) -> int:
        result = await self.db.execute(
            select(Notification).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
                Notification.status != NotificationStatus.READ,
            )
        )
        notifications = result.scalars().all()
        count = 0
        for n in notifications:
            n.status = NotificationStatus.READ
            n.read_at = datetime.now(timezone.utc)
            count += 1
        await self.db.flush()
        return count

    async def update_notification(self, notification: Notification) -> Notification:
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    # Notification Delivery methods
    async def create_delivery(self, delivery: NotificationDelivery) -> NotificationDelivery:
        self.db.add(delivery)
        await self.db.flush()
        await self.db.refresh(delivery)
        return delivery

    async def get_delivery_by_id(self, delivery_id: UUID, tenant_id: UUID) -> Optional[NotificationDelivery]:
        result = await self.db.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.id == delivery_id,
                NotificationDelivery.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_deliveries_for_notification(self, notification_id: UUID, tenant_id: UUID) -> List[NotificationDelivery]:
        result = await self.db.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification_id,
                NotificationDelivery.tenant_id == tenant_id,
            )
        )
        return list(result.scalars().all())

    async def update_delivery(self, delivery: NotificationDelivery) -> NotificationDelivery:
        await self.db.flush()
        await self.db.refresh(delivery)
        return delivery

    # Notification Preference methods
    async def create_preference(self, preference: NotificationPreference) -> NotificationPreference:
        self.db.add(preference)
        await self.db.flush()
        await self.db.refresh(preference)
        return preference

    async def get_preference(
        self, user_id: UUID, trigger: NotificationTrigger, channel: NotificationChannel, tenant_id: UUID
    ) -> Optional[NotificationPreference]:
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.trigger == trigger,
                NotificationPreference.channel == channel,
                NotificationPreference.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_preferences_for_user(self, user_id: UUID, tenant_id: UUID) -> List[NotificationPreference]:
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.tenant_id == tenant_id,
            )
        )
        return list(result.scalars().all())

    async def upsert_preference(
        self, user_id: UUID, trigger: NotificationTrigger, channel: NotificationChannel,
        tenant_id: UUID, data: NotificationPreferenceCreate, created_by: UUID
    ) -> NotificationPreference:
        existing = await self.get_preference(user_id, trigger, channel, tenant_id)
        if existing:
            existing.is_enabled = data.is_enabled
            existing.metadata = data.metadata
            existing.updated_by = created_by
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            preference = NotificationPreference(
                user_id=user_id,
                trigger=trigger,
                channel=channel,
                **data.model_dump(exclude={"user_id", "trigger", "channel"}),
                tenant_id=tenant_id,
                created_by=created_by,
            )
            return await self.create_preference(preference)

    async def update_preference(self, preference: NotificationPreference) -> NotificationPreference:
        await self.db.flush()
        await self.db.refresh(preference)
        return preference


from datetime import timezone