"""DSC Certificate background worker tasks"""

from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal as async_session_maker
from app.core.tenancy.context import set_tenant_context
from app.modules.dsc.models import DSCCertificate, DSCStatus
from app.modules.dsc.service import DSCCertificateService
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User
from app.modules.firms.models import Firm


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_dsc_expiry_reminders(self) -> dict:
    """Process DSC expiry reminders for all tenants"""
    from app.modules.firms.models import Firm
    
    async def _process():
        async with async_session_maker() as db:
            # Get all active firms
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_reminders = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    count = await _process_tenant_dsc_reminders(db, firm.id)
                    total_reminders += count
                except Exception as e:
                    # Log error but continue with other tenants
                    print(f"Error processing DSC reminders for tenant {firm.id}: {e}")
            
            return {"total_reminders_sent": total_reminders}
        
        import asyncio
        return asyncio.run(_process())


async def _process_tenant_dsc_reminders(db, tenant_id: UUID) -> int:
    """Process DSC reminders for a specific tenant"""
    service = DSCCertificateService(db)
    
    # Get expiring certificates (30, 15, 7, 1 days)
    expiring_certs = await service.get_expiring_soon(tenant_id, days=30)
    
    reminder_count = 0
    for cert in expiring_certs:
        days_until = (cert.expiry_date - datetime.utcnow()).days
        
        # Send reminders at specific intervals
        if days_until in [30, 15, 7, 1] and not cert.renewal_reminder_sent:
            # Send notification to holder and custodian
            notification_service = NotificationService(db)
            
            recipients = [cert.holder_id]
            if cert.custodian_id:
                recipients.append(cert.custodian_id)
            
            for recipient_id in recipients:
                await notification_service.send_notification(
                    user_id=recipient_id,
                    trigger="dsc_expiry_reminder",
                    data={
                        "certificate_serial": cert.certificate_serial_number,
                        "holder_name": cert.holder.full_name if cert.holder else "Unknown",
                        "expiry_date": cert.expiry_date.isoformat(),
                        "days_until_expiry": days_until,
                        "dsc_type": cert.dsc_type.value,
                    },
                    tenant_id=tenant_id,
                )
            
            # Mark reminder as sent
            cert.renewal_reminder_sent = True
            await service.repository.update(cert)
            reminder_count += 1
    
    return reminder_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_dsc_auto_expiry(self) -> dict:
    """Auto-expire DSC certificates that have passed their expiry date"""
    from app.core.database.session import async_session_maker
    from app.modules.firms.models import Firm
    
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_expired = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    count = await _auto_expire_tenant_dsc(db, firm.id)
                    total_expired += count
                except Exception as e:
                    print(f"Error auto-expiring DSC for tenant {firm.id}: {e}")
            
            return {"total_auto_expired": total_expired}
    
    import asyncio
    return asyncio.run(_process())


async def _auto_expire_tenant_dsc(db, tenant_id: UUID) -> int:
    """Auto-expire certificates for a specific tenant"""
    service = DSCCertificateService(db)
    
    # Get all active certificates that have expired
    result = await db.execute(
        select(DSCCertificate).where(
            DSCCertificate.tenant_id == tenant_id,
            DSCCertificate.status == DSCStatus.ACTIVE.value,
            DSCCertificate.expiry_date < datetime.utcnow(),
        )
    )
    expired_certs = result.scalars().all()
    
    count = 0
    for cert in expired_certs:
        cert.status = DSCStatus.EXPIRED.value
        cert.updated_by = None  # System
        await service.repository.update(cert)
        count += 1
    
    return count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_pending_dsc_renewals(self) -> dict:
    """Process pending DSC renewal requests that are ready for review"""
    from app.core.database.session import async_session_maker
    from app.modules.firms.models import Firm
    
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_processed = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    count = await _process_tenant_dsc_renewals(db, firm.id)
                    total_processed += count
                except Exception as e:
                    print(f"Error processing DSC renewals for tenant {firm.id}: {e}")
            
            return {"total_renewals_processed": total_processed}
    
    import asyncio
    return asyncio.run(_process())


async def _process_tenant_dsc_renewals(db, tenant_id: UUID) -> int:
    """Process pending renewal requests"""
    # This would check for renewal requests that need attention
    # e.g., send reminders to approvers, escalate overdue requests
    return 0