"""License/Registration background worker tasks"""

from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal as async_session_maker
from app.core.tenancy.context import set_tenant_context
from app.modules.licenses.models import License, LicenseStatus
from app.modules.firms.models import Firm
from app.modules.notifications.service import NotificationService


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_license_expiry_reminders(self) -> dict:
    """Process license expiry reminders for all tenants"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_reminders = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    count = await _process_tenant_license_reminders(db, firm.id)
                    total_reminders += count
                except Exception as e:
                    print(f"Error processing license reminders for tenant {firm.id}: {e}")
            
            return {"total_reminders_sent": total_reminders}
    
    import asyncio
    return asyncio.run(_process())


async def _process_tenant_license_reminders(db, tenant_id: UUID) -> int:
    """Process license reminders for a specific tenant"""
    from app.modules.licenses.service import LicenseService
    service = LicenseService(db)
    
    expiring_licenses = await service.get_expiring_soon(tenant_id, days=30)
    
    reminder_count = 0
    for license in expiring_licenses:
        days_until = (license.expiry_date - datetime.utcnow()).days
        
        if days_until in [30, 15, 7, 1] and not license.reminder_sent_at:
            notification_service = NotificationService(db)
            
            recipients = [license.professional_id]
            
            for recipient_id in recipients:
                await notification_service.send_notification(
                    user_id=recipient_id,
                    trigger="license_expiry_reminder",
                    data={
                        "license_number": license.license_number,
                        "professional_name": license.professional.full_name if license.professional else "Unknown",
                        "expiry_date": license.expiry_date.isoformat(),
                        "days_until_expiry": days_until,
                        "license_type": license.license_type.value,
                    },
                    tenant_id=tenant_id,
                )
            
            license.reminder_sent_at = datetime.utcnow()
            await service.repository.update(license)
            reminder_count += 1
    
    return reminder_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_license_auto_expiry(self) -> dict:
    """Auto-expire licenses that have passed their expiry date"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_expired = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    count = await _auto_expire_tenant_licenses(db, firm.id)
                    total_expired += count
                except Exception as e:
                    print(f"Error auto-expiring licenses for tenant {firm.id}: {e}")
            
            return {"total_auto_expired": total_expired}
    
    import asyncio
    return asyncio.run(_process())


async def _auto_expire_tenant_licenses(db, tenant_id: UUID) -> int:
    """Auto-expire licenses for a specific tenant"""
    result = await db.execute(
        select(License).where(
            License.tenant_id == tenant_id,
            License.status == LicenseStatus.ACTIVE.value,
            License.expiry_date < datetime.utcnow(),
        )
    )
    expired_licenses = result.scalars().all()
    
    count = 0
    for license in expired_licenses:
        license.status = LicenseStatus.EXPIRED.value
        license.updated_by = None
        await db.commit()
        count += 1
    
    return count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_pending_license_renewals(self) -> dict:
    """Process pending license renewal requests"""
    # Check for renewal requests that need attention
    return {"renewals_processed": 0}