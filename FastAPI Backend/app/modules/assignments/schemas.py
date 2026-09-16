from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssignmentBase(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    user_id: UUID | None = None
    team_id: UUID | None = None
    notes: str | None = None
    metadata: dict[str, Any] = {}


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    user_id: UUID | None = None
    team_id: UUID | None = None
    is_active: bool | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class AssignmentReassignRequest(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    new_user_id: UUID | None = None
    new_team_id: UUID | None = None
    reason: str
    metadata: dict[str, Any] = {}


class AssignmentUnassignRequest(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    reason: str
    metadata: dict[str, Any] = {}


class AssignmentResponse(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assigned_by_id: UUID
    assigned_at: datetime
    is_active: bool
    unassigned_at: datetime | None = None
    unassigned_by_id: UUID | None = None
    unassign_reason: str | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    user: Optional["UserResponse"] = None
    team: Optional["TeamResponse"] = None
    assigned_by: Optional["UserResponse"] = None


class AssignmentHistoryBase(BaseModel):
    action: str = Field(..., max_length=50)
    from_user_id: UUID | None = None
    to_user_id: UUID | None = None
    from_team_id: UUID | None = None
    to_team_id: UUID | None = None
    reason: str | None = None
    metadata: dict[str, Any] = {}


class AssignmentHistoryResponse(AssignmentHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assignment_id: UUID
    actor_id: UUID
    tenant_id: UUID
    created_at: datetime

    actor: Optional["UserResponse"] = None


class AssignmentHistoryListResponse(BaseModel):
    items: list[AssignmentHistoryResponse]
    total: int
    page: int
    page_size: int


class EscalationBase(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    escalated_to_id: UUID
    reason: str = Field(..., max_length=50)
    description: str
    metadata: dict[str, Any] = {}


class EscalationCreate(EscalationBase):
    pass


class EscalationUpdate(BaseModel):
    is_resolved: bool | None = None
    resolution_notes: str | None = None
    metadata: dict[str, Any] | None = None


class EscalationResolveRequest(BaseModel):
    resolution_notes: str | None = None
    metadata: dict[str, Any] = {}


class EscalationResponse(EscalationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    escalated_from_id: UUID | None = None
    escalated_by_id: UUID
    previous_assignee_id: UUID | None = None
    previous_team_id: UUID | None = None
    is_resolved: bool
    resolved_at: datetime | None = None
    resolved_by_id: UUID | None = None
    resolution_notes: str | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    escalated_from: Optional["UserResponse"] = None
    escalated_to: Optional["UserResponse"] = None
    escalated_by: Optional["UserResponse"] = None


class EscalationListResponse(BaseModel):
    items: list[EscalationResponse]
    total: int
    page: int
    page_size: int


class BulkAssignmentRequest(BaseModel):
    assignments: list[AssignmentCreate]


class BulkReassignmentRequest(BaseModel):
    reassignments: list[AssignmentReassignRequest]


from app.modules.users.schemas import TeamResponse, UserResponse
