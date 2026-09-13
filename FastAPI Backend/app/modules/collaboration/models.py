import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import (
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    func,
    Enum,
    ARRAY,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.clients.models import Client
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.documents.models import Document
    from app.modules.notices.models import Notice
    from app.modules.reviews.models import ReviewRequest


class CommentableEntityType(str, PyEnum):
    MATTER = "matter"
    TASK = "task"
    DOCUMENT = "document"
    NOTICE = "notice"
    REVIEW = "review"
    CLIENT = "client"
    COMPLIANCE_CYCLE = "compliance_cycle"
    MCA_CYCLE = "mca_cycle"
    TDS_CYCLE = "tds_cycle"


class CommentType(str, PyEnum):
    COMMENT = "comment"
    INTERNAL_NOTE = "internal_note"
    MENTION = "mention"
    SYSTEM = "system"


class Comment(Base, TenantBaseModelMixin):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_comments_tenant_author", "tenant_id", "author_id"),
        Index("ix_comments_tenant_parent", "tenant_id", "parent_comment_id"),
        Index("ix_comments_created_at", "created_at"),
    )

    entity_type: Mapped[CommentableEntityType] = mapped_column(Enum(CommentableEntityType), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    comment_type: Mapped[CommentType] = mapped_column(Enum(CommentType), default=CommentType.COMMENT, nullable=False)

    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
    )

    mentions: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], lazy="selectin")
    parent_comment: Mapped[Optional["Comment"]] = relationship("Comment", remote_side="Comment.id", back_populates="replies", lazy="selectin")
    replies: Mapped[List["Comment"]] = relationship("Comment", back_populates="parent_comment", lazy="dynamic")
    attachments: Mapped[List["CommentAttachment"]] = relationship("CommentAttachment", back_populates="comment", lazy="dynamic")


class CommentAttachment(Base, TenantBaseModelMixin):
    __tablename__ = "comment_attachments"
    __table_args__ = (
        Index("ix_comment_attachments_tenant_comment", "tenant_id", "comment_id"),
    )

    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), default="azure_blob", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    comment: Mapped["Comment"] = relationship("Comment", back_populates="attachments")


class CommentReaction(Base, TenantBaseModelMixin):
    __tablename__ = "comment_reactions"
    __table_args__ = (
        Index("ix_comment_reactions_tenant_comment", "tenant_id", "comment_id"),
        Index("ix_comment_reactions_tenant_user", "tenant_id", "user_id"),
        UniqueConstraint("tenant_id", "comment_id", "user_id", "reaction_type", name="uq_comment_user_reaction"),
    )

    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    reaction_type: Mapped[str] = mapped_column(String(20), nullable=False)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    comment: Mapped["Comment"] = relationship("Comment", back_populates="reactions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")


# Add reactions relationship to Comment model
Comment.reactions: Mapped[List["CommentReaction"]] = relationship("CommentReaction", back_populates="comment", lazy="dynamic")