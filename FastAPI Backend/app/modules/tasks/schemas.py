from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    REWORK = "rework"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskBase(BaseModel):
    client_id: UUID | None = None
    matter_id: UUID | None = None
    parent_task_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    task_number: str | None = Field(None, max_length=100)
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    team_id: UUID | None = None
    due_date: datetime | None = None
    start_date: datetime | None = None
    estimated_hours: float | None = None
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_communication_id: UUID | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    task_number: str | None = Field(None, max_length=100)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    assignee_id: UUID | None = None
    team_id: UUID | None = None
    due_date: datetime | None = None
    start_date: datetime | None = None
    completed_date: datetime | None = None
    estimated_hours: float | None = None
    checklist: list[dict[str, Any]] | None = None
    dependencies: list[UUID] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class TaskResponse(TaskBase):
    id: UUID
    status: TaskStatus
    reporter_id: UUID | None = None
    actual_hours: float | None = None
    completed_date: datetime | None = None
    progress_percentage: int
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskAction(BaseModel):
    action: str
    assignee_id: UUID | None = None
    status: TaskStatus | None = None
    notes: str | None = None
