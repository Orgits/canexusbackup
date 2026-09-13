from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
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
    UserWorkloadResponse,
    TeamWorkloadResponse,
    WorkloadDashboardResponse,
)
from app.modules.workload.repository import WorkloadRepository
from app.modules.users.models import User, Team
from app.modules.tasks.models import Task, TaskStatus
from app.modules.matters.models import Matter, MatterStatus
from app.modules.compliance.models import ComplianceCycle, ComplianceStatus
from app.modules.notices.models import Notice, NoticeStatus as NoticeStatusEnum


class WorkloadService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = WorkloadRepository(db)

    # User Availability methods
    async def set_availability(
        self, user_id: UUID, date: date, data: UserAvailabilityCreate, tenant_id: UUID, created_by: UUID
    ) -> UserAvailability:
        return await self.repository.upsert_availability(user_id, date, tenant_id, data, created_by)

    async def get_user_availability(
        self, user_id: UUID, tenant_id: UUID, start_date: date, end_date: date
    ) -> List[UserAvailability]:
        return await self.repository.get_availabilities_for_user(user_id, tenant_id, start_date, end_date)

    async def get_team_availability(
        self, team_id: UUID, tenant_id: UUID, start_date: date, end_date: date
    ) -> List[UserAvailability]:
        return await self.repository.get_availabilities_for_team(team_id, tenant_id, start_date, end_date)

    async def bulk_set_availability(
        self, user_id: UUID, tenant_id: UUID, availabilities: List[Dict[str, Any]], created_by: UUID
    ) -> List[UserAvailability]:
        results = []
        for avail in availabilities:
            date_val = avail.get("date")
            if isinstance(date_val, str):
                date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
            data = UserAvailabilityCreate(
                user_id=user_id,
                date=date_val,
                is_available=avail.get("is_available", True),
                available_hours=avail.get("available_hours", 8.0),
                reason=avail.get("reason"),
                metadata=avail.get("metadata", {}),
            )
            result = await self.set_availability(user_id, date_val, data, tenant_id, created_by)
            results.append(result)
        return results

    # Team Capacity methods
    async def set_team_capacity(
        self, team_id: UUID, period_type: WorkloadPeriod, period_start: date,
        data: TeamCapacityCreate, tenant_id: UUID, created_by: UUID
    ) -> TeamCapacity:
        period_end = data.period_end
        if not period_end:
            # Calculate period_end based on period_type and period_start
            if period_type == WorkloadPeriod.DAILY:
                period_end = period_start
            elif period_type == WorkloadPeriod.WEEKLY:
                period_end = period_start + timedelta(days=6)
            elif period_type == WorkloadPeriod.MONTHLY:
                # Last day of month
                if period_start.month == 12:
                    period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)
            elif period_type == WorkloadPeriod.QUARTERLY:
                quarter_end_month = ((period_start.month - 1) // 3 + 1) * 3
                if quarter_end_month == 12:
                    period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(period_start.year, quarter_end_month + 1, 1) - timedelta(days=1)

        return await self.repository.upsert_capacity(
            team_id, period_type, period_start, tenant_id,
            TeamCapacityCreate(
                team_id=team_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                total_capacity_hours=data.total_capacity_hours,
                allocated_hours=data.allocated_hours,
                available_hours=data.available_hours,
                metadata=data.metadata,
            ),
            created_by
        )

    async def get_team_capacity(
        self, team_id: UUID, tenant_id: UUID, period_type: Optional[WorkloadPeriod] = None
    ) -> List[TeamCapacity]:
        return await self.repository.get_capacities_for_team(team_id, tenant_id, period_type)

    # Workload Calculation methods
    async def calculate_user_workload(
        self, user_id: UUID, tenant_id: UUID, as_of_date: Optional[date] = None
    ) -> UserWorkloadResponse:
        if as_of_date is None:
            as_of_date = date.today()

        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise NotFoundException(detail="User not found")

        # Get team name
        team_name = None
        if user.team_id:
            team_result = await self.db.execute(
                select(Team).where(Team.id == user.team_id)
            )
            team = team_result.scalar_one_or_none()
            if team:
                team_name = team.name

        # Get open tasks
        now = datetime.now(timezone.utc)
        week_start = as_of_date - timedelta(days=as_of_date.weekday())
        week_end = week_start + timedelta(days=6)
        next_week_start = week_end + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)

        # Tasks
        open_tasks_query = select(func.count(Task.id)).where(
            Task.assignee_id == user_id,
            Task.tenant_id == tenant_id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.REWORK]),
        )
        open_tasks = (await self.db.execute(open_tasks_query)).scalar() or 0

        overdue_tasks_query = select(func.count(Task.id)).where(
            Task.assignee_id == user_id,
            Task.tenant_id == tenant_id,
            Task.due_date < now,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.REWORK]),
        )
        overdue_tasks = (await self.db.execute(overdue_tasks_query)).scalar() or 0

        due_this_week_query = select(func.count(Task.id)).where(
            Task.assignee_id == user_id,
            Task.tenant_id == tenant_id,
            Task.due_date >= datetime.combine(week_start, datetime.min.time()),
            Task.due_date <= datetime.combine(week_end, datetime.max.time()),
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.REWORK]),
        )
        due_this_week = (await self.db.execute(due_this_week_query)).scalar() or 0

        due_next_week_query = select(func.count(Task.id)).where(
            Task.assignee_id == user_id,
            Task.tenant_id == tenant_id,
            Task.due_date >= datetime.combine(next_week_start, datetime.min.time()),
            Task.due_date <= datetime.combine(next_week_end, datetime.max.time()),
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.REWORK]),
        )
        due_next_week = (await self.db.execute(due_next_week_query)).scalar() or 0

        # Matters
        assigned_matters_query = select(func.count(Matter.id)).where(
            Matter.responsible_user_id == user_id,
            Matter.tenant_id == tenant_id,
            Matter.status.not_in([MatterStatus.CLOSED, MatterStatus.COMPLETED]),
        )
        assigned_matters = (await self.db.execute(assigned_matters_query)).scalar() or 0

        active_matters_query = select(func.count(Matter.id)).where(
            Matter.responsible_user_id == user_id,
            Matter.tenant_id == tenant_id,
            Matter.status.in_([MatterStatus.IN_PROGRESS, MatterStatus.READY_FOR_REVIEW, MatterStatus.REWORK]),
        )
        active_matters = (await self.db.execute(active_matters_query)).scalar() or 0

        overdue_matters_query = select(func.count(Matter.id)).where(
            Matter.responsible_user_id == user_id,
            Matter.tenant_id == tenant_id,
            Matter.due_date < now,
            Matter.status.not_in([MatterStatus.CLOSED, MatterStatus.COMPLETED]),
        )
        overdue_matters = (await self.db.execute(overdue_matters_query)).scalar() or 0

        # Effort
        effort_query = select(
            func.coalesce(func.sum(Task.estimated_hours), 0),
            func.coalesce(func.sum(Task.actual_hours), 0),
        ).where(
            Task.assignee_id == user_id,
            Task.tenant_id == tenant_id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.REWORK]),
        )
        effort_result = await self.db.execute(effort_query)
        estimated_hours, actual_hours = effort_result.one()

        # Available hours (from availability)
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        week_end_dt = datetime.combine(week_end, datetime.max.time())
        avail_query = select(func.coalesce(func.sum(UserAvailability.available_hours), 0)).where(
            UserAvailability.user_id == user_id,
            UserAvailability.tenant_id == tenant_id,
            UserAvailability.date >= week_start,
            UserAvailability.date <= week_end,
            UserAvailability.is_available == True,
        )
        available_hours = (await self.db.execute(avail_query)).scalar() or 0

        utilization = 0
        if available_hours > 0:
            utilization = min(100, (float(actual_hours or 0) / float(available_hours)) * 100)

        # Compliance
        pending_compliance_query = select(func.count(ComplianceCycle.id)).where(
            ComplianceCycle.assigned_user_id == user_id,
            ComplianceCycle.tenant_id == tenant_id,
            ComplianceCycle.status.in_([ComplianceStatus.PENDING, ComplianceStatus.IN_PROGRESS, ComplianceStatus.READY_FOR_REVIEW]),
        )
        pending_compliance = (await self.db.execute(pending_compliance_query)).scalar() or 0

        overdue_compliance_query = select(func.count(ComplianceCycle.id)).where(
            ComplianceCycle.assigned_user_id == user_id,
            ComplianceCycle.tenant_id == tenant_id,
            ComplianceCycle.due_date < now,
            ComplianceCycle.status.in_([ComplianceStatus.PENDING, ComplianceStatus.IN_PROGRESS, ComplianceStatus.READY_FOR_REVIEW]),
        )
        overdue_compliance = (await self.db.execute(overdue_compliance_query)).scalar() or 0

        # Notices
        pending_notices_query = select(func.count(Notice.id)).where(
            Notice.assignee_id == user_id,
            Notice.tenant_id == tenant_id,
            Notice.status.not_in([NoticeStatusEnum.CLOSED, NoticeStatusEnum.RESPONDED]),
        )
        pending_notices = (await self.db.execute(pending_notices_query)).scalar() or 0

        overdue_notices_query = select(func.count(Notice.id)).where(
            Notice.assignee_id == user_id,
            Notice.tenant_id == tenant_id,
            Notice.response_deadline < now,
            Notice.status.not_in([NoticeStatusEnum.CLOSED, NoticeStatusEnum.RESPONDED]),
        )
        overdue_notices = (await self.db.execute(overdue_notices_query)).scalar() or 0

        is_overloaded = utilization > 90 or overdue_tasks > 5 or overdue_matters > 3

        return UserWorkloadResponse(
            user_id=user.id,
            user_name=user.full_name or user.email,
            user_email=user.email,
            team_id=user.team_id,
            team_name=team_name,
            open_tasks=open_tasks,
            overdue_tasks=overdue_tasks,
            due_this_week=due_this_week,
            due_next_week=due_next_week,
            assigned_matters=assigned_matters,
            active_matters=active_matters,
            overdue_matters=overdue_matters,
            estimated_hours=float(estimated_hours or 0),
            actual_hours=float(actual_hours or 0),
            available_hours=float(available_hours or 0),
            utilization_percentage=utilization,
            pending_compliance=pending_compliance,
            overdue_compliance=overdue_compliance,
            pending_notices=pending_notices,
            overdue_notices=overdue_notices,
            is_overloaded=is_overloaded,
        )

    async def calculate_team_workload(
        self, team_id: UUID, tenant_id: UUID, as_of_date: Optional[date] = None
    ) -> TeamWorkloadResponse:
        if as_of_date is None:
            as_of_date = date.today()

        # Get team
        team_result = await self.db.execute(
            select(Team).where(Team.id == team_id, Team.tenant_id == tenant_id)
        )
        team = team_result.scalar_one_or_none()
        if not team:
            raise NotFoundException(detail="Team not found")

        # Get team members
        members_result = await self.db.execute(
            select(User).where(User.team_id == team_id, User.tenant_id == tenant_id)
        )
        members = members_result.scalars().all()

        member_workloads = []
        total_open_tasks = 0
        total_overdue_tasks = 0
        total_due_this_week = 0
        total_due_next_week = 0
        total_assigned_matters = 0
        total_active_matters = 0
        total_overdue_matters = 0
        total_estimated_hours = 0
        total_actual_hours = 0
        total_available_hours = 0
        total_pending_compliance = 0
        total_overdue_compliance = 0
        total_pending_notices = 0
        total_overdue_notices = 0

        for member in members:
            workload = await self.calculate_user_workload(member.id, tenant_id, as_of_date)
            member_workloads.append(workload)

            total_open_tasks += workload.open_tasks
            total_overdue_tasks += workload.overdue_tasks
            total_due_this_week += workload.due_this_week
            total_due_next_week += workload.due_next_week
            total_assigned_matters += workload.assigned_matters
            total_active_matters += workload.active_matters
            total_overdue_matters += workload.overdue_matters
            total_estimated_hours += workload.estimated_hours
            total_actual_hours += workload.actual_hours
            total_available_hours += workload.available_hours
            total_pending_compliance += workload.pending_compliance
            total_overdue_compliance += workload.overdue_compliance
            total_pending_notices += workload.pending_notices
            total_overdue_notices += workload.overdue_notices

        avg_utilization = 0
        if total_available_hours > 0:
            avg_utilization = min(100, (total_actual_hours / total_available_hours) * 100)

        # Get team capacity
        period_type = WorkloadPeriod.WEEKLY
        week_start = as_of_date - timedelta(days=as_of_date.weekday())
        capacities = await self.repository.get_capacities_for_team(team_id, tenant_id, period_type)
        current_capacity = None
        for cap in capacities:
            if cap.period_start <= week_start <= cap.period_end:
                current_capacity = cap
                break

        return TeamWorkloadResponse(
            team_id=team.id,
            team_name=team.name,
            total_members=len(members),
            open_tasks=total_open_tasks,
            overdue_tasks=total_overdue_tasks,
            due_this_week=total_due_this_week,
            due_next_week=total_due_next_week,
            assigned_matters=total_assigned_matters,
            active_matters=total_active_matters,
            overdue_matters=total_overdue_matters,
            total_estimated_hours=total_estimated_hours,
            total_actual_hours=total_actual_hours,
            total_available_hours=total_available_hours,
            avg_utilization_percentage=avg_utilization,
            pending_compliance=total_pending_compliance,
            overdue_compliance=total_overdue_compliance,
            pending_notices=total_pending_notices,
            overdue_notices=total_overdue_notices,
            total_capacity_hours=current_capacity.total_capacity_hours if current_capacity else 0,
            allocated_hours=current_capacity.allocated_hours if current_capacity else 0,
            available_hours=current_capacity.available_hours if current_capacity else 0,
            members=member_workloads,
        )

    async def get_workload_dashboard(
        self, tenant_id: UUID, user_id: Optional[UUID] = None, team_id: Optional[UUID] = None,
        as_of_date: Optional[date] = None
    ) -> WorkloadDashboardResponse:
        if as_of_date is None:
            as_of_date = date.today()

        # Get or create summary
        summary = await self.repository.get_summary(as_of_date, tenant_id, user_id, team_id)
        if not summary:
            # Create new summary
            if user_id:
                workload = await self.calculate_user_workload(user_id, tenant_id, as_of_date)
                summary = WorkloadSummary(
                    user_id=user_id,
                    summary_date=as_of_date,
                    current_open_tasks=workload.open_tasks,
                    current_overdue_tasks=workload.overdue_tasks,
                    current_assigned_matters=workload.assigned_matters,
                    current_active_matters=workload.active_matters,
                    tasks_due_today=0,  # Would need separate query
                    tasks_due_this_week=workload.due_this_week,
                    tasks_due_next_week=workload.due_next_week,
                    matters_due_this_week=0,
                    matters_due_next_week=0,
                    estimated_hours_this_week=workload.estimated_hours,
                    actual_hours_this_week=workload.actual_hours,
                    available_hours_this_week=workload.available_hours,
                    pending_compliance_this_week=workload.pending_compliance,
                    overdue_compliance=workload.overdue_compliance,
                    pending_notices=workload.pending_notices,
                    overdue_notices=workload.overdue_notices,
                    capacity_utilization=workload.utilization_percentage,
                    is_overloaded=workload.is_overloaded,
                    tenant_id=tenant_id,
                )
            elif team_id:
                workload = await self.calculate_team_workload(team_id, tenant_id, as_of_date)
                summary = WorkloadSummary(
                    team_id=team_id,
                    summary_date=as_of_date,
                    current_open_tasks=workload.open_tasks,
                    current_overdue_tasks=workload.overdue_tasks,
                    current_assigned_matters=workload.assigned_matters,
                    current_active_matters=workload.active_matters,
                    tasks_due_today=0,
                    tasks_due_this_week=workload.due_this_week,
                    tasks_due_next_week=workload.due_next_week,
                    matters_due_this_week=0,
                    matters_due_next_week=0,
                    estimated_hours_this_week=workload.total_estimated_hours,
                    actual_hours_this_week=workload.total_actual_hours,
                    available_hours_this_week=workload.total_available_hours,
                    pending_compliance_this_week=workload.pending_compliance,
                    overdue_compliance=workload.overdue_compliance,
                    pending_notices=workload.pending_notices,
                    overdue_notices=workload.overdue_notices,
                    capacity_utilization=workload.avg_utilization_percentage,
                    is_overloaded=workload.avg_utilization_percentage > 90,
                    tenant_id=tenant_id,
                )
            else:
                # Firm-wide summary - would need aggregate queries
                summary = WorkloadSummary(
                    summary_date=as_of_date,
                    tenant_id=tenant_id,
                )

            summary = await self.repository.upsert_summary(summary)

        # Get user workloads
        user_workloads = []
        if user_id:
            user_workloads = [await self.calculate_user_workload(user_id, tenant_id, as_of_date)]
        elif team_id:
            team_workload = await self.calculate_team_workload(team_id, tenant_id, as_of_date)
            user_workloads = team_workload.members
        else:
            # Get all users for firm
            users_result = await self.db.execute(
                select(User).where(User.tenant_id == tenant_id)
            )
            users = users_result.scalars().all()
            for user in users:
                user_workloads.append(await self.calculate_user_workload(user.id, tenant_id, as_of_date))

        # Get team workloads
        team_workloads = []
        if team_id:
            team_workloads = [await self.calculate_team_workload(team_id, tenant_id, as_of_date)]
        else:
            teams_result = await self.db.execute(
                select(Team).where(Team.tenant_id == tenant_id)
            )
            teams = teams_result.scalars().all()
            for team in teams:
                team_workloads.append(await self.calculate_team_workload(team.id, tenant_id, as_of_date))

        return WorkloadDashboardResponse(
            summary=summary,
            user_workloads=user_workloads,
            team_workloads=team_workloads,
        )

    # Snapshot methods
    async def generate_snapshots(
        self, tenant_id: UUID, snapshot_date: Optional[date] = None,
        period_type: WorkloadPeriod = WorkloadPeriod.DAILY
    ) -> List[WorkloadSnapshot]:
        if snapshot_date is None:
            snapshot_date = date.today()

        snapshots = []

        # User snapshots
        users_result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id)
        )
        users = users_result.scalars().all()

        for user in users:
            workload = await self.calculate_user_workload(user.id, tenant_id, snapshot_date)
            snapshot = WorkloadSnapshot(
                user_id=user.id,
                team_id=user.team_id,
                snapshot_date=snapshot_date,
                period_type=period_type,
                open_tasks=workload.open_tasks,
                overdue_tasks=workload.overdue_tasks,
                due_this_week=workload.due_this_week,
                due_next_week=workload.due_next_week,
                assigned_matters=workload.assigned_matters,
                active_matters=workload.active_matters,
                overdue_matters=workload.overdue_matters,
                estimated_hours=workload.estimated_hours,
                actual_hours=workload.actual_hours,
                available_hours=workload.available_hours,
                utilization_percentage=workload.utilization_percentage,
                pending_compliance=workload.pending_compliance,
                overdue_compliance=workload.overdue_compliance,
                pending_notices=workload.pending_notices,
                overdue_notices=workload.overdue_notices,
                tenant_id=tenant_id,
            )
            snapshots.append(await self.repository.upsert_snapshot(snapshot))

        # Team snapshots
        teams_result = await self.db.execute(
            select(Team).where(Team.tenant_id == tenant_id)
        )
        teams = teams_result.scalars().all()

        for team in teams:
            workload = await self.calculate_team_workload(team.id, tenant_id, snapshot_date)
            snapshot = WorkloadSnapshot(
                team_id=team.id,
                snapshot_date=snapshot_date,
                period_type=period_type,
                open_tasks=workload.open_tasks,
                overdue_tasks=workload.overdue_tasks,
                due_this_week=workload.due_this_week,
                due_next_week=workload.due_next_week,
                assigned_matters=workload.assigned_matters,
                active_matters=workload.active_matters,
                overdue_matters=workload.overdue_matters,
                estimated_hours=workload.total_estimated_hours,
                actual_hours=workload.total_actual_hours,
                available_hours=workload.total_available_hours,
                utilization_percentage=workload.avg_utilization_percentage,
                pending_compliance=workload.pending_compliance,
                overdue_compliance=workload.overdue_compliance,
                pending_notices=workload.pending_notices,
                overdue_notices=workload.overdue_notices,
                tenant_id=tenant_id,
            )
            snapshots.append(await self.repository.upsert_snapshot(snapshot))

        return snapshots