from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CommentAttachmentBase(BaseModel):
    filename: str = Field(..., max_length=500)
    file_size: int = Field(..., ge=0)
    mime_type: str = Field(..., max_length=100)
    storage_path: str = Field(..., max_length=1000)
    storage_provider: str = Field(default="azure_blob", max_length=50)
    storage_key: str = Field(..., max_length=500)
    metadata: Dict[str, Any] = {}


class CommentAttachmentCreate(CommentAttachmentBase):
    pass


class CommentAttachmentResponse(CommentAttachmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    comment_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class CommentReactionBase(BaseModel):
    comment_id: UUID
    reaction_type: str = Field(..., max_length=20)
    metadata: Dict[str, Any] = {}


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
    parent_comment_id: Optional[UUID] = None
    mentions: List[UUID] = []
    metadata: Dict[str, Any] = {}


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    comment_type: Optional[str] = Field(None, max_length=20)
    mentions: Optional[List[UUID]] = None
    metadata: Optional[Dict[str, Any]] = None


class CommentResponse(CommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    is_edited: bool
    edited_at: Optional[datetime] = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    author: Optional["UserResponse"] = None
    parent_comment: Optional["CommentResponse"] = None
    replies: List["CommentResponse"] = []
    attachments: List[CommentAttachmentResponse] = []
    reactions: List[CommentReactionResponse] = []


class CommentListResponse(BaseModel):
    items: List[CommentResponse]
    total: int
    page: int
    page_size: int


class CommentThreadResponse(BaseModel):
    comments: List[CommentResponse]
    total: int
    page: int
    page_size: int


from app.modules.users.schemas import UserResponse