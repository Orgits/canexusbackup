from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict


class AssignmentBase(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    user_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    user_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AssignmentReassignRequest(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    new_user_id: Optional[UUID] = None
    new_team_id: Optional[UUID] = None
    reason: str
    metadata: Dict[str, Any] = {}


class AssignmentUnassignRequest(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    reason: str
    metadata: Dict[str, Any] = {}


class AssignmentResponse(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assigned_by_id: UUID
    assigned_at: datetime
    is_active: bool
    unassigned_at: Optional[datetime] = None
    unassigned_by_id: Optional[UUID] = None
    unassign_reason: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    user: Optional["UserResponse"] = None
    team: Optional["TeamResponse"] = None
    assigned_by: Optional["UserResponse"] = None


class AssignmentHistoryBase(BaseModel):
    action: str = Field(..., max_length=50)
    from_user_id: Optional[UUID] = None
    to_user_id: Optional[UUID] = None
    from_team_id: Optional[UUID] = None
    to_team_id: Optional[UUID] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class AssignmentHistoryResponse(AssignmentHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assignment_id: UUID
    actor_id: UUID
    tenant_id: UUID
    created_at: datetime

    actor: Optional["UserResponse"] = None


class AssignmentHistoryListResponse(BaseModel):
    items: List[AssignmentHistoryResponse]
    total: int
    page: int
    page_size: int


class EscalationBase(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    escalated_to_id: UUID
    reason: str = Field(..., max_length=50)
    description: str
    metadata: Dict[str, Any] = {}


class EscalationCreate(EscalationBase):
    pass


class EscalationUpdate(BaseModel):
    is_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EscalationResolveRequest(BaseModel):
    resolution_notes: Optional[str] = None
    metadata: Dict[str, Any] = {}


class EscalationResponse(EscalationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    escalated_from_id: Optional[UUID] = None
    escalated_by_id: UUID
    previous_assignee_id: Optional[UUID] = None
    previous_team_id: Optional[UUID] = None
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[UUID] = None
    resolution_notes: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    escalated_from: Optional["UserResponse"] = None
    escalated_to: Optional["UserResponse"] = None
    escalated_by: Optional["UserResponse"] = None


class EscalationListResponse(BaseModel):
    items: List[EscalationResponse]
    total: int
    page: int
    page_size: int


class BulkAssignmentRequest(BaseModel):
    assignments: List[AssignmentCreate]


class BulkReassignmentRequest(BaseModel):
    reassignments: List[AssignmentReassignRequest]


from app.modules.users.schemas import UserResponse, TeamResponse