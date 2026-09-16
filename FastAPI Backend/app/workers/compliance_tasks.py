import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal
from app.core.tenancy.context import TenantContext
from app.modules.compliance.models import ComplianceCycle, ComplianceStatus, ComplianceType
from app.modules.outbox.models import OutboxEventType
from app.modules.outbox.service import get_outbox_service
from app.workers.base import TenantAwareWorker

logger = logging.getLogger(__name__)


class ComplianceCycleGenerator(TenantAwareWorker):
    def __init__(self, tenant_id: UUID):
        super().__init__(tenant_id)

    async def execute(self) -> dict:
        cycles_created = 0
        cycles_updated = 0

        async with self.session() as session:
            result = await session.execute(
                select(ComplianceType).where(
                    ComplianceType.tenant_id == self.tenant_id,
                    ComplianceType.is_active == True,
                )
            )
            compliance_types = result.scalars().all()

            for ctype in compliance_types:
                created, updated = await self._generate_cycles_for_type(session, ctype)
                cycles_created += created
                cycles_updated += updated

        return {
            "tenant_id": str(self.tenant_id),
            "cycles_created": cycles_created,
            "cycles_updated": cycles_updated,
        }

    async def _generate_cycles_for_type(
        self, session: AsyncSession, ctype: ComplianceType
    ) -> tuple[int, int]:
        created = 0
        updated = 0

        frequency = ctype.frequency
        today = date.today()

        if frequency.value == "ANNUAL":
            start_date = date(today.year, 4, 1)
            end_date = date(today.year + 1, 3, 31)
        elif frequency.value == "QUARTERLY":
            quarter = (today.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date = date(today.year, start_month, 1)
            if start_month == 10:
                end_date = date(today.year + 1, 3, 31)
            else:
                end_date = date(today.year, start_month + 3, 1) - timedelta(days=1)
        elif frequency.value == "MONTHLY":
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        else:
            return 0, 0

        existing = await session.execute(
            select(ComplianceCycle).where(
                ComplianceCycle.tenant_id == self.tenant_id,
                ComplianceCycle.compliance_type_id == ctype.id,
                ComplianceCycle.period_start == start_date,
            )
        )
        cycle = existing.scalar_one_or_none()

        if cycle:
            if cycle.due_date != ctype.due_date:
                cycle.due_date = ctype.due_date
                cycle.updated_at = datetime.now(UTC)
                updated += 1

                outbox_service = get_outbox_service(session)
                await outbox_service.emit_event(
                    tenant_id=self.tenant_id,
                    event_type=OutboxEventType.COMPLIANCE_DUE_DATE_CHANGED,
                    aggregate_type="compliance_cycle",
                    aggregate_id=cycle.id,
                    payload={"old_due_date": cycle.due_date.isoformat(), "new_due_date": ctype.due_date.isoformat()},
                )
        else:
            cycle = ComplianceCycle(
                tenant_id=self.tenant_id,
                compliance_type_id=ctype.id,
                period_start=start_date,
                period_end=end_date,
                due_date=ctype.due_date,
                status=ComplianceStatus.PENDING,
            )
            session.add(cycle)
            await session.flush()
            created += 1

            outbox_service = get_outbox_service(session)
            await outbox_service.emit_event(
                tenant_id=self.tenant_id,
                event_type=OutboxEventType.COMPLIANCE_CYCLE_CREATED,
                aggregate_type="compliance_cycle",
                aggregate_id=cycle.id,
                payload={"period_start": start_date.isoformat(), "period_end": end_date.isoformat()},
            )

        return created, updated


class ComplianceReminderSender(TenantAwareWorker):
    def __init__(self, tenant_id: UUID):
        super().__init__(tenant_id)

    async def execute(self) -> dict:
        reminders_sent = 0

        async with self.session() as session:
            today = date.today()
            reminder_dates = [
                today + timedelta(days=30),
                today + timedelta(days=14),
                today + timedelta(days=7),
                today + timedelta(days=1),
            ]

            for reminder_date in reminder_dates:
                result = await session.execute(
                    select(ComplianceCycle).where(
                        ComplianceCycle.tenant_id == self.tenant_id,
                        ComplianceCycle.due_date == reminder_date,
                        ComplianceCycle.status.in_([ComplianceStatus.PENDING, ComplianceStatus.IN_PROGRESS]),
                    )
                )
                cycles = result.scalars().all()

                for cycle in cycles:
                    await self._send_reminder(session, cycle, reminder_date)
                    reminders_sent += 1

        return {
            "tenant_id": str(self.tenant_id),
            "reminders_sent": reminders_sent,
        }

    async def _send_reminder(self, session: AsyncSession, cycle: ComplianceCycle, reminder_date: date):
        outbox_service = get_outbox_service(session)
        await outbox_service.emit_event(
            tenant_id=self.tenant_id,
            event_type=OutboxEventType.COMPLIANCE_REMINDER_SENT,
            aggregate_type="compliance_cycle",
            aggregate_id=cycle.id,
            payload={
                "reminder_date": reminder_date.isoformat(),
                "days_until_due": (cycle.due_date - reminder_date).days,
            },
            idempotency_key=f"reminder_{cycle.id}_{reminder_date.isoformat()}",
        )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_compliance_cycles(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_generate_compliance_cycles())
        return result
    finally:
        loop.close()


async def run_generate_compliance_cycles():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(TenantContext))

    from app.modules.firms.models import Firm
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]

    total_created = 0
    total_updated = 0

    for tenant_id in tenant_ids:
        try:
            generator = ComplianceCycleGenerator(tenant_id)
            result = await generator.execute()
            total_created += result["cycles_created"]
            total_updated += result["cycles_updated"]
        except Exception as e:
            logger.error(f"Failed to generate compliance cycles for tenant {tenant_id}: {e}")

    return {
        "total_cycles_created": total_created,
        "total_cycles_updated": total_updated,
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def send_compliance_reminders(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_send_compliance_reminders())
        return result
    finally:
        loop.close()


async def run_send_compliance_reminders():
    from app.modules.firms.models import Firm

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]

    total_reminders = 0

    for tenant_id in tenant_ids:
        try:
            sender = ComplianceReminderSender(tenant_id)
            result = await sender.execute()
            total_reminders += result["reminders_sent"]
        except Exception as e:
            logger.error(f"Failed to send compliance reminders for tenant {tenant_id}: {e}")

    return {"total_reminders_sent": total_reminders}
