import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal
from app.modules.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
)
from app.modules.outbox.models import OutboxEventType
from app.modules.outbox.service import get_outbox_service
from app.workers.base import TenantAwareWorker

logger = logging.getLogger(__name__)


class DeadlineReminderSender(TenantAwareWorker):
    def __init__(self, tenant_id: UUID):
        super().__init__(tenant_id)

    async def execute(self) -> dict:
        reminders_sent = 0

        async with self.session() as session:
            from app.modules.compliance.models import ComplianceCycle, ComplianceStatus
            from app.modules.notices.models import Notice, NoticeStatus
            from app.modules.tasks.models import Task, TaskStatus

            today = date.today()
            upcoming = today + timedelta(days=7)

            tasks_result = await session.execute(
                select(Task).where(
                    Task.tenant_id == self.tenant_id,
                    Task.due_date.between(today, upcoming),
                    Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
                )
            )
            tasks = tasks_result.scalars().all()

            for task in tasks:
                await self._send_task_deadline_reminder(session, task)
                reminders_sent += 1

            compliance_result = await session.execute(
                select(ComplianceCycle).where(
                    ComplianceCycle.tenant_id == self.tenant_id,
                    ComplianceCycle.due_date.between(today, upcoming),
                    ComplianceCycle.status.in_([ComplianceStatus.PENDING, ComplianceStatus.IN_PROGRESS]),
                )
            )
            cycles = compliance_result.scalars().all()

            for cycle in cycles:
                await self._send_compliance_deadline_reminder(session, cycle)
                reminders_sent += 1

            notices_result = await session.execute(
                select(Notice).where(
                    Notice.tenant_id == self.tenant_id,
                    Notice.response_due_date.between(today, upcoming),
                    Notice.status.in_([NoticeStatus.RECEIVED, NoticeStatus.ACKNOWLEDGED, NoticeStatus.UNDER_REVIEW]),
                )
            )
            notices = notices_result.scalars().all()

            for notice in notices:
                await self._send_notice_deadline_reminder(session, notice)
                reminders_sent += 1

        return {
            "tenant_id": str(self.tenant_id),
            "reminders_sent": reminders_sent,
        }

    async def _send_task_deadline_reminder(self, session: AsyncSession, task):
        outbox_service = get_outbox_service(session)
        await outbox_service.emit_event(
            tenant_id=self.tenant_id,
            event_type=OutboxEventType.NOTIFICATION_CREATED,
            aggregate_type="notification",
            aggregate_id=task.id,
            payload={
                "trigger": "deadline_approaching",
                "entity_type": "task",
                "entity_id": str(task.id),
                "title": f"Task deadline approaching: {task.title}",
                "message": f"Task '{task.title}' is due on {task.due_date}",
                "channels": ["in_app", "email"],
                "recipient_id": str(task.assigned_user_id) if task.assigned_user_id else None,
            },
            idempotency_key=f"deadline_task_{task.id}_{task.due_date.isoformat()}",
        )

    async def _send_compliance_deadline_reminder(self, session: AsyncSession, cycle):
        outbox_service = get_outbox_service(session)
        await outbox_service.emit_event(
            tenant_id=self.tenant_id,
            event_type=OutboxEventType.NOTIFICATION_CREATED,
            aggregate_type="notification",
            aggregate_id=cycle.id,
            payload={
                "trigger": "deadline_approaching",
                "entity_type": "compliance_cycle",
                "entity_id": str(cycle.id),
                "title": "Compliance deadline approaching",
                "message": f"Compliance cycle for {cycle.compliance_type.code} is due on {cycle.due_date}",
                "channels": ["in_app", "email"],
            },
            idempotency_key=f"deadline_compliance_{cycle.id}_{cycle.due_date.isoformat()}",
        )

    async def _send_notice_deadline_reminder(self, session: AsyncSession, notice):
        outbox_service = get_outbox_service(session)
        await outbox_service.emit_event(
            tenant_id=self.tenant_id,
            event_type=OutboxEventType.NOTIFICATION_CREATED,
            aggregate_type="notification",
            aggregate_id=notice.id,
            payload={
                "trigger": "deadline_approaching",
                "entity_type": "notice",
                "entity_id": str(notice.id),
                "title": f"Notice deadline approaching: {notice.notice_number}",
                "message": f"Notice response due on {notice.response_due_date}",
                "channels": ["in_app", "email"],
            },
            idempotency_key=f"deadline_notice_{notice.id}_{notice.response_due_date.isoformat()}",
        )


class NotificationDeliveryProcessor(TenantAwareWorker):
    def __init__(self, tenant_id: UUID):
        super().__init__(tenant_id)

    async def execute(self) -> dict:
        delivered = 0
        failed = 0

        async with self.session() as session:
            result = await session.execute(
                select(Notification).where(
                    Notification.tenant_id == self.tenant_id,
                    Notification.status == NotificationStatus.PENDING,
                )
            )
            notifications = result.scalars().all()

            for notification in notifications:
                try:
                    await self._deliver_notification(session, notification)
                    delivered += 1
                except Exception as e:
                    logger.error(f"Failed to deliver notification {notification.id}: {e}")
                    notification.status = NotificationStatus.FAILED
                    failed += 1

        return {
            "tenant_id": str(self.tenant_id),
            "delivered": delivered,
            "failed": failed,
        }

    async def _deliver_notification(self, session: AsyncSession, notification: Notification):
        for channel in notification.channels:
            delivery = NotificationDelivery(
                notification_id=notification.id,
                channel=channel,
                status=NotificationStatus.PENDING,
                tenant_id=self.tenant_id,
            )
            session.add(delivery)
            await session.flush()

            try:
                if channel == NotificationChannel.IN_APP:
                    await self._deliver_in_app(session, notification, delivery)
                elif channel == NotificationChannel.EMAIL:
                    await self._deliver_email(session, notification, delivery)
                elif channel == NotificationChannel.SMS:
                    await self._deliver_sms(session, notification, delivery)
                elif channel == NotificationChannel.WHATSAPP:
                    await self._deliver_whatsapp(session, notification, delivery)

                delivery.status = NotificationStatus.DELIVERED
                delivery.delivered_at = datetime.now(UTC)

            except Exception as e:
                delivery.status = NotificationStatus.FAILED
                delivery.failed_at = datetime.now(UTC)
                delivery.error_message = str(e)
                raise

        notification.status = NotificationStatus.SENT
        notification.read_at = None

    async def _deliver_in_app(self, session: AsyncSession, notification: Notification, delivery: NotificationDelivery):
        pass

    async def _deliver_email(self, session: AsyncSession, notification: Notification, delivery: NotificationDelivery):
        pass

    async def _deliver_sms(self, session: AsyncSession, notification: Notification, delivery: NotificationDelivery):
        pass

    async def _deliver_whatsapp(self, session: AsyncSession, notification: Notification, delivery: NotificationDelivery):
        pass


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def send_deadline_reminders(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_send_deadline_reminders())
        return result
    finally:
        loop.close()


async def run_send_deadline_reminders():
    from app.modules.firms.models import Firm

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]

    total_sent = 0

    for tenant_id in tenant_ids:
        try:
            sender = DeadlineReminderSender(tenant_id)
            result = await sender.execute()
            total_sent += result["reminders_sent"]
        except Exception as e:
            logger.error(f"Failed to send deadline reminders for tenant {tenant_id}: {e}")

    return {"total_reminders_sent": total_sent}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_notification_deliveries(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_process_notification_deliveries())
        return result
    finally:
        loop.close()


async def run_process_notification_deliveries():
    from app.modules.firms.models import Firm

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]

    total_delivered = 0
    total_failed = 0

    for tenant_id in tenant_ids:
        try:
            processor = NotificationDeliveryProcessor(tenant_id)
            result = await processor.execute()
            total_delivered += result["delivered"]
            total_failed += result["failed"]
        except Exception as e:
            logger.error(f"Failed to process notifications for tenant {tenant_id}: {e}")

    return {"total_delivered": total_delivered, "total_failed": total_failed}
