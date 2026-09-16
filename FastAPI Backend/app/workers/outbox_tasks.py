import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal
from app.modules.outbox.models import OutboxEvent, OutboxEventType
from app.modules.outbox.repository import OutboxRepository
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class OutboxProcessor(BaseWorker):
    def __init__(self, batch_size: int = 100):
        super().__init__()
        self.batch_size = batch_size
        self._handlers: dict[OutboxEventType, callable] = {}

    def register_handler(self, event_type: OutboxEventType, handler: callable):
        self._handlers[event_type] = handler

    async def execute(self) -> dict:
        processed = 0
        failed = 0
        dead_lettered = 0

        async with self.session() as session:
            repo = OutboxRepository(session)
            events = await repo.get_events_for_processing(limit=self.batch_size)

            for event in events:
                try:
                    await self._process_event(session, repo, event)
                    processed += 1
                except Exception as e:
                    logger.error(f"Failed to process event {event.id}: {e}")
                    await repo.mark_failed(event.id, str(e))
                    failed += 1

                    if event.retry_count >= event.max_retries:
                        await repo.mark_dead_letter(event.id, f"Max retries exceeded: {e}")
                        dead_lettered += 1

        return {
            "processed": processed,
            "failed": failed,
            "dead_lettered": dead_lettered,
        }

    async def _process_event(self, session: AsyncSession, repo: OutboxRepository, event: OutboxEvent):
        if not await repo.mark_processing(event.id):
            logger.warning(f"Event {event.id} already being processed, skipping")
            return

        handler = self._handlers.get(event.event_type)
        if not handler:
            raise ValueError(f"No handler registered for event type: {event.event_type}")

        try:
            await handler(event)
            await repo.mark_processed(event.id)
        except Exception:
            raise


async def get_outbox_processor() -> OutboxProcessor:
    processor = OutboxProcessor()

    processor.register_handler(
        OutboxEventType.COMPLIANCE_CYCLE_CREATED,
        handle_compliance_cycle_created,
    )
    processor.register_handler(
        OutboxEventType.COMPLIANCE_CYCLE_UPDATED,
        handle_compliance_cycle_updated,
    )
    processor.register_handler(
        OutboxEventType.COMPLIANCE_DUE_DATE_CHANGED,
        handle_compliance_due_date_changed,
    )
    processor.register_handler(
        OutboxEventType.INVOICE_CREATED,
        handle_invoice_created,
    )
    processor.register_handler(
        OutboxEventType.INVOICE_PAID,
        handle_invoice_paid,
    )
    processor.register_handler(
        OutboxEventType.PAYMENT_CREATED,
        handle_payment_created,
    )
    processor.register_handler(
        OutboxEventType.TASK_CREATED,
        handle_task_created,
    )
    processor.register_handler(
        OutboxEventType.TASK_ASSIGNED,
        handle_task_assigned,
    )
    processor.register_handler(
        OutboxEventType.WORKFLOW_TRANSITIONED,
        handle_workflow_transitioned,
    )
    processor.register_handler(
        OutboxEventType.NOTIFICATION_CREATED,
        handle_notification_created,
    )
    processor.register_handler(
        OutboxEventType.DOCUMENT_UPLOADED,
        handle_document_uploaded,
    )

    return processor


async def handle_compliance_cycle_created(event: OutboxEvent):
    logger.info(f"Handling compliance cycle created: {event.aggregate_id}")
    await send_compliance_notifications(event.tenant_id, event.aggregate_id, "created")


async def handle_compliance_cycle_updated(event: OutboxEvent):
    logger.info(f"Handling compliance cycle updated: {event.aggregate_id}")
    await send_compliance_notifications(event.tenant_id, event.aggregate_id, "updated")


async def handle_compliance_due_date_changed(event: OutboxEvent):
    logger.info(f"Handling compliance due date changed: {event.aggregate_id}")
    await send_due_date_change_notifications(event.tenant_id, event.aggregate_id, event.payload)


async def handle_invoice_created(event: OutboxEvent):
    logger.info(f"Handling invoice created: {event.aggregate_id}")
    await send_invoice_notifications(event.tenant_id, event.aggregate_id, "created")


async def handle_invoice_paid(event: OutboxEvent):
    logger.info(f"Handling invoice paid: {event.aggregate_id}")
    await send_invoice_notifications(event.tenant_id, event.aggregate_id, "paid")


async def handle_payment_created(event: OutboxEvent):
    logger.info(f"Handling payment created: {event.aggregate_id}")
    await send_payment_notifications(event.tenant_id, event.aggregate_id)


async def handle_task_created(event: OutboxEvent):
    logger.info(f"Handling task created: {event.aggregate_id}")
    await send_task_notifications(event.tenant_id, event.aggregate_id, "created")


async def handle_task_assigned(event: OutboxEvent):
    logger.info(f"Handling task assigned: {event.aggregate_id}")
    await send_task_notifications(event.tenant_id, event.aggregate_id, "assigned")


async def handle_workflow_transitioned(event: OutboxEvent):
    logger.info(f"Handling workflow transitioned: {event.aggregate_id}")
    await send_workflow_notifications(event.tenant_id, event.aggregate_id, event.payload)


async def handle_notification_created(event: OutboxEvent):
    logger.info(f"Handling notification created: {event.aggregate_id}")
    await deliver_notification(event.tenant_id, event.aggregate_id)


async def handle_document_uploaded(event: OutboxEvent):
    logger.info(f"Handling document uploaded: {event.aggregate_id}")
    await process_document(event.tenant_id, event.aggregate_id)


async def send_compliance_notifications(tenant_id: UUID, cycle_id: UUID, action: str):
    pass


async def send_due_date_change_notifications(tenant_id: UUID, cycle_id: UUID, payload: dict):
    pass


async def send_invoice_notifications(tenant_id: UUID, invoice_id: UUID, action: str):
    pass


async def send_payment_notifications(tenant_id: UUID, payment_id: UUID):
    pass


async def send_task_notifications(tenant_id: UUID, task_id: UUID, action: str):
    pass


async def send_workflow_notifications(tenant_id: UUID, instance_id: UUID, payload: dict):
    pass


async def deliver_notification(tenant_id: UUID, notification_id: UUID):
    pass


async def process_document(tenant_id: UUID, document_id: UUID):
    pass


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_outbox_events(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_outbox_processor())
        return result
    finally:
        loop.close()


async def run_outbox_processor():
    processor = await get_outbox_processor()
    return await processor.execute()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=3600)
def cleanup_processed_outbox(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_cleanup_outbox())
        return result
    finally:
        loop.close()


async def run_cleanup_outbox():
    async with AsyncSessionLocal() as session:
        repo = OutboxRepository(session)
        total_cleaned = 0
        # Process all tenants
        result = await session.execute(select(OutboxEvent.tenant_id).distinct())
        tenant_ids = [row[0] for row in result.fetchall()]

        for tenant_id in tenant_ids:
            cleaned = await repo.cleanup_processed(tenant_id, older_than_days=30)
            total_cleaned += cleaned

        return {"cleaned": total_cleaned}
