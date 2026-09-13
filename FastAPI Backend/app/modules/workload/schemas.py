from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict


class UserAvailabilityBase(BaseModel):
    user_id: UUID
    date: date
    is_available: bool = True
    available_hours: float = Field(default=8.0, ge=0, le=24)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class UserAvailabilityCreate(UserAvailabilityBase):
    pass


class UserAvailabilityUpdate(BaseModel):
    is_available: Optional[bool] = None
    available_hours: Optional[float] = Field(None, ge=0, le=24)
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UserAvailabilityResponse(UserAvailabilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    user: Optional["UserResponse"] = None


class TeamCapacityBase(BaseModel):
    team_id: UUID
    period_type: str = Field(..., pattern="^(daily|weekly|monthly|quarterly)$")
    period_start: date
    period_end: date
    total_capacity_hours: float = Field(default=0, ge=0)
    allocated_hours: float = Field(default=0, ge=0)
    available_hours: float = Field(default=0, ge=0)
    metadata: Dict[str, Any] = {}


class TeamCapacityCreate(TeamCapacityBase):
    pass


class TeamCapacityUpdate(BaseModel):
    total_capacity_hours: Optional[float] = Field(None, ge=0)
    allocated_hours: Optional[float] = Field(None, ge=0)
    available_hours: Optional[float] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None


class TeamCapacityResponse(TeamCapacityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    team: Optional["TeamResponse"] = None


class WorkloadSnapshotBase(BaseModel):
    user_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    snapshot_date: date
    period_type: str = Field(..., pattern="^(daily|weekly|monthly|quarterly)$")

    open_tasks: int = 0
    overdue_tasks: int = 0
    due_this_week: int = 0
    due_next_week: int = 0

    assigned_matters: int = 0
    active_matters: int = 0
    overdue_matters: int = 0

    estimated_hours: float = Field(default=0, ge=0)
    actual_hours: float = Field(default=0, ge=0)
    available_hours: float = Field(default=0, ge=0)
    utilization_percentage: float = Field(default=0, ge=0, le=100)

    pending_compliance: int = 0
    overdue_compliance: int = 0

    pending_notices: int = 0
    overdue_notices: int = 0

    metadata: Dict[str, Any] = {}


class WorkloadSnapshotCreate(WorkloadSnapshotBase):
    pass


class WorkloadSnapshotResponse(WorkloadSnapshotBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    user: Optional["UserResponse"] = None
    team: Optional["TeamResponse"] = None


class WorkloadSummaryBase(BaseModel):
    user_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    summary_date: date

    current_open_tasks: int = 0
    current_overdue_tasks: int = 0
    current_assigned_matters: int = 0
    current_active_matters: int = 0

    tasks_due_today: int = 0
    tasks_due_this_week: int = 0
    tasks_due_next_week: int = 0
    matters_due_this_week: int = 0
    matters_due_next_week: int = 0

    estimated_hours_this_week: float = Field(default=0, ge=0)
    actual_hours_this_week: float = Field(default=0, ge=0)
    available_hours_this_week: float = Field(default=0, ge=0)

    pending_compliance_this_week: int = 0
    overdue_compliance: int = 0

    pending_notices: int = 0
    overdue_notices: int = 0

    capacity_utilization: float = Field(default=0, ge=0, le=100)
    is_overloaded: bool = False

    metadata: Dict[str, Any] = {}


class WorkloadSummaryCreate(WorkloadSummaryBase):
    pass


class WorkloadSummaryResponse(WorkloadSummaryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    user: Optional["UserResponse"] = None
    team: Optional["TeamResponse"] = None


class WorkloadSummaryListResponse(BaseModel):
    items: List[WorkloadSummaryResponse]
    total: int
    page: int
    page_size: int


class UserWorkloadResponse(BaseModel):
    user_id: UUID
    user_name: str
    user_email: str
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None

    open_tasks: int = 0
    overdue_tasks: int = 0
    due_this_week: int = 0
    due_next_week: int = 0

    assigned_matters: int = 0
    active_matters: int = 0
    overdue_matters: int = 0

    estimated_hours: float = 0
    actual_hours: float = 0
    available_hours: float = 0
    utilization_percentage: float = 0

    pending_compliance: int = 0
    overdue_compliance: int = 0

    pending_notices: int = 0
    overdue_notices: int = 0

    is_overloaded: bool = False


class TeamWorkloadResponse(BaseModel):
    team_id: UUID
    team_name: str

    total_members: int = 0
    open_tasks: int = 0
    overdue_tasks: int = 0
    due_this_week: int = 0
    due_next_week: int = 0

    assigned_matters: int = 0
    active_matters: int = 0
    overdue_matters: int = 0

    total_estimated_hours: float = 0
    total_actual_hours: float = 0
    total_available_hours: float = 0
    avg_utilization_percentage: float = 0

    pending_compliance: int = 0
    overdue_compliance: int = 0

    pending_notices: int = 0
    overdue_notices: int = 0

    total_capacity_hours: float = 0
    allocated_hours: float = 0
    available_hours: float = 0

    members: List[UserWorkloadResponse] = []


class WorkloadDashboardResponse(BaseModel):
    summary: WorkloadSummaryResponse
    user_workloads: List[UserWorkloadResponse] = []
    team_workloads: List[TeamWorkloadResponse] = []


from app.modules.users.schemas import UserResponse, TeamResponse