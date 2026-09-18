"""MFA background worker tasks"""

from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal as async_session_maker
from app.core.tenancy.context import set_tenant_context
from app.modules.mfa.models import MFAEnrollment, MFAEnrollmentStatus, MFALoginChallenge
from app.modules.firms.models import Firm


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_mfa_lockout_cleanup(self) -> dict:
    """Clean up expired MFA lockouts and challenges"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_cleaned = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    # Unlock MFA enrollments where lockout period has passed
                    result = await db.execute(
                        select(MFAEnrollment).where(
                            MFAEnrollment.tenant_id == firm.id,
                            MFAEnrollment.status == MFAEnrollmentStatus.LOCKED.value,
                            MFAEnrollment.locked_at < datetime.utcnow() - timedelta(minutes=15),
                        )
                    )
                    locked_enrollments = result.scalars().all()
                    
                    for enrollment in locked_enrollments:
                        enrollment.status = MFAEnrollmentStatus.ACTIVE.value
                        enrollment.failed_attempts = 0
                        enrollment.locked_at = None
                        enrollment.lock_reason = None
                        await db.commit()
                        total_cleaned += 1
                    
                    # Clean up expired login challenges
                    await db.execute(
                        select(MFALoginChallenge).where(
                            MFALoginChallenge.tenant_id == firm.id,
                            MFALoginChallenge.status == "pending",
                            MFALoginChallenge.expires_at < datetime.utcnow(),
                        ).delete(synchronize_session=False)
                    )
                    await db.commit()
                    
                except Exception as e:
                    print(f"Error cleaning MFA for tenant {firm.id}: {e}")
            
            return {"total_cleaned": total_cleaned}
    
    import asyncio
    return asyncio.run(_process())


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_mfa_enrollment_expiry(self) -> dict:
    """Expire pending MFA enrollments that haven't been verified"""
    async def _process():
        async with async_session_maker() as db:
            firms_result = await db.execute(select(Firm).where(Firm.is_active == True))
            firms = firms_result.scalars().all()
            
            total_expired = 0
            for firm in firms:
                set_tenant_context(firm.id)
                try:
                    # Expire pending enrollments older than 24 hours
                    result = await db.execute(
                        select(MFAEnrollment).where(
                            MFAEnrollment.tenant_id == firm.id,
                            MFAEnrollment.status == MFAEnrollmentStatus.PENDING.value,
                            MFAEnrollment.created_at < datetime.utcnow() - timedelta(hours=24),
                        )
                    )
                    pending_enrollments = result.scalars().all()
                    
                    for enrollment in pending_enrollments:
                        enrollment.status = MFAEnrollmentStatus.DISABLED.value
                        await db.commit()
                        total_expired += 1
                        
                except Exception as e:
                    print(f"Error expiring MFA enrollments for tenant {firm.id}: {e}")
            
            return {"total_expired": total_expired}
    
    import asyncio
    return asyncio.run(_process())