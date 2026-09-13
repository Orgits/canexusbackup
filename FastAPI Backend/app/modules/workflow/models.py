import uuid
from datetime import datetime, timezone
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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class WorkflowEntityType(str, PyEnum):
    MATTER = "matter"
    COMPLIANCE_CYCLE = "compliance_cycle"
    NOTICE = "notice"
    REVIEW = "review"
    TASK = "task"
    AUDIT_WORKPAPER = "audit_workpaper"
    DOCUMENT = "document"


class WorkflowDefinition(Base, TenantBaseModelMixin):
    __tablename__ = "workflow_definitions"
    __table_args__ = (
        Index("ix_workflow_definitions_tenant_entity", "tenant_id", "entity_type"),
        Index("ix_workflow_definitions_tenant_code", "tenant_id", "code"),
        UniqueConstraint("tenant_id", "code", name="uq_tenant_workflow_code"),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_type: Mapped[WorkflowEntityType] = mapped_column(Enum(WorkflowEntityType), nullable=False, index=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    initial_state: Mapped[str] = mapped_column(String(100), nullable=False)
    states: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    transitions: Mapped[List[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    instances: Mapped[List["WorkflowInstance"]] = relationship("WorkflowInstance", back_populates="definition", lazy="dynamic")
    transitions_def: Mapped[List["WorkflowTransitionDefinition"]] = relationship("WorkflowTransitionDefinition", back_populates="definition", lazy="dynamic")


class WorkflowTransitionDefinition(Base, TenantBaseModelMixin):
    __tablename__ = "workflow_transition_definitions"
    __table_args__ = (
        Index("ix_wf_transition_defs_tenant_workflow", "tenant_id", "workflow_definition_id"),
        Index("ix_wf_transition_defs_from_to", "from_state", "to_state"),
        UniqueConstraint("workflow_definition_id", "code", name="uq_wf_def_transition_code"),
    )

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)

    required_permissions: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    required_roles: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    auto_transition: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_transition_delay: Mapped[Optional[int]] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    definition: Mapped["WorkflowDefinition"] = relationship("WorkflowDefinition", back_populates="transitions_def")


class WorkflowInstance(Base, TenantBaseModelMixin):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        Index("ix_workflow_instances_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_workflow_instances_tenant_definition", "tenant_id", "workflow_definition_id"),
        Index("ix_workflow_instances_tenant_state", "tenant_id", "current_state"),
        Index("ix_workflow_instances_tenant_assignee", "tenant_id", "assigned_user_id"),
        UniqueConstraint("tenant_id", "entity_type", "entity_id", name="uq_tenant_entity_workflow"),
    )

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    entity_type: Mapped[WorkflowEntityType] = mapped_column(Enum(WorkflowEntityType), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    current_state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    previous_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    context_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    definition: Mapped["WorkflowDefinition"] = relationship("WorkflowDefinition", back_populates="instances")
    assigned_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_user_id], lazy="selectin")
    history: Mapped[List["WorkflowTransitionHistory"]] = relationship("WorkflowTransitionHistory", back_populates="instance", lazy="dynamic")


class WorkflowTransitionHistory(Base, TenantBaseModelMixin):
    __tablename__ = "workflow_transition_history"
    __table_args__ = (
        Index("ix_wf_history_tenant_instance", "tenant_id", "workflow_instance_id"),
        Index("ix_wf_history_tenant_actor", "tenant_id", "actor_id"),
        Index("ix_wf_history_created_at", "created_at"),
    )

    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transition_definition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_transition_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )

    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)
    transition_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    actor_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )

    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    instance: Mapped["WorkflowInstance"] = relationship("WorkflowInstance", back_populates="history")
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id], lazy="selectin")