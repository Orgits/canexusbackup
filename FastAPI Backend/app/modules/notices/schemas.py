from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoticeEscalationBase(BaseModel):
    escalated_to_id: UUID
    reason: str
    previous_deadline: datetime | None = None
    new_deadline: datetime | None = None
    metadata: dict[str, Any] = {}


class NoticeEscalationCreate(NoticeEscalationBase):
    pass


class NoticeEscalationResponse(NoticeEscalationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notice_id: UUID
    escalated_from_id: UUID | None = None
    escalated_by_id: UUID
    is_resolved: bool
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    escalated_from: Optional["UserResponse"] = None
    escalated_to: Optional["UserResponse"] = None
    escalated_by: Optional["UserResponse"] = None


class NoticeEscalationListResponse(BaseModel):
    items: list[NoticeEscalationResponse]
    total: int
    page: int
    page_size: int


class NoticeBase(BaseModel):
    client_id: UUID
    authority: str = Field(..., max_length=50)
    authority_name: str | None = Field(None, max_length=255)
    reference_number: str = Field(..., max_length=100)
    notice_type: str = Field(..., max_length=50)
    subject: str = Field(..., max_length=500)
    description: str | None = None
    received_date: datetime
    notice_date: datetime | None = None
    response_deadline: datetime
    extended_deadline: datetime | None = None
    priority: str = Field(default="medium", max_length=20)
    assignee_id: UUID | None = None
    team_id: UUID | None = None
    demand_amount: float | None = Field(None, ge=0)
    penalty_amount: float | None = Field(None, ge=0)
    interest_amount: float | None = Field(None, ge=0)
    metadata: dict[str, Any] = {}


class NoticeCreate(NoticeBase):
    matter_id: UUID | None = None


class NoticeUpdate(BaseModel):
    matter_id: UUID | None = None
    authority: str | None = Field(None, max_length=50)
    authority_name: str | None = Field(None, max_length=255)
    reference_number: str | None = Field(None, max_length=100)
    notice_type: str | None = Field(None, max_length=50)
    subject: str | None = Field(None, max_length=500)
    description: str | None = None
    received_date: datetime | None = None
    notice_date: datetime | None = None
    response_deadline: datetime | None = None
    extended_deadline: datetime | None = None
    status: str | None = None
    priority: str | None = Field(None, max_length=20)
    assignee_id: UUID | None = None
    team_id: UUID | None = None
    demand_amount: float | None = Field(None, ge=0)
    penalty_amount: float | None = Field(None, ge=0)
    interest_amount: float | None = Field(None, ge=0)
    total_amount: float | None = Field(None, ge=0)
    response_draft: str | None = None
    response_filed_date: datetime | None = None
    response_acknowledgment: str | None = Field(None, max_length=100)
    response_mode: str | None = Field(None, max_length=50)
    outcome: str | None = None
    order_date: datetime | None = None
    order_summary: str | None = None
    appeal_filed: bool | None = None
    appeal_details: str | None = None
    metadata: dict[str, Any] | None = None


class NoticeStatusUpdate(BaseModel):
    status: str = Field(..., max_length=50)
    comment: str | None = None
    metadata: dict[str, Any] = {}


class NoticeResponseUpdate(BaseModel):
    response_draft: str | None = None
    response_filed_date: datetime | None = None
    response_acknowledgment: str | None = Field(None, max_length=100)
    response_mode: str | None = Field(None, max_length=50)
    metadata: dict[str, Any] = {}


class NoticeClosureUpdate(BaseModel):
    closure_reason: str
    outcome: str | None = None
    order_date: datetime | None = None
    order_summary: str | None = None
    appeal_filed: bool = False
    appeal_details: str | None = None
    metadata: dict[str, Any] = {}


class NoticeResponse(NoticeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    matter_id: UUID | None = None
    workflow_instance_id: UUID | None = None
    status: str
    escalated_to_id: UUID | None = None
    total_amount: float | None = None
    response_draft: str | None = None
    response_filed_date: datetime | None = None
    response_acknowledgment: str | None = None
    response_mode: str | None = None
    outcome: str | None = None
    order_date: datetime | None = None
    order_summary: str | None = None
    appeal_filed: bool
    appeal_details: str | None = None
    closed_at: datetime | None = None
    closed_by: UUID | None = None
    closure_reason: str | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    client: Optional["ClientResponse"] = None
    matter: Optional["MatterResponse"] = None
    assignee: Optional["UserResponse"] = None
    team: Optional["TeamResponse"] = None
    escalated_to: Optional["UserResponse"] = None
    escalation_history: list[NoticeEscalationResponse] = []


class NoticeListResponse(BaseModel):
    items: list[NoticeResponse]
    total: int
    page: int
    page_size: int


class NoticeSummaryResponse(BaseModel):
    total_notices: int
    received: int
    under_review: int
    response_drafting: int
    responded: int
    hearing_scheduled: int
    closed: int
    overdue: int
    escalated: int
    total_demand_amount: float
    upcoming_deadlines: list[NoticeResponse] = []


from app.modules.clients.schemas import ClientResponse
from app.modules.matters.schemas import MatterResponse
from app.modules.users.schemas import TeamResponse, UserResponse
