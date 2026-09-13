from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ValidationException
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
    SendNotificationRequest,
    NotificationStatsResponse,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.users.models import User


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = NotificationRepository(db)

    # Template methods
    async def create_template(
        self, data: NotificationTemplateCreate, tenant_id: UUID, created_by: UUID
    ) -> NotificationTemplate:
        try:
            trigger_enum = NotificationTrigger(data.trigger)
        except ValueError:
            raise ValidationException(detail=f"Invalid trigger: {data.trigger}")

        existing = await self.repository.get_template_by_code(data.code, tenant_id)
        if existing:
            raise ValidationException(detail="Template with this code already exists")

        template = NotificationTemplate(
            **data.model_dump(exclude={"trigger"}),
            trigger=trigger_enum,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create_template(template)

    async def get_template(self, template_id: UUID, tenant_id: UUID) -> NotificationTemplate:
        template = await self.repository.get_template_by_id(template_id, tenant_id)
        if not template:
            raise NotFoundException(detail="Notification template not found")
        return template

    async def get_template_by_code(self, code: str, tenant_id: UUID) -> NotificationTemplate:
        template = await self.repository.get_template_by_code(code, tenant_id)
        if not template:
            raise NotFoundException(detail="Notification template not found")
        return template

    async def get_templates_by_trigger(self, trigger: str, tenant_id: UUID) -> List[NotificationTemplate]:
        try:
            trigger_enum = NotificationTrigger(trigger)
        except ValueError:
            raise ValidationException(detail=f"Invalid trigger: {trigger}")
        return await self.repository.get_templates_by_trigger(trigger_enum, tenant_id)

    async def list_templates(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        trigger: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[NotificationTemplate], int]:
        trigger_enum = None
        if trigger:
            try:
                trigger_enum = NotificationTrigger(trigger)
            except ValueError:
                raise ValidationException(detail=f"Invalid trigger: {trigger}")
        return await self.repository.get_all_templates(tenant_id, page, page_size, trigger_enum, is_active)

    async def update_template(
        self, template_id: UUID, tenant_id: UUID, data: NotificationTemplateUpdate, updated_by: UUID
    ) -> NotificationTemplate:
        template = await self.get_template(template_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if "trigger" in update_data:
            try:
                template.trigger = NotificationTrigger(update_data.pop("trigger"))
            except ValueError:
                raise ValidationException(detail="Invalid trigger")

        if "default_priority" in update_data:
            try:
                template.default_priority = NotificationPriority(update_data.pop("default_priority"))
            except ValueError:
                raise ValidationException(detail="Invalid priority")

        for field, value in update_data.items():
            setattr(template, field, value)
        template.updated_by = updated_by
        return await self.repository.update_template(template)

    async def delete_template(self, template_id: UUID, tenant_id: UUID) -> None:
        template = await self.get_template(template_id, tenant_id)
        if template.is_system:
            raise ValidationException(detail="Cannot delete system template")
        await self.repository.delete_template(template)

    async def initialize_system_templates(self, tenant_id: UUID) -> List[NotificationTemplate]:
        system_templates = [
            {
                "code": "ASSIGNMENT_CREATED",
                "name": "Assignment Created",
                "description": "Notification when a new assignment is created",
                "trigger": NotificationTrigger.ASSIGNMENT,
                "channels": ["in_app", "email"],
                "subject_template": "New Assignment: {{entity_type}} - {{entity_name}}",
                "body_template": "You have been assigned to {{entity_type}} \"{{entity_name}}\". {{#if due_date}}Due date: {{due_date}}{{/if}}",
                "default_priority": NotificationPriority.NORMAL,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "REASSIGNMENT",
                "name": "Reassignment Notification",
                "description": "Notification when an entity is reassigned",
                "trigger": NotificationTrigger.REASSIGNMENT,
                "channels": ["in_app", "email"],
                "subject_template": "Reassigned: {{entity_type}} - {{entity_name}}",
                "body_template": "You have been reassigned to {{entity_type}} \"{{entity_name}}\" (previously assigned to {{previous_assignee}}).",
                "default_priority": NotificationPriority.HIGH,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "DEADLINE_APPROACHING",
                "name": "Deadline Approaching",
                "description": "Notification when a deadline is approaching",
                "trigger": NotificationTrigger.DEADLINE_APPROACHING,
                "channels": ["in_app", "email"],
                "subject_template": "Deadline Approaching: {{entity_type}} - {{entity_name}}",
                "body_template": "The deadline for {{entity_type}} \"{{entity_name}}\" is approaching on {{due_date}}.",
                "default_priority": NotificationPriority.HIGH,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "DEADLINE_OVERDUE",
                "name": "Deadline Overdue",
                "description": "Notification when a deadline is overdue",
                "trigger": NotificationTrigger.DEADLINE_OVERDUE,
                "channels": ["in_app", "email"],
                "subject_template": "OVERDUE: {{entity_type}} - {{entity_name}}",
                "body_template": "The deadline for {{entity_type}} \"{{entity_name}}\" was due on {{due_date}} and is now overdue.",
                "default_priority": NotificationPriority.URGENT,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "REVIEW_REQUEST",
                "name": "Review Request",
                "description": "Notification when a review is requested",
                "trigger": NotificationTrigger.REVIEW_REQUEST,
                "channels": ["in_app", "email"],
                "subject_template": "Review Request: {{entity_type}} - {{entity_name}}",
                "body_template": "You have been requested to review {{entity_type}} \"{{entity_name}}\". {{#if due_date}}Please complete by {{due_date}}.{{/if}}",
                "default_priority": NotificationPriority.HIGH,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "REVIEW_APPROVED",
                "name": "Review Approved",
                "description": "Notification when a review is approved",
                "trigger": NotificationTrigger.REVIEW_APPROVED,
                "channels": ["in_app"],
                "subject_template": "Review Approved: {{entity_type}} - {{entity_name}}",
                "body_template": "Your review of {{entity_type}} \"{{entity_name}}\" has been approved.",
                "default_priority": NotificationPriority.NORMAL,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "REVIEW_REJECTED",
                "name": "Review Rejected",
                "description": "Notification when a review is rejected",
                "trigger": NotificationTrigger.REVIEW_REJECTED,
                "channels": ["in_app", "email"],
                "subject_template": "Review Rejected: {{entity_type}} - {{entity_name}}",
                "body_template": "Your review of {{entity_type}} \"{{entity_name}}\" has been rejected. {{#if comment}}Reason: {{comment}}{{/if}}",
                "default_priority": NotificationPriority.HIGH,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "REVIEW_REWORK",
                "name": "Review Rework Requested",
                "description": "Notification when rework is requested on a review",
                "trigger": NotificationTrigger.REVIEW_REWORK,
                "channels": ["in_app", "email"],
                "subject_template": "Rework Requested: {{entity_type}} - {{entity_name}}",
                "body_template": "Rework has been requested for {{entity_type}} \"{{entity_name}}\". {{#if comment}}Comments: {{comment}}{{/if}}",
                "default_priority": NotificationPriority.HIGH,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "MENTION",
                "name": "Mention Notification",
                "description": "Notification when user is mentioned in a comment",
                "trigger": NotificationTrigger.MENTION,
                "channels": ["in_app"],
                "subject_template": "You were mentioned in {{entity_type}} - {{entity_name}}",
                "body_template": "{{actor_name}} mentioned you in a comment on {{entity_type}} \"{{entity_name}}\": {{comment_preview}}",
                "default_priority": NotificationPriority.NORMAL,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "ESCALATION",
                "name": "Escalation Notification",
                "description": "Notification when an item is escalated",
                "trigger": NotificationTrigger.ESCALATION,
                "channels": ["in_app", "email"],
                "subject_template": "ESCALATED: {{entity_type}} - {{entity_name}}",
                "body_template": "{{entity_type}} \"{{entity_name}}\" has been escalated to you. Reason: {{reason}}",
                "default_priority": NotificationPriority.URGENT,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "COMMENT_ADDED",
                "name": "Comment Added",
                "description": "Notification when a comment is added to an entity you're following",
                "trigger": NotificationTrigger.COMMENT,
                "channels": ["in_app"],
                "subject_template": "New Comment: {{entity_type}} - {{entity_name}}",
                "body_template": "{{actor_name}} commented on {{entity_type}} \"{{entity_name}}\": {{comment_preview}}",
                "default_priority": NotificationPriority.NORMAL,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "STATUS_CHANGE",
                "name": "Status Change",
                "description": "Notification when an entity status changes",
                "trigger": NotificationTrigger.STATUS_CHANGE,
                "channels": ["in_app"],
                "subject_template": "Status Changed: {{entity_type}} - {{entity_name}}",
                "body_template": "{{entity_type}} \"{{entity_name}}\" status changed from {{old_status}} to {{new_status}}.",
                "default_priority": NotificationPriority.NORMAL,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "DOCUMENT_UPLOADED",
                "name": "Document Uploaded",
                "description": "Notification when a document is uploaded to an entity",
                "trigger": NotificationTrigger.DOCUMENT_UPLOADED,
                "channels": ["in_app"],
                "subject_template": "New Document: {{entity_type}} - {{entity_name}}",
                "body_template": "A new document \"{{document_name}}\" has been uploaded to {{entity_type}} \"{{entity_name}}\".",
                "default_priority": NotificationPriority.NORMAL,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "COMPLIANCE_DUE",
                "name": "Compliance Due",
                "description": "Notification when a compliance item is due",
                "trigger": NotificationTrigger.COMPLIANCE_DUE,
                "channels": ["in_app", "email"],
                "subject_template": "Compliance Due: {{compliance_type}} for {{client_name}}",
                "body_template": "{{compliance_type}} compliance for {{client_name}} is due on {{due_date}}.",
                "default_priority": NotificationPriority.HIGH,
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "NOTICE_RECEIVED",
                "name": "Notice Received",
                "description": "Notification when a new notice is received",
                "trigger": NotificationTrigger.NOTICE_RECEIVED,
                "channels": ["in_app", "email"],
                "subject_template": "New Notice: {{notice_type}} from {{authority}}",
                "body_template": "A {{notice_type}} notice ({{reference_number}}) has been received from {{authority}} for {{client_name}}. Response deadline: {{response_deadline}}.",
                "default_priority": NotificationPriority.URGENT,
                "is_system": True,
                "is_active": True,
            },
        ]

        created = []
        for template_data in system_templates:
            existing = await self.repository.get_template_by_code(template_data["code"], tenant_id)
            if not existing:
                template = NotificationTemplate(
                    **template_data,
                    tenant_id=tenant_id,
                )
                created.append(await self.repository.create_template(template))
        return created

    # Notification methods
    async def send_notification(
        self, request: SendNotificationRequest, tenant_id: UUID, actor_id: UUID
    ) -> List[Notification]:
        notifications = []

        for recipient_id in request.recipient_ids:
            # Check preferences
            channels = request.channels
            if request.template_code:
                template = await self.repository.get_template_by_code(request.template_code, tenant_id)
                if template:
                    channels = template.channels
                    # Render template with variables
                    # In a real implementation, use a template engine like Jinja2
                    title = template.subject_template
                    message = template.body_template
                    for key, value in request.template_variables.items():
                        title = title.replace(f"{{{{{key}}}}}", str(value))
                        message = message.replace(f"{{{{{key}}}}}", str(value))
                else:
                    title = request.title
                    message = request.message
            else:
                title = request.title
                message = request.message

            # Filter channels based on user preferences
            filtered_channels = []
            for channel in channels:
                try:
                    channel_enum = NotificationChannel(channel)
                except ValueError:
                    continue

                preference = await self.repository.get_preference(
                    recipient_id,
                    NotificationTrigger(request.trigger) if request.trigger in NotificationTrigger.__members__.values() else NotificationTrigger.CUSTOM,
                    channel_enum,
                    tenant_id,
                )
                if preference is None or preference.is_enabled:
                    filtered_channels.append(channel)

            if not filtered_channels:
                filtered_channels = ["in_app"]

            notification = Notification(
                recipient_id=recipient_id,
                trigger=NotificationTrigger(request.trigger) if request.trigger in NotificationTrigger.__members__.values() else NotificationTrigger.CUSTOM,
                template_id=request.template_id,
                title=title,
                message=message,
                priority=NotificationPriority(request.priority) if request.priority in NotificationPriority.__members__.values() else NotificationPriority.NORMAL,
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                actor_id=actor_id,
                channels=filtered_channels,
                channel_status={ch: NotificationStatus.PENDING.value for ch in filtered_channels},
                metadata=request.metadata,
                tenant_id=tenant_id,
                created_by=actor_id,
            )
            notifications.append(notification)

        created = await self.repository.bulk_create_notifications(notifications)

        # Create delivery records for each channel
        for notification in created:
            for channel in notification.channels:
                delivery = NotificationDelivery(
                    notification_id=notification.id,
                    channel=NotificationChannel(channel) if channel in NotificationChannel.__members__.values() else NotificationChannel.IN_APP,
                    recipient_address=None,  # Would be populated from user profile
                    subject=notification.title,
                    content=notification.message,
                    status=NotificationStatus.PENDING,
                    tenant_id=tenant_id,
                )
                await self.repository.create_delivery(delivery)

        return created

    async def get_notification(self, notification_id: UUID, tenant_id: UUID) -> Notification:
        notification = await self.repository.get_notification_by_id(notification_id, tenant_id)
        if not notification:
            raise NotFoundException(detail="Notification not found")
        return notification

    async def get_notifications(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        recipient_id: Optional[UUID] = None,
        trigger: Optional[str] = None,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Notification], int]:
        trigger_enum = None
        if trigger:
            try:
                trigger_enum = NotificationTrigger(trigger)
            except ValueError:
                raise ValidationException(detail=f"Invalid trigger: {trigger}")

        status_enum = None
        if status:
            try:
                status_enum = NotificationStatus(status)
            except ValueError:
                raise ValidationException(detail=f"Invalid status: {status}")

        return await self.repository.get_all_notifications(
            tenant_id, page, page_size, recipient_id, trigger_enum, status_enum,
            entity_type, entity_id, start_date, end_date, sort_by, sort_order
        )

    async def mark_as_read(self, notification_id: UUID, tenant_id: UUID, user_id: UUID) -> Notification:
        notification = await self.get_notification(notification_id, tenant_id)
        if notification.recipient_id != user_id:
            raise ValidationException(detail="Cannot mark another user's notification as read")

        return await self.repository.mark_as_read(notification_id, tenant_id)

    async def mark_all_as_read(self, tenant_id: UUID, user_id: UUID) -> int:
        return await self.repository.mark_all_as_read(user_id, tenant_id)

    async def get_stats(self, tenant_id: UUID, user_id: UUID) -> NotificationStatsResponse:
        recipient_id = user_id

        total_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
            )
        )
        total = total_result.scalar() or 0

        unread_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
                Notification.status != NotificationStatus.READ,
            )
        )
        unread = unread_result.scalar() or 0

        read_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
                Notification.status == NotificationStatus.READ,
            )
        )
        read = read_result.scalar() or 0

        pending_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
                Notification.status == NotificationStatus.PENDING,
            )
        )
        pending = pending_result.scalar() or 0

        failed_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
                Notification.status == NotificationStatus.FAILED,
            )
        )
        failed = failed_result.scalar() or 0

        # By trigger
        trigger_result = await self.db.execute(
            select(Notification.trigger, func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
            ).group_by(Notification.trigger)
        )
        by_trigger = {str(row[0]): row[1] for row in trigger_result.all()}

        # By priority
        priority_result = await self.db.execute(
            select(Notification.priority, func.count(Notification.id)).where(
                Notification.recipient_id == recipient_id,
                Notification.tenant_id == tenant_id,
            ).group_by(Notification.priority)
        )
        by_priority = {str(row[0]): row[1] for row in priority_result.all()}

        return NotificationStatsResponse(
            total=total,
            unread=unread,
            read=read,
            pending=pending,
            failed=failed,
            by_trigger=by_trigger,
            by_priority=by_priority,
        )

    # Preference methods
    async def set_preference(
        self, user_id: UUID, trigger: str, channel: str, data: NotificationPreferenceCreate,
        tenant_id: UUID, created_by: UUID
    ) -> NotificationPreference:
        try:
            trigger_enum = NotificationTrigger(trigger)
            channel_enum = NotificationChannel(channel)
        except ValueError:
            raise ValidationException(detail="Invalid trigger or channel")

        return await self.repository.upsert_preference(
            user_id, trigger_enum, channel_enum, tenant_id, data, created_by
        )

    async def get_preferences(self, user_id: UUID, tenant_id: UUID) -> List[NotificationPreference]:
        return await self.repository.get_preferences_for_user(user_id, tenant_id)

    async def update_preference(
        self, preference_id: UUID, tenant_id: UUID, data: NotificationPreferenceUpdate, updated_by: UUID
    ) -> NotificationPreference:
        # Would need to get by ID - simplified for now
        preferences = await self.repository.get_preferences_for_user(updated_by, tenant_id)
        preference = next((p for p in preferences if p.id == preference_id), None)
        if not preference:
            raise NotFoundException(detail="Preference not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preference, field, value)
        preference.updated_by = updated_by
        return await self.repository.update_preference(preference)