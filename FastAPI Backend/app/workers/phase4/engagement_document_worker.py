"""Engagement Document background worker tasks"""

from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal as async_session_maker
from app.core.tenancy.context import set_tenant_context
from app.modules.engagement_documents.models import EngagementDocument, EngagementDocumentStatus
from app.modules.firms.models import Firm
from app.modules.notifications.service import NotificationService


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_engagement_document_reminders(self) -> dict:
    """Send reminders for pending engagement document signatures"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_reminders = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    count = await _process_tenant_engagement_reminders(db, firm.id)
                    total_reminders += count
                except Exception as e:
                    print(f"Error processing engagement doc reminders for tenant {firm.id}: {e}")
            
            return {"total_reminders_sent": total_reminders}
    
    import asyncio
    return asyncio.run(_process())


async def _process_tenant_engagement_reminders(db, tenant_id: UUID) -> int:
    """Process engagement document reminders for a specific tenant"""
    from app.modules.engagement_documents.service import EngagementDocumentSignerService
    from app.modules.engagement_documents.models import EngagementDocumentSigner
    
    result = await db.execute(
        select(EngagementDocumentSigner).where(
            EngagementDocumentSigner.tenant_id == tenant_id,
            EngagementDocumentSigner.status == "pending",
            EngagementDocumentSigner.reminder_sent_at < datetime.utcnow() - timedelta(days=3),
        ).limit(100)
    )
    pending_signers = result.scalars().all()
    
    reminder_count = 0
    for signer in pending_signers:
        notification_service = NotificationService(db)
        await notification_service.send_notification(
            user_id=signer.signer_id,
            trigger="engagement_document_signature_reminder",
            data={
                "document_title": signer.engagement_document.title if signer.engagement_document else "Engagement Document",
                "document_number": signer.engagement_document.document_number if signer.engagement_document else "Unknown",
                "signer_role": signer.signer_role,
            },
            tenant_id=tenant_id,
        )
        
        signer.reminder_sent_at = datetime.utcnow()
        signer.reminder_count += 1
        await db.commit()
        reminder_count += 1
    
    return reminder_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_expired_engagement_documents(self) -> dict:
    """Auto-expire engagement documents that have passed their valid_until date"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_expired = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    result = await db.execute(
                        select(EngagementDocument).where(
                            EngagementDocument.tenant_id == firm.id,
                            EngagementDocument.status.in_([
                                EngagementDocumentStatus.DRAFT.value,
                                EngagementDocumentStatus.PENDING_REVIEW.value,
                                EngagementDocumentStatus.PENDING_SIGNATURE.value,
                            ]),
                            EngagementDocument.valid_until < datetime.utcnow(),
                        )
                    )
                    expired_docs = result.scalars().all()
                    
                    for doc in expired_docs:
                        doc.status = EngagementDocumentStatus.EXPIRED.value
                        await db.commit()
                        total_expired += 1
                except Exception as e:
                    print(f"Error expiring engagement docs for tenant {firm.id}: {e}")
            
            return {"total_auto_expired": total_expired}
    
    import asyncio
    return asyncio.run(_process())