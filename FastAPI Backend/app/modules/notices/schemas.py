from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class NoticeEscalationBase(BaseModel):
    escalated_to_id: UUID
    reason: str
    previous_deadline: Optional[datetime] = None
    new_deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class NoticeEscalationCreate(NoticeEscalationBase):
    pass


class NoticeEscalationResponse(NoticeEscalationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notice_id: UUID
    escalated_from_id: Optional[UUID] = None
    escalated_by_id: UUID
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    escalated_from: Optional["UserResponse"] = None
    escalated_to: Optional["UserResponse"] = None
    escalated_by: Optional["UserResponse"] = None


class NoticeEscalationListResponse(BaseModel):
    items: List[NoticeEscalationResponse]
    total: int
    page: int
    page_size: int


class NoticeBase(BaseModel):
    client_id: UUID
    authority: str = Field(..., max_length=50)
    authority_name: Optional[str] = Field(None, max_length=255)
    reference_number: str = Field(..., max_length=100)
    notice_type: str = Field(..., max_length=50)
    subject: str = Field(..., max_length=500)
    description: Optional[str] = None
    received_date: datetime
    notice_date: Optional[datetime] = None
    response_deadline: datetime
    extended_deadline: Optional[datetime] = None
    priority: str = Field(default="medium", max_length=20)
    assignee_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    demand_amount: Optional[float] = Field(None, ge=0)
    penalty_amount: Optional[float] = Field(None, ge=0)
    interest_amount: Optional[float] = Field(None, ge=0)
    metadata: Dict[str, Any] = {}


class NoticeCreate(NoticeBase):
    matter_id: Optional[UUID] = None


class NoticeUpdate(BaseModel):
    matter_id: Optional[UUID] = None
    authority: Optional[str] = Field(None, max_length=50)
    authority_name: Optional[str] = Field(None, max_length=255)
    reference_number: Optional[str] = Field(None, max_length=100)
    notice_type: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    received_date: Optional[datetime] = None
    notice_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    extended_deadline: Optional[datetime] = None
    status: Optional[str] = None
    priority: Optional[str] = Field(None, max_length=20)
    assignee_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    demand_amount: Optional[float] = Field(None, ge=0)
    penalty_amount: Optional[float] = Field(None, ge=0)
    interest_amount: Optional[float] = Field(None, ge=0)
    total_amount: Optional[float] = Field(None, ge=0)
    response_draft: Optional[str] = None
    response_filed_date: Optional[datetime] = None
    response_acknowledgment: Optional[str] = Field(None, max_length=100)
    response_mode: Optional[str] = Field(None, max_length=50)
    outcome: Optional[str] = None
    order_date: Optional[datetime] = None
    order_summary: Optional[str] = None
    appeal_filed: Optional[bool] = None
    appeal_details: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NoticeStatusUpdate(BaseModel):
    status: str = Field(..., max_length=50)
    comment: Optional[str] = None
    metadata: Dict[str, Any] = {}


class NoticeResponseUpdate(BaseModel):
    response_draft: Optional[str] = None
    response_filed_date: Optional[datetime] = None
    response_acknowledgment: Optional[str] = Field(None, max_length=100)
    response_mode: Optional[str] = Field(None, max_length=50)
    metadata: Dict[str, Any] = {}


class NoticeClosureUpdate(BaseModel):
    closure_reason: str
    outcome: Optional[str] = None
    order_date: Optional[datetime] = None
    order_summary: Optional[str] = None
    appeal_filed: bool = False
    appeal_details: Optional[str] = None
    metadata: Dict[str, Any] = {}


class NoticeResponse(NoticeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    matter_id: Optional[UUID] = None
    workflow_instance_id: Optional[UUID] = None
    status: str
    escalated_to_id: Optional[UUID] = None
    total_amount: Optional[float] = None
    response_draft: Optional[str] = None
    response_filed_date: Optional[datetime] = None
    response_acknowledgment: Optional[str] = None
    response_mode: Optional[str] = None
    outcome: Optional[str] = None
    order_date: Optional[datetime] = None
    order_summary: Optional[str] = None
    appeal_filed: bool
    appeal_details: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[UUID] = None
    closure_reason: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    client: Optional["ClientResponse"] = None
    matter: Optional["MatterResponse"] = None
    assignee: Optional["UserResponse"] = None
    team: Optional["TeamResponse"] = None
    escalated_to: Optional["UserResponse"] = None
    escalation_history: List[NoticeEscalationResponse] = []


class NoticeListResponse(BaseModel):
    items: List[NoticeResponse]
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
    upcoming_deadlines: List[NoticeResponse] = []


from app.modules.clients.schemas import ClientResponse
from app.modules.matters.schemas import MatterResponse
from app.modules.users.schemas import UserResponse, TeamResponse