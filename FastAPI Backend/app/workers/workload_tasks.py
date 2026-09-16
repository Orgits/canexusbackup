import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery.app import celery_app
from app.core.database.session import AsyncSessionLocal
from app.modules.matters.models import Matter, MatterStatus
from app.modules.tasks.models import Task, TaskStatus
from app.modules.users.models import User
from app.modules.workload.models import (
    UserAvailability,
    WorkloadPeriod,
    WorkloadSnapshot,
    WorkloadSummary,
)
from app.workers.base import TenantAwareWorker

logger = logging.getLogger(__name__)


class WorkloadSnapshotGenerator(TenantAwareWorker):
    def __init__(self, tenant_id: UUID, snapshot_date: date | None = None):
        super().__init__(tenant_id)
        self.snapshot_date = snapshot_date or date.today()

    async def execute(self) -> dict:
        snapshots_created = 0

        async with self.session() as session:
            result = await session.execute(
                select(User.id).where(
                    User.tenant_id == self.tenant_id,
                    User.is_active == True,
                )
            )
            user_ids = [row[0] for row in result.fetchall()]

            for user_id in user_ids:
                snapshot = await self._generate_user_snapshot(session, user_id)
                if snapshot:
                    snapshots_created += 1

        return {
            "tenant_id": str(self.tenant_id),
            "snapshot_date": self.snapshot_date.isoformat(),
            "snapshots_created": snapshots_created,
        }

    async def _generate_user_snapshot(self, session: AsyncSession, user_id: UUID) -> WorkloadSnapshot | None:
        existing = await session.execute(
            select(WorkloadSnapshot).where(
                WorkloadSnapshot.tenant_id == self.tenant_id,
                WorkloadSnapshot.user_id == user_id,
                WorkloadSnapshot.snapshot_date == self.snapshot_date,
                WorkloadSnapshot.period_type == WorkloadPeriod.DAILY,
            )
        )
        if existing.scalar_one_or_none():
            return None

        open_tasks = await session.execute(
            select(func.count(Task.id)).where(
                Task.tenant_id == self.tenant_id,
                Task.assigned_user_id == user_id,
                Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
            )
        )
        open_task_count = open_tasks.scalar() or 0

        overdue_tasks = await session.execute(
            select(func.count(Task.id)).where(
                Task.tenant_id == self.tenant_id,
                Task.assigned_user_id == user_id,
                Task.due_date < self.snapshot_date,
                Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
            )
        )
        overdue_task_count = overdue_tasks.scalar() or 0

        open_matters = await session.execute(
            select(func.count(Matter.id)).where(
                Matter.tenant_id == self.tenant_id,
                Matter.responsible_user_id == user_id,
                Matter.status.in_([MatterStatus.IN_PROGRESS, MatterStatus.INFORMATION_PENDING]),
            )
        )
        open_matter_count = open_matters.scalar() or 0

        overdue_matters = await session.execute(
            select(func.count(Matter.id)).where(
                Matter.tenant_id == self.tenant_id,
                Matter.responsible_user_id == user_id,
                Matter.due_date < self.snapshot_date,
                Matter.status.in_([MatterStatus.IN_PROGRESS, MatterStatus.INFORMATION_PENDING]),
            )
        )
        overdue_matter_count = overdue_matters.scalar() or 0

        high_priority_tasks = await session.execute(
            select(func.count(Task.id)).where(
                Task.tenant_id == self.tenant_id,
                Task.assigned_user_id == user_id,
                Task.priority.in_(["HIGH", "URGENT"]),
                Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
            )
        )
        high_priority_count = high_priority_tasks.scalar() or 0

        availability = await session.execute(
            select(func.coalesce(func.sum(UserAvailability.available_hours), 0)).where(
                UserAvailability.tenant_id == self.tenant_id,
                UserAvailability.user_id == user_id,
                UserAvailability.date == self.snapshot_date,
                UserAvailability.is_available == True,
            )
        )
        available_hours = availability.scalar() or 8.0

        allocated_hours = open_task_count * 2.0

        if available_hours > 0:
            utilization = min((allocated_hours / available_hours) * 100, 200)
        else:
            utilization = 0

        snapshot = WorkloadSnapshot(
            tenant_id=self.tenant_id,
            user_id=user_id,
            team_id=None,
            snapshot_date=self.snapshot_date,
            period_type=WorkloadPeriod.DAILY,
            open_tasks=open_task_count,
            overdue_tasks=overdue_task_count,
            open_matters=open_matter_count,
            overdue_matters=overdue_matter_count,
            high_priority_tasks=high_priority_count,
            available_hours=available_hours,
            allocated_hours=allocated_hours,
            utilization_percentage=utilization,
        )
        session.add(snapshot)
        await session.flush()
        return snapshot


class WorkloadSummaryUpdater(TenantAwareWorker):
    def __init__(self, tenant_id: UUID, summary_date: date | None = None):
        super().__init__(tenant_id)
        self.summary_date = summary_date or date.today()

    async def execute(self) -> dict:
        summaries_updated = 0

        async with self.session() as session:
            result = await session.execute(
                select(User.id).where(
                    User.tenant_id == self.tenant_id,
                    User.is_active == True,
                )
            )
            user_ids = [row[0] for row in result.fetchall()]

            for user_id in user_ids:
                await self._update_user_summary(session, user_id)
                summaries_updated += 1

        return {
            "tenant_id": str(self.tenant_id),
            "summary_date": self.summary_date.isoformat(),
            "summaries_updated": summaries_updated,
        }

    async def _update_user_summary(self, session: AsyncSession, user_id: UUID):
        week_start = self.summary_date - timedelta(days=self.summary_date.weekday())
        week_end = week_start + timedelta(days=6)

        snapshots = await session.execute(
            select(WorkloadSnapshot).where(
                WorkloadSnapshot.tenant_id == self.tenant_id,
                WorkloadSnapshot.user_id == user_id,
                WorkloadSnapshot.snapshot_date.between(week_start, week_end),
                WorkloadSnapshot.period_type == WorkloadPeriod.DAILY,
            )
        )
        daily_snapshots = snapshots.scalars().all()

        if not daily_snapshots:
            return

        avg_utilization = sum(s.utilization_percentage for s in daily_snapshots) / len(daily_snapshots)
        total_overdue = sum(s.overdue_tasks + s.overdue_matters for s in daily_snapshots)
        total_high_priority = sum(s.high_priority_tasks for s in daily_snapshots)
        total_open_tasks = sum(s.open_tasks for s in daily_snapshots)
        total_open_matters = sum(s.open_matters for s in daily_snapshots)
        total_hours = sum(s.allocated_hours for s in daily_snapshots)

        from app.modules.notices.models import Notice, NoticeStatus
        overdue_notices = await session.execute(
            select(func.count(Notice.id)).where(
                Notice.tenant_id == self.tenant_id,
                Notice.assigned_user_id == user_id,
                Notice.response_due_date < self.summary_date,
                Notice.status.in_([NoticeStatus.RECEIVED, NoticeStatus.ACKNOWLEDGED, NoticeStatus.UNDER_REVIEW]),
            )
        )
        overdue_notice_count = overdue_notices.scalar() or 0

        is_overloaded = avg_utilization > 90 or total_overdue > 5 or total_high_priority > 3

        stmt = pg_insert(WorkloadSummary).values(
            tenant_id=self.tenant_id,
            user_id=user_id,
            summary_date=self.summary_date,
            avg_utilization_percentage=avg_utilization,
            overdue_tasks=total_overdue,
            overdue_notices=overdue_notice_count,
            high_priority_tasks=total_high_priority,
            open_tasks=total_open_tasks,
            open_matters=total_open_matters,
            total_hours_worked=total_hours,
            is_overloaded=is_overloaded,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "user_id", "summary_date"],
            set_={
                "avg_utilization_percentage": avg_utilization,
                "overdue_tasks": total_overdue,
                "overdue_notices": overdue_notice_count,
                "high_priority_tasks": total_high_priority,
                "open_tasks": total_open_tasks,
                "open_matters": total_open_matters,
                "total_hours_worked": total_hours,
                "is_overloaded": is_overloaded,
                "updated_at": datetime.now(UTC),
            },
        )
        await session.execute(stmt)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_daily_workload_snapshots(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_generate_workload_snapshots())
        return result
    finally:
        loop.close()


async def run_generate_workload_snapshots():
    from app.modules.firms.models import Firm

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]

    total_created = 0

    for tenant_id in tenant_ids:
        try:
            generator = WorkloadSnapshotGenerator(tenant_id)
            result = await generator.execute()
            total_created += result["snapshots_created"]
        except Exception as e:
            logger.error(f"Failed to generate workload snapshots for tenant {tenant_id}: {e}")

    return {"total_snapshots_created": total_created}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_workload_summaries(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_generate_workload_summaries())
        return result
    finally:
        loop.close()


async def run_generate_workload_summaries():
    from app.modules.firms.models import Firm

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Firm.id).where(Firm.is_active == True))
        tenant_ids = [row[0] for row in result.fetchall()]

    total_updated = 0

    for tenant_id in tenant_ids:
        try:
            updater = WorkloadSummaryUpdater(tenant_id)
            result = await updater.execute()
            total_updated += result["summaries_updated"]
        except Exception as e:
            logger.error(f"Failed to update workload summaries for tenant {tenant_id}: {e}")

    return {"total_summaries_updated": total_updated}
