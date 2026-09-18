"""E-Signature background worker tasks"""

from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal as async_session_maker
from app.core.tenancy.context import set_tenant_context
from app.modules.e_signature.models import ESignatureRequest, ESignatureRequestStatus
from app.modules.firms.models import Firm
from app.modules.notifications.service import NotificationService


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_esignature_expiry_reminders(self) -> dict:
    """Send reminders for pending e-signature requests"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_reminders = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    count = await _process_tenant_esignature_reminders(db, firm.id)
                    total_reminders += count
                except Exception as e:
                    print(f"Error processing e-signature reminders for tenant {firm.id}: {e}")
            
            return {"total_reminders_sent": total_reminders}
    
    import asyncio
    return asyncio.run(_process())


async def _process_tenant_esignature_reminders(db, tenant_id: UUID) -> int:
    """Process e-signature reminders for a specific tenant"""
    from app.modules.e_signature.models import ESigner
    from app.modules.e_signature.service import ESignerService
    
    # Find pending signers who haven't been reminded recently
    result = await db.execute(
        select(ESigner).where(
            ESigner.tenant_id == tenant_id,
            ESigner.status.in_(["pending", "sent", "viewed"]),
            ESigner.reminder_count < 3,
        ).limit(100)
    )
    pending_signers = result.scalars().all()
    
    reminder_count = 0
    for signer in pending_signers:
        if signer.sent_at and (datetime.utcnow() - signer.sent_at) > timedelta(days=2):
            notification_service = NotificationService(db)
            await notification_service.send_notification(
                user_id=signer.signer_id if signer.signer_id else None,
                trigger="esignature_signature_reminder",
                data={
                    "request_title": signer.request.title if signer.request else "E-Signature Request",
                    "signer_name": signer.name,
                    "signer_role": signer.role,
                },
                tenant_id=tenant_id,
            )
            
            signer.reminder_count += 1
            await db.commit()
            reminder_count += 1
    
    return reminder_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_esignature_auto_expiry(self) -> dict:
    """Auto-expire e-signature requests that have passed their expiry date"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_expired = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    result = await db.execute(
                        select(ESignatureRequest).where(
                            ESignatureRequest.tenant_id == firm.id,
                            ESignatureRequest.status.in_([
                                ESignatureRequestStatus.SENT.value,
                                ESignatureRequestStatus.IN_PROGRESS.value,
                                ESignatureRequestStatus.PENDING.value,
                            ]),
                            ESignatureRequest.expires_at < datetime.utcnow(),
                        )
                    )
                    expired_requests = result.scalars().all()
                    
                    for req in expired_requests:
                        req.status = ESignatureRequestStatus.EXPIRED.value
                        await db.commit()
                        total_expired += 1
                except Exception as e:
                    print(f"Error expiring e-signature requests for tenant {firm.id}: {e}")
            
            return {"total_auto_expired": total_expired}
    
    import asyncio
    return asyncio.run(_process())


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_esignature_webhook_queue(self) -> dict:
    """Process pending e-signature webhook events"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_processed = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    from app.modules.e_signature.service import ESignatureWebhookService
                    from app.modules.e_signature.models import ESignatureWebhookEvent
                    
                    result = await db.execute(
                        select(ESignatureWebhookEvent).where(
                            ESignatureWebhookEvent.tenant_id == firm.id,
                            ESignatureWebhookEvent.processed == False,
                            ESignatureWebhookEvent.retry_count < 3,
                        ).limit(50)
                    )
                    pending_events = result.scalars().all()
                    
                    service = ESignatureWebhookService(db)
                    for event in pending_events:
                        await service.process_webhook(
                            # Reconstruct webhook data from event
                            ESignatureWebhookEventCreate(
                                provider=event.provider,
                                external_event_id=event.external_event_id,
                                event_type=event.event_type,
                                external_request_id=event.external_request_id,
                                payload=event.payload,
                                idempotency_key=event.idempotency_key,
                            ),
                            firm.id
                        )
                        total_processed += 1
                except Exception as e:
                    print(f"Error processing webhook events for tenant {firm.id}: {e}")
            
            return {"total_webhooks_processed": total_processed}
    
    import asyncio
    return asyncio.run(_process())