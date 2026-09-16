import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import Team, User


class AssignableEntityType(str, PyEnum):
    MATTER = "matter"
    TASK = "task"
    COMPLIANCE_CYCLE = "compliance_cycle"
    NOTICE = "notice"
    REVIEW = "review"


class AssignmentAction(str, PyEnum):
    ASSIGN = "assign"
    REASSIGN = "reassign"
    UNASSIGN = "unassign"
    TEAM_ASSIGN = "team_assign"
    ESCALATE = "escalate"
    DE_ESCALATE = "de_escalate"


class EscalationReason(str, PyEnum):
    OVERDUE = "overdue"
    WORKLOAD = "workload"
    EXPERTISE = "expertise"
    UNAVAILABLE = "unavailable"
    PRIORITY = "priority"
    SLA_BREACH = "sla_breach"
    MANUAL = "manual"


class Assignment(Base, TenantBaseModelMixin):
    __tablename__ = "assignments"
    __table_args__ = (
        Index("ix_assignments_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_assignments_tenant_user", "tenant_id", "user_id"),
        Index("ix_assignments_tenant_team", "tenant_id", "team_id"),
        Index("ix_assignments_tenant_status", "tenant_id", "is_active"),
    )

    entity_type: Mapped[AssignableEntityType] = mapped_column(Enum(AssignableEntityType), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
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

    assigned_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unassigned_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    unassign_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    team: Mapped[Optional["Team"]] = relationship("Team", lazy="selectin")
    assigned_by: Mapped["User"] = relationship("User", foreign_keys=[assigned_by_id], lazy="selectin")
    history: Mapped[list["AssignmentHistory"]] = relationship("AssignmentHistory", lazy="dynamic")


class AssignmentHistory(Base, TenantBaseModelMixin):
    __tablename__ = "assignment_history"
    __table_args__ = (
        Index("ix_assignment_history_tenant_assignment", "tenant_id", "assignment_id"),
        Index("ix_assignment_history_tenant_actor", "tenant_id", "actor_id"),
        Index("ix_assignment_history_created_at", "created_at"),
    )

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action: Mapped[AssignmentAction] = mapped_column(Enum(AssignmentAction), nullable=False)
    from_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    to_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    from_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    to_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    assignment: Mapped["Assignment"] = relationship("Assignment", back_populates="history")
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id], lazy="selectin")


class Escalation(Base, TenantBaseModelMixin):
    __tablename__ = "escalations"
    __table_args__ = (
        Index("ix_escalations_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_escalations_tenant_from", "tenant_id", "escalated_from_id"),
        Index("ix_escalations_tenant_to", "tenant_id", "escalated_to_id"),
        Index("ix_escalations_tenant_status", "tenant_id", "is_resolved"),
    )

    entity_type: Mapped[AssignableEntityType] = mapped_column(Enum(AssignableEntityType), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    escalated_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    escalated_to_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    escalated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    reason: Mapped[EscalationReason] = mapped_column(Enum(EscalationReason), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    previous_assignee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    previous_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    escalated_from: Mapped[Optional["User"]] = relationship("User", foreign_keys=[escalated_from_id], lazy="selectin")
    escalated_to: Mapped["User"] = relationship("User", foreign_keys=[escalated_to_id], lazy="selectin")
    escalated_by: Mapped["User"] = relationship("User", foreign_keys=[escalated_by_id], lazy="selectin")
