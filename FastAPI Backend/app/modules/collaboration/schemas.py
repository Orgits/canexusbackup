from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommentAttachmentBase(BaseModel):
    filename: str = Field(..., max_length=500)
    file_size: int = Field(..., ge=0)
    mime_type: str = Field(..., max_length=100)
    storage_path: str = Field(..., max_length=1000)
    storage_provider: str = Field(default="azure_blob", max_length=50)
    storage_key: str = Field(..., max_length=500)
    metadata: dict[str, Any] = {}


class CommentAttachmentCreate(CommentAttachmentBase):
    pass


class CommentAttachmentResponse(CommentAttachmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    comment_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


class CommentReactionBase(BaseModel):
    comment_id: UUID
    reaction_type: str = Field(..., max_length=20)
    metadata: dict[str, Any] = {}


class CommentReactionCreate(CommentReactionBase):
    pass


class CommentReactionResponse(CommentReactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tenant_id: UUID
    created_at: datetime

    user: Optional["UserResponse"] = None


class CommentBase(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    content: str = Field(..., min_length=1)
    comment_type: str = Field(default="comment", max_length=20)
    parent_comment_id: UUID | None = None
    mentions: list[UUID] = []
    metadata: dict[str, Any] = {}


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)
    comment_type: str | None = Field(None, max_length=20)
    mentions: list[UUID] | None = None
    metadata: dict[str, Any] | None = None


class CommentResponse(CommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    is_edited: bool
    edited_at: datetime | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    author: Optional["UserResponse"] = None
    parent_comment: Optional["CommentResponse"] = None
    replies: list["CommentResponse"] = []
    attachments: list[CommentAttachmentResponse] = []
    reactions: list[CommentReactionResponse] = []


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    page_size: int


class CommentThreadResponse(BaseModel):
    comments: list[CommentResponse]
    total: int
    page: int
    page_size: int


from app.modules.users.schemas import UserResponse
