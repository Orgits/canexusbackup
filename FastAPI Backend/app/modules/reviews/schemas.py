from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ReviewCommentBase(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False
    mentions: List[UUID] = []
    parent_comment_id: Optional[UUID] = None
    metadata: Dict[str, Any] = {}


class ReviewCommentCreate(ReviewCommentBase):
    pass


class ReviewCommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    is_internal: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ReviewCommentResponse(ReviewCommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_request_id: UUID
    author_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    author: Optional["UserResponse"] = None
    replies: List["ReviewCommentResponse"] = []


class ReviewHistoryBase(BaseModel):
    action: str = Field(..., max_length=50)
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    comment: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ReviewHistoryResponse(ReviewHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_request_id: UUID
    actor_id: UUID
    tenant_id: UUID
    created_at: datetime

    actor: Optional["UserResponse"] = None


class ReviewRequestBase(BaseModel):
    source_object_type: str = Field(..., max_length=50)
    source_object_id: UUID
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    stage: str = Field(default="draft", max_length=50)
    reviewer_id: Optional[UUID] = None
    reviewer_team_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    priority: str = Field(default="medium", max_length=20)
    metadata: Dict[str, Any] = {}


class ReviewRequestCreate(ReviewRequestBase):
    pass


class ReviewRequestUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    reviewer_id: Optional[UUID] = None
    reviewer_team_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = Field(None, max_length=20)
    metadata: Optional[Dict[str, Any]] = None


class ReviewActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|request_rework|escalate|submit)$")
    comment: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ReviewRequestResponse(ReviewRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_instance_id: Optional[UUID] = None
    status: str
    submitted_by_id: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    reviewer: Optional["UserResponse"] = None
    reviewer_team: Optional["TeamResponse"] = None
    submitted_by: Optional["UserResponse"] = None
    workflow_instance: Optional["WorkflowInstanceResponse"] = None


class ReviewRequestDetailResponse(ReviewRequestResponse):
    comments: List[ReviewCommentResponse] = []
    history: List[ReviewHistoryResponse] = []


class ReviewRequestListResponse(BaseModel):
    items: List[ReviewRequestResponse]
    total: int
    page: int
    page_size: int


class ReviewCommentListResponse(BaseModel):
    items: List[ReviewCommentResponse]
    total: int
    page: int
    page_size: int


class ReviewHistoryListResponse(BaseModel):
    items: List[ReviewHistoryResponse]
    total: int
    page: int
    page_size: int


from app.modules.users.schemas import UserResponse, TeamResponse
from app.modules.workflow.schemas import WorkflowInstanceResponse