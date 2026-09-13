from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.modules.workload.models import (
    UserAvailability,
    TeamCapacity,
    WorkloadSnapshot,
    WorkloadSummary,
    WorkloadPeriod,
)
from app.modules.workload.schemas import (
    UserAvailabilityCreate,
    UserAvailabilityUpdate,
    TeamCapacityCreate,
    TeamCapacityUpdate,
    WorkloadSnapshotCreate,
    WorkloadSummaryCreate,
)


class WorkloadRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # User Availability methods
    async def create_availability(self, availability: UserAvailability) -> UserAvailability:
        self.db.add(availability)
        await self.db.flush()
        await self.db.refresh(availability)
        return availability

    async def get_availability(self, user_id: UUID, date: date, tenant_id: UUID) -> Optional[UserAvailability]:
        result = await self.db.execute(
            select(UserAvailability).where(
                UserAvailability.user_id == user_id,
                UserAvailability.date == date,
                UserAvailability.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_availabilities_for_user(
        self, user_id: UUID, tenant_id: UUID, start_date: date, end_date: date
    ) -> List[UserAvailability]:
        result = await self.db.execute(
            select(UserAvailability).where(
                UserAvailability.user_id == user_id,
                UserAvailability.tenant_id == tenant_id,
                UserAvailability.date >= start_date,
                UserAvailability.date <= end_date,
            ).order_by(UserAvailability.date)
        )
        return list(result.scalars().all())

    async def get_availabilities_for_team(
        self, team_id: UUID, tenant_id: UUID, start_date: date, end_date: date
    ) -> List[UserAvailability]:
        from app.modules.users.models import User
        result = await self.db.execute(
            select(UserAvailability)
            .join(User, UserAvailability.user_id == User.id)
            .where(
                User.team_id == team_id,
                UserAvailability.tenant_id == tenant_id,
                UserAvailability.date >= start_date,
                UserAvailability.date <= end_date,
            ).order_by(UserAvailability.date)
        )
        return list(result.scalars().all())

    async def upsert_availability(
        self, user_id: UUID, date: date, tenant_id: UUID, data: UserAvailabilityCreate, created_by: UUID
    ) -> UserAvailability:
        existing = await self.get_availability(user_id, date, tenant_id)
        if existing:
            existing.is_available = data.is_available
            existing.available_hours = data.available_hours
            existing.reason = data.reason
            existing.metadata = data.metadata
            existing.updated_by = created_by
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            availability = UserAvailability(
                user_id=user_id,
                date=date,
                **data.model_dump(exclude={"user_id", "date"}),
                tenant_id=tenant_id,
                created_by=created_by,
            )
            return await self.create_availability(availability)

    async def update_availability(self, availability: UserAvailability) -> UserAvailability:
        await self.db.flush()
        await self.db.refresh(availability)
        return availability

    # Team Capacity methods
    async def create_capacity(self, capacity: TeamCapacity) -> TeamCapacity:
        self.db.add(capacity)
        await self.db.flush()
        await self.db.refresh(capacity)
        return capacity

    async def get_capacity(
        self, team_id: UUID, period_type: WorkloadPeriod, period_start: date, tenant_id: UUID
    ) -> Optional[TeamCapacity]:
        result = await self.db.execute(
            select(TeamCapacity).where(
                TeamCapacity.team_id == team_id,
                TeamCapacity.period_type == period_type,
                TeamCapacity.period_start == period_start,
                TeamCapacity.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_capacities_for_team(
        self, team_id: UUID, tenant_id: UUID, period_type: Optional[WorkloadPeriod] = None
    ) -> List[TeamCapacity]:
        query = select(TeamCapacity).where(
            TeamCapacity.team_id == team_id,
            TeamCapacity.tenant_id == tenant_id,
        )
        if period_type:
            query = query.where(TeamCapacity.period_type == period_type)
        query = query.order_by(TeamCapacity.period_start)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def upsert_capacity(
        self, team_id: UUID, period_type: WorkloadPeriod, period_start: date, tenant_id: UUID,
        data: TeamCapacityCreate, created_by: UUID
    ) -> TeamCapacity:
        existing = await self.get_capacity(team_id, period_type, period_start, tenant_id)
        if existing:
            existing.total_capacity_hours = data.total_capacity_hours
            existing.allocated_hours = data.allocated_hours
            existing.available_hours = data.available_hours
            existing.metadata = data.metadata
            existing.updated_by = created_by
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            capacity = TeamCapacity(
                team_id=team_id,
                period_type=period_type,
                period_start=period_start,
                period_end=data.period_end,
                **data.model_dump(exclude={"team_id", "period_type", "period_start", "period_end"}),
                tenant_id=tenant_id,
                created_by=created_by,
            )
            return await self.create_capacity(capacity)

    async def update_capacity(self, capacity: TeamCapacity) -> TeamCapacity:
        await self.db.flush()
        await self.db.refresh(capacity)
        return capacity

    # Workload Snapshot methods
    async def create_snapshot(self, snapshot: WorkloadSnapshot) -> WorkloadSnapshot:
        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_snapshot(
        self,
        snapshot_date: date,
        period_type: WorkloadPeriod,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
    ) -> Optional[WorkloadSnapshot]:
        query = select(WorkloadSnapshot).where(
            WorkloadSnapshot.snapshot_date == snapshot_date,
            WorkloadSnapshot.period_type == period_type,
            WorkloadSnapshot.tenant_id == tenant_id,
        )
        if user_id:
            query = query.where(WorkloadSnapshot.user_id == user_id)
        if team_id:
            query = query.where(WorkloadSnapshot.team_id == team_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_snapshots_for_user(
        self, user_id: UUID, tenant_id: UUID, start_date: date, end_date: date,
        period_type: Optional[WorkloadPeriod] = None
    ) -> List[WorkloadSnapshot]:
        query = select(WorkloadSnapshot).where(
            WorkloadSnapshot.user_id == user_id,
            WorkloadSnapshot.tenant_id == tenant_id,
            WorkloadSnapshot.snapshot_date >= start_date,
            WorkloadSnapshot.snapshot_date <= end_date,
        )
        if period_type:
            query = query.where(WorkloadSnapshot.period_type == period_type)
        query = query.order_by(WorkloadSnapshot.snapshot_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_snapshots_for_team(
        self, team_id: UUID, tenant_id: UUID, start_date: date, end_date: date,
        period_type: Optional[WorkloadPeriod] = None
    ) -> List[WorkloadSnapshot]:
        query = select(WorkloadSnapshot).where(
            WorkloadSnapshot.team_id == team_id,
            WorkloadSnapshot.tenant_id == tenant_id,
            WorkloadSnapshot.snapshot_date >= start_date,
            WorkloadSnapshot.snapshot_date <= end_date,
        )
        if period_type:
            query = query.where(WorkloadSnapshot.period_type == period_type)
        query = query.order_by(WorkloadSnapshot.snapshot_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def upsert_snapshot(
        self, snapshot: WorkloadSnapshot
    ) -> WorkloadSnapshot:
        existing = await self.get_snapshot(
            snapshot.snapshot_date, snapshot.period_type, snapshot.tenant_id,
            snapshot.user_id, snapshot.team_id
        )
        if existing:
            for field, value in snapshot.__dict__.items():
                if not field.startswith('_') and field not in ['id', 'created_at', 'created_by', 'tenant_id']:
                    setattr(existing, field, value)
            existing.updated_by = snapshot.updated_by
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            return await self.create_snapshot(snapshot)

    # Workload Summary methods
    async def create_summary(self, summary: WorkloadSummary) -> WorkloadSummary:
        self.db.add(summary)
        await self.db.flush()
        await self.db.refresh(summary)
        return summary

    async def get_summary(
        self, summary_date: date, tenant_id: UUID, user_id: Optional[UUID] = None, team_id: Optional[UUID] = None
    ) -> Optional[WorkloadSummary]:
        query = select(WorkloadSummary).where(
            WorkloadSummary.summary_date == summary_date,
            WorkloadSummary.tenant_id == tenant_id,
        )
        if user_id:
            query = query.where(WorkloadSummary.user_id == user_id)
        if team_id:
            query = query.where(WorkloadSummary.team_id == team_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_summaries_for_user(
        self, user_id: UUID, tenant_id: UUID, start_date: date, end_date: date
    ) -> List[WorkloadSummary]:
        result = await self.db.execute(
            select(WorkloadSummary).where(
                WorkloadSummary.user_id == user_id,
                WorkloadSummary.tenant_id == tenant_id,
                WorkloadSummary.summary_date >= start_date,
                WorkloadSummary.summary_date <= end_date,
            ).order_by(WorkloadSummary.summary_date)
        )
        return list(result.scalars().all())

    async def get_summaries_for_team(
        self, team_id: UUID, tenant_id: UUID, start_date: date, end_date: date
    ) -> List[WorkloadSummary]:
        result = await self.db.execute(
            select(WorkloadSummary).where(
                WorkloadSummary.team_id == team_id,
                WorkloadSummary.tenant_id == tenant_id,
                WorkloadSummary.summary_date >= start_date,
                WorkloadSummary.summary_date <= end_date,
            ).order_by(WorkloadSummary.summary_date)
        )
        return list(result.scalars().all())

    async def get_all_summaries(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[WorkloadSummary], int]:
        query = select(WorkloadSummary).where(WorkloadSummary.tenant_id == tenant_id)
        count_query = select(func.count(WorkloadSummary.id)).where(WorkloadSummary.tenant_id == tenant_id)

        if user_id:
            query = query.where(WorkloadSummary.user_id == user_id)
            count_query = count_query.where(WorkloadSummary.user_id == user_id)

        if team_id:
            query = query.where(WorkloadSummary.team_id == team_id)
            count_query = count_query.where(WorkloadSummary.team_id == team_id)

        if start_date:
            query = query.where(WorkloadSummary.summary_date >= start_date)
            count_query = count_query.where(WorkloadSummary.summary_date >= start_date)

        if end_date:
            query = query.where(WorkloadSummary.summary_date <= end_date)
            count_query = count_query.where(WorkloadSummary.summary_date <= end_date)

        query = query.order_by(WorkloadSummary.summary_date.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(WorkloadSummary.user),
                selectinload(WorkloadSummary.team),
            )
        )
        summaries = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(summaries), total

    async def upsert_summary(self, summary: WorkloadSummary) -> WorkloadSummary:
        existing = await self.get_summary(
            summary.summary_date, summary.tenant_id, summary.user_id, summary.team_id
        )
        if existing:
            for field, value in summary.__dict__.items():
                if not field.startswith('_') and field not in ['id', 'created_at', 'created_by', 'tenant_id']:
                    setattr(existing, field, value)
            existing.updated_by = summary.updated_by
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            return await self.create_summary(summary)