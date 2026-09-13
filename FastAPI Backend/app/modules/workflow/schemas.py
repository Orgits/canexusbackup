from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class WorkflowStateBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    is_initial: bool = False
    is_terminal: bool = False
    order: int = 0
    color: Optional[str] = None
    icon: Optional[str] = None
    metadata: Dict[str, Any] = {}


class WorkflowTransitionBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    from_state: str = Field(..., max_length=100)
    to_state: str = Field(..., max_length=100)
    required_permissions: List[str] = []
    required_roles: List[str] = []
    conditions: Dict[str, Any] = {}
    auto_transition: bool = False
    auto_transition_delay: Optional[int] = None
    is_active: bool = True
    metadata: Dict[str, Any] = {}


class WorkflowDefinitionBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    entity_type: str = Field(..., max_length=50)
    initial_state: str = Field(..., max_length=100)
    states: List[WorkflowStateBase] = []
    transitions: List[WorkflowTransitionBase] = []
    is_active: bool = True
    is_default: bool = False
    metadata: Dict[str, Any] = {}


class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    pass


class WorkflowDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    states: Optional[List[WorkflowStateBase]] = None
    transitions: Optional[List[WorkflowTransitionBase]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowDefinitionResponse(WorkflowDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class WorkflowTransitionDefinitionBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    from_state: str = Field(..., max_length=100)
    to_state: str = Field(..., max_length=100)
    required_permissions: List[str] = []
    required_roles: List[str] = []
    conditions: Dict[str, Any] = {}
    auto_transition: bool = False
    auto_transition_delay: Optional[int] = None
    is_active: bool = True
    metadata: Dict[str, Any] = {}


class WorkflowTransitionDefinitionCreate(WorkflowTransitionDefinitionBase):
    pass


class WorkflowTransitionDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    required_permissions: Optional[List[str]] = None
    required_roles: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    auto_transition: Optional[bool] = None
    auto_transition_delay: Optional[int] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowTransitionDefinitionResponse(WorkflowTransitionDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_definition_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class WorkflowInstanceBase(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    current_state: str = Field(..., max_length=100)
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    context_data: Dict[str, Any] = {}


class WorkflowInstanceCreate(BaseModel):
    workflow_definition_id: UUID
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    context_data: Dict[str, Any] = {}


class WorkflowInstanceUpdate(BaseModel):
    assigned_user_id: Optional[UUID] = None
    assigned_team_id: Optional[UUID] = None
    context_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WorkflowInstanceResponse(WorkflowInstanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_definition_id: UUID
    previous_state: Optional[str] = None
    is_active: bool
    completed_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    definition: Optional[WorkflowDefinitionResponse] = None
    assigned_user: Optional["UserResponse"] = None


class WorkflowTransitionRequest(BaseModel):
    transition_code: str = Field(..., max_length=100)
    comment: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class WorkflowTransitionHistoryBase(BaseModel):
    from_state: str = Field(..., max_length=100)
    to_state: str = Field(..., max_length=100)
    transition_code: Optional[str] = None
    comment: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class WorkflowTransitionHistoryResponse(WorkflowTransitionHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_instance_id: UUID
    transition_definition_id: Optional[UUID] = None
    actor_id: UUID
    actor_team_id: Optional[UUID] = None
    tenant_id: UUID
    created_at: datetime

    actor: Optional["UserResponse"] = None


class AvailableTransitionResponse(BaseModel):
    transition: WorkflowTransitionDefinitionResponse
    can_execute: bool
    missing_permissions: List[str] = []
    missing_roles: List[str] = []


class WorkflowDefinitionListResponse(BaseModel):
    items: List[WorkflowDefinitionResponse]
    total: int
    page: int
    page_size: int


class WorkflowInstanceListResponse(BaseModel):
    items: List[WorkflowInstanceResponse]
    total: int
    page: int
    page_size: int


class WorkflowTransitionHistoryListResponse(BaseModel):
    items: List[WorkflowTransitionHistoryResponse]
    total: int
    page: int
    page_size: int


from app.modules.users.schemas import UserResponse