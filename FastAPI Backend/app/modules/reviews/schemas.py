from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewCommentBase(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False
    mentions: list[UUID] = []
    parent_comment_id: UUID | None = None
    metadata: dict[str, Any] = {}


class ReviewCommentCreate(ReviewCommentBase):
    pass


class ReviewCommentUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)
    is_internal: bool | None = None
    metadata: dict[str, Any] | None = None


class ReviewCommentResponse(ReviewCommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_request_id: UUID
    author_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    author: Optional["UserResponse"] = None
    replies: list["ReviewCommentResponse"] = []


class ReviewHistoryBase(BaseModel):
    action: str = Field(..., max_length=50)
    from_stage: str | None = None
    to_stage: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    comment: str | None = None
    metadata: dict[str, Any] = {}


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
    description: str | None = None
    stage: str = Field(default="draft", max_length=50)
    reviewer_id: UUID | None = None
    reviewer_team_id: UUID | None = None
    due_date: datetime | None = None
    priority: str = Field(default="medium", max_length=20)
    metadata: dict[str, Any] = {}


class ReviewRequestCreate(ReviewRequestBase):
    pass


class ReviewRequestUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    reviewer_id: UUID | None = None
    reviewer_team_id: UUID | None = None
    due_date: datetime | None = None
    priority: str | None = Field(None, max_length=20)
    metadata: dict[str, Any] | None = None


class ReviewActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|request_rework|escalate|submit)$")
    comment: str | None = None
    metadata: dict[str, Any] = {}


class ReviewRequestResponse(ReviewRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_instance_id: UUID | None = None
    status: str
    submitted_by_id: UUID | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    reviewer: Optional["UserResponse"] = None
    reviewer_team: Optional["TeamResponse"] = None
    submitted_by: Optional["UserResponse"] = None
    workflow_instance: Optional["WorkflowInstanceResponse"] = None


class ReviewRequestDetailResponse(ReviewRequestResponse):
    comments: list[ReviewCommentResponse] = []
    history: list[ReviewHistoryResponse] = []


class ReviewRequestListResponse(BaseModel):
    items: list[ReviewRequestResponse]
    total: int
    page: int
    page_size: int


class ReviewCommentListResponse(BaseModel):
    items: list[ReviewCommentResponse]
    total: int
    page: int
    page_size: int


class ReviewHistoryListResponse(BaseModel):
    items: list[ReviewHistoryResponse]
    total: int
    page: int
    page_size: int


from app.modules.users.schemas import TeamResponse, UserResponse
from app.modules.workflow.schemas import WorkflowInstanceResponse
