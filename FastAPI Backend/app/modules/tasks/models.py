import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.clients.models import Client
    from app.modules.communications.models import Communication
    from app.modules.documents.models import Document
    from app.modules.matters.models import Matter
    from app.modules.users.models import Team, User


class TaskStatus(str, PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    REWORK = "rework"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class TaskPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class Task(Base, TenantBaseModelMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_tenant_client", "tenant_id", "client_id"),
        Index("ix_tasks_tenant_matter", "tenant_id", "matter_id"),
        Index("ix_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_tasks_tenant_assignee", "tenant_id", "assignee_id"),
        Index("ix_tasks_tenant_due_date", "tenant_id", "due_date"),
        Index("ix_tasks_tenant_parent", "tenant_id", "parent_task_id"),
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    matter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_number: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)

    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    compliance_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_cycles.id", ondelete="SET NULL"),
        nullable=True,
    )

    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    estimated_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    actual_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, default=0)

    progress_percentage: Mapped[int] = mapped_column(default=0, nullable=False)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    dependencies: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    source_communication_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communications.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    client: Mapped[Optional["Client"]] = relationship("Client", lazy="selectin")
    matter: Mapped[Optional["Matter"]] = relationship("Matter", lazy="selectin")
    parent_task: Mapped[Optional["Task"]] = relationship("Task", remote_side="Task.id", lazy="selectin")
    subtasks: Mapped[list["Task"]] = relationship("Task", lazy="dynamic")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id], lazy="selectin")
    team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")
    reporter: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reporter_id], lazy="selectin")
    compliance_cycle: Mapped[Optional["ComplianceCycle"]] = relationship("ComplianceCycle", foreign_keys=[compliance_cycle_id], lazy="selectin")
    documents: Mapped[list["Document"]] = relationship("Document", lazy="dynamic")
    source_communication: Mapped[Optional["Communication"]] = relationship("Communication", foreign_keys=[source_communication_id], lazy="selectin")
