"""UDIN background worker tasks"""

from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal as async_session_maker
from app.core.tenancy.context import set_tenant_context
from app.modules.udin.models import UDINRecord, UDINStatus
from app.modules.firms.models import Firm


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_udin_expiry_check(self) -> dict:
    """Check for expired UDIN records"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_expired = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    # Auto-expire UDINs that are older than 1 year and not verified
                    from app.modules.udin.service import UDINService
                    service = UDINService(db)
                    
                    result = await db.execute(
                        select(UDINRecord).where(
                            UDINRecord.tenant_id == firm.id,
                            UDINRecord.status == UDINStatus.GENERATED.value,
                            UDINRecord.generated_at < datetime.utcnow() - timedelta(days=365),
                        )
                    )
                    expired_udins = result.scalars().all()
                    
                    for udin in expired_udins:
                        udin.status = UDINStatus.EXPIRED.value
                        await db.commit()
                        total_expired += 1
                        
                except Exception as e:
                    print(f"Error processing UDIN expiry for tenant {firm.id}: {e}")
            
            return {"total_auto_expired": total_expired}
    
    import asyncio
    return asyncio.run(_process())


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_udin_verification_reminders(self) -> dict:
    """Send reminders for pending UDIN verifications"""
    # This would send reminders to professionals to verify their UDINs
    return {"reminders_sent": 0}