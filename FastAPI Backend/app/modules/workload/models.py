import uuid
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import (
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    func,
    Enum,
    ARRAY,
    Index,
    UniqueConstraint,
    Numeric,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User, Team
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task


class WorkloadPeriod(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class UserAvailability(Base, TenantBaseModelMixin):
    __tablename__ = "user_availability"
    __table_args__ = (
        Index("ix_user_availability_tenant_user", "tenant_id", "user_id"),
        Index("ix_user_availability_tenant_date", "tenant_id", "date"),
        UniqueConstraint("tenant_id", "user_id", "date", name="uq_tenant_user_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    available_hours: Mapped[float] = mapped_column(Numeric(4, 2), default=8.0, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", lazy="selectin")


class TeamCapacity(Base, TenantBaseModelMixin):
    __tablename__ = "team_capacity"
    __table_args__ = (
        Index("ix_team_capacity_tenant_team", "tenant_id", "team_id"),
        Index("ix_team_capacity_tenant_period", "tenant_id", "period_type", "period_start"),
        UniqueConstraint("tenant_id", "team_id", "period_type", "period_start", name="uq_tenant_team_period"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period_type: Mapped[WorkloadPeriod] = mapped_column(Enum(WorkloadPeriod), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    total_capacity_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    allocated_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    available_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    team: Mapped["Team"] = relationship("Team", lazy="selectin")


class WorkloadSnapshot(Base, TenantBaseModelMixin):
    __tablename__ = "workload_snapshots"
    __table_args__ = (
        Index("ix_workload_snapshots_tenant_user", "tenant_id", "user_id"),
        Index("ix_workload_snapshots_tenant_team", "tenant_id", "team_id"),
        Index("ix_workload_snapshots_tenant_date", "tenant_id", "snapshot_date"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_type: Mapped[WorkloadPeriod] = mapped_column(Enum(WorkloadPeriod), nullable=False)

    # Task metrics
    open_tasks: Mapped[int] = mapped_column(default=0, nullable=False)
    overdue_tasks: Mapped[int] = mapped_column(default=0, nullable=False)
    due_this_week: Mapped[int] = mapped_column(default=0, nullable=False)
    due_next_week: Mapped[int] = mapped_column(default=0, nullable=False)

    # Matter metrics
    assigned_matters: Mapped[int] = mapped_column(default=0, nullable=False)
    active_matters: Mapped[int] = mapped_column(default=0, nullable=False)
    overdue_matters: Mapped[int] = mapped_column(default=0, nullable=False)

    # Effort metrics
    estimated_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    actual_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    available_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    utilization_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)

    # Compliance metrics
    pending_compliance: Mapped[int] = mapped_column(default=0, nullable=False)
    overdue_compliance: Mapped[int] = mapped_column(default=0, nullable=False)

    # Notice metrics
    pending_notices: Mapped[int] = mapped_column(default=0, nullable=False)
    overdue_notices: Mapped[int] = mapped_column(default=0, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")


class WorkloadSummary(Base, TenantBaseModelMixin):
    __tablename__ = "workload_summaries"
    __table_args__ = (
        Index("ix_workload_summaries_tenant_user", "tenant_id", "user_id"),
        Index("ix_workload_summaries_tenant_team", "tenant_id", "team_id"),
        Index("ix_workload_summaries_tenant_date", "tenant_id", "summary_date"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Current workload
    current_open_tasks: Mapped[int] = mapped_column(default=0, nullable=False)
    current_overdue_tasks: Mapped[int] = mapped_column(default=0, nullable=False)
    current_assigned_matters: Mapped[int] = mapped_column(default=0, nullable=False)
    current_active_matters: Mapped[int] = mapped_column(default=0, nullable=False)

    # Upcoming workload
    tasks_due_today: Mapped[int] = mapped_column(default=0, nullable=False)
    tasks_due_this_week: Mapped[int] = mapped_column(default=0, nullable=False)
    tasks_due_next_week: Mapped[int] = mapped_column(default=0, nullable=False)
    matters_due_this_week: Mapped[int] = mapped_column(default=0, nullable=False)
    matters_due_next_week: Mapped[int] = mapped_column(default=0, nullable=False)

    # Effort tracking
    estimated_hours_this_week: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    actual_hours_this_week: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    available_hours_this_week: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    # Compliance
    pending_compliance_this_week: Mapped[int] = mapped_column(default=0, nullable=False)
    overdue_compliance: Mapped[int] = mapped_column(default=0, nullable=False)

    # Notices
    pending_notices: Mapped[int] = mapped_column(default=0, nullable=False)
    overdue_notices: Mapped[int] = mapped_column(default=0, nullable=False)

    # Capacity
    capacity_utilization: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    is_overloaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")