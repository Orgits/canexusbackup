from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.collaboration.models import (
    Comment,
    CommentableEntityType,
    CommentAttachment,
    CommentReaction,
    CommentType,
)
from app.modules.collaboration.repository import CollaborationRepository
from app.modules.collaboration.schemas import (
    CommentAttachmentCreate,
    CommentCreate,
    CommentUpdate,
)
from app.modules.users.models import User


class CollaborationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = CollaborationRepository(db)

    async def create_comment(
        self, data: CommentCreate, tenant_id: UUID, author_id: UUID
    ) -> Comment:
        try:
            entity_type_enum = CommentableEntityType(data.entity_type)
            comment_type_enum = CommentType(data.comment_type)
        except ValueError as e:
            raise ValidationException(detail=str(e))

        # Validate parent comment if provided
        if data.parent_comment_id:
            parent = await self.repository.get_comment_by_id(data.parent_comment_id, tenant_id)
            if not parent:
                raise NotFoundException(detail="Parent comment not found")
            if parent.entity_type != entity_type_enum or parent.entity_id != data.entity_id:
                raise ValidationException(detail="Parent comment belongs to different entity")

        # Validate mentions
        if data.mentions:
            for user_id in data.mentions:
                user_result = await self.db.execute(
                    select(User).where(User.id == user_id, User.tenant_id == tenant_id)
                )
                if not user_result.scalar_one_or_none():
                    raise ValidationException(detail=f"Mentioned user {user_id} not found")

        comment = Comment(
            entity_type=entity_type_enum,
            entity_id=data.entity_id,
            author_id=author_id,
            content=data.content,
            comment_type=comment_type_enum,
            parent_comment_id=data.parent_comment_id,
            mentions=data.mentions,
            metadata=data.metadata,
            tenant_id=tenant_id,
            created_by=author_id,
        )
        return await self.repository.create_comment(comment)

    async def get_comment(self, comment_id: UUID, tenant_id: UUID) -> Comment:
        comment = await self.repository.get_comment_by_id(comment_id, tenant_id)
        if not comment:
            raise NotFoundException(detail="Comment not found")
        return comment

    async def get_comments(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        include_replies: bool = False,
        comment_type: str | None = None,
    ) -> tuple[list[Comment], int]:
        try:
            entity_type_enum = CommentableEntityType(entity_type)
        except ValueError:
            raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        comment_type_enum = None
        if comment_type:
            try:
                comment_type_enum = CommentType(comment_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid comment_type: {comment_type}")

        return await self.repository.get_comments_for_entity(
            entity_type_enum, entity_id, tenant_id, page, page_size, include_replies, comment_type_enum
        )

    async def get_comment_thread(self, comment_id: UUID, tenant_id: UUID) -> list[Comment]:
        comment = await self.get_comment(comment_id, tenant_id)
        replies = await self.repository.get_comment_thread(comment_id, tenant_id)
        return [comment] + replies

    async def update_comment(
        self, comment_id: UUID, tenant_id: UUID, data: CommentUpdate, updated_by: UUID
    ) -> Comment:
        comment = await self.get_comment(comment_id, tenant_id)

        if comment.author_id != updated_by:
            raise ValidationException(detail="Only author can update comment")

        update_data = data.model_dump(exclude_unset=True)

        # Validate mentions
        if "mentions" in update_data:
            for user_id in update_data["mentions"]:
                user_result = await self.db.execute(
                    select(User).where(User.id == user_id, User.tenant_id == tenant_id)
                )
                if not user_result.scalar_one_or_none():
                    raise ValidationException(detail=f"Mentioned user {user_id} not found")

        for field, value in update_data.items():
            setattr(comment, field, value)
        comment.updated_by = updated_by

        return await self.repository.update_comment(comment)

    async def delete_comment(self, comment_id: UUID, tenant_id: UUID, actor_id: UUID) -> None:
        comment = await self.get_comment(comment_id, tenant_id)

        if comment.author_id != actor_id:
            raise ValidationException(detail="Only author can delete comment")

        await self.repository.delete_comment(comment)

    # Attachment methods
    async def add_attachment(
        self, comment_id: UUID, data: CommentAttachmentCreate, tenant_id: UUID, uploaded_by: UUID
    ) -> CommentAttachment:
        comment = await self.get_comment(comment_id, tenant_id)

        attachment = CommentAttachment(
            comment_id=comment.id,
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=uploaded_by,
        )
        return await self.repository.create_attachment(attachment)

    async def get_attachments(self, comment_id: UUID, tenant_id: UUID) -> list[CommentAttachment]:
        await self.get_comment(comment_id, tenant_id)
        return await self.repository.get_attachments_for_comment(comment_id, tenant_id)

    async def delete_attachment(self, attachment_id: UUID, tenant_id: UUID, actor_id: UUID) -> None:
        result = await self.db.execute(
            select(CommentAttachment).where(
                CommentAttachment.id == attachment_id,
                CommentAttachment.tenant_id == tenant_id,
            )
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            raise NotFoundException(detail="Attachment not found")

        comment = await self.get_comment(attachment.comment_id, tenant_id)
        if comment.author_id != actor_id:
            raise ValidationException(detail="Only comment author can delete attachments")

        await self.repository.delete_attachment(attachment)

    # Reaction methods
    async def toggle_reaction(
        self, comment_id: UUID, reaction_type: str, tenant_id: UUID, user_id: UUID
    ) -> tuple[CommentReaction, bool]:
        comment = await self.get_comment(comment_id, tenant_id)

        reaction, created = await self.repository.toggle_reaction(comment_id, user_id, reaction_type, tenant_id)
        return reaction, created

    async def get_reactions(self, comment_id: UUID, tenant_id: UUID) -> list[CommentReaction]:
        await self.get_comment(comment_id, tenant_id)
        return await self.repository.get_reactions_for_comment(comment_id, tenant_id)

    async def remove_reaction(
        self, comment_id: UUID, reaction_type: str, tenant_id: UUID, user_id: UUID
    ) -> None:
        reaction = await self.repository.get_reaction(comment_id, user_id, reaction_type, tenant_id)
        if not reaction:
            raise NotFoundException(detail="Reaction not found")

        if reaction.user_id != user_id:
            raise ValidationException(detail="Only reaction owner can remove reaction")

        await self.repository.delete_reaction(reaction)
