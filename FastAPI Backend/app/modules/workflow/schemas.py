from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStateBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = None
    is_initial: bool = False
    is_terminal: bool = False
    order: int = 0
    color: str | None = None
    icon: str | None = None
    metadata: dict[str, Any] = {}


class WorkflowTransitionBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = None
    from_state: str = Field(..., max_length=100)
    to_state: str = Field(..., max_length=100)
    required_permissions: list[str] = []
    required_roles: list[str] = []
    conditions: dict[str, Any] = {}
    auto_transition: bool = False
    auto_transition_delay: int | None = None
    is_active: bool = True
    metadata: dict[str, Any] = {}


class WorkflowDefinitionBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: str | None = None
    entity_type: str = Field(..., max_length=50)
    initial_state: str = Field(..., max_length=100)
    states: list[WorkflowStateBase] = []
    transitions: list[WorkflowTransitionBase] = []
    is_active: bool = True
    is_default: bool = False
    metadata: dict[str, Any] = {}


class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    pass


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    states: list[WorkflowStateBase] | None = None
    transitions: list[WorkflowTransitionBase] | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    metadata: dict[str, Any] | None = None


class WorkflowDefinitionResponse(WorkflowDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class WorkflowTransitionDefinitionBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = None
    from_state: str = Field(..., max_length=100)
    to_state: str = Field(..., max_length=100)
    required_permissions: list[str] = []
    required_roles: list[str] = []
    conditions: dict[str, Any] = {}
    auto_transition: bool = False
    auto_transition_delay: int | None = None
    is_active: bool = True
    metadata: dict[str, Any] = {}


class WorkflowTransitionDefinitionCreate(WorkflowTransitionDefinitionBase):
    pass


class WorkflowTransitionDefinitionUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    required_permissions: list[str] | None = None
    required_roles: list[str] | None = None
    conditions: dict[str, Any] | None = None
    auto_transition: bool | None = None
    auto_transition_delay: int | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class WorkflowTransitionDefinitionResponse(WorkflowTransitionDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_definition_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class WorkflowInstanceBase(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    current_state: str = Field(..., max_length=100)
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    context_data: dict[str, Any] = {}


class WorkflowInstanceCreate(BaseModel):
    workflow_definition_id: UUID
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    context_data: dict[str, Any] = {}


class WorkflowInstanceUpdate(BaseModel):
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    context_data: dict[str, Any] | None = None
    is_active: bool | None = None


class WorkflowInstanceResponse(WorkflowInstanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_definition_id: UUID
    previous_state: str | None = None
    is_active: bool
    completed_at: datetime | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    definition: WorkflowDefinitionResponse | None = None
    assigned_user: Optional["UserResponse"] = None


class WorkflowTransitionRequest(BaseModel):
    transition_code: str = Field(..., max_length=100)
    comment: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = {}


class WorkflowTransitionHistoryBase(BaseModel):
    from_state: str = Field(..., max_length=100)
    to_state: str = Field(..., max_length=100)
    transition_code: str | None = None
    comment: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = {}


class WorkflowTransitionHistoryResponse(WorkflowTransitionHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_instance_id: UUID
    transition_definition_id: UUID | None = None
    actor_id: UUID
    actor_team_id: UUID | None = None
    tenant_id: UUID
    created_at: datetime

    actor: Optional["UserResponse"] = None


class AvailableTransitionResponse(BaseModel):
    transition: WorkflowTransitionDefinitionResponse
    can_execute: bool
    missing_permissions: list[str] = []
    missing_roles: list[str] = []


class WorkflowDefinitionListResponse(BaseModel):
    items: list[WorkflowDefinitionResponse]
    total: int
    page: int
    page_size: int


class WorkflowInstanceListResponse(BaseModel):
    items: list[WorkflowInstanceResponse]
    total: int
    page: int
    page_size: int


class WorkflowTransitionHistoryListResponse(BaseModel):
    items: list[WorkflowTransitionHistoryResponse]
    total: int
    page: int
    page_size: int


from app.modules.users.schemas import UserResponse
