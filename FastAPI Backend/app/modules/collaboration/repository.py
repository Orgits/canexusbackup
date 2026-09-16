from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.collaboration.models import (
    Comment,
    CommentableEntityType,
    CommentAttachment,
    CommentReaction,
    CommentType,
)


class CollaborationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Comment methods
    async def create_comment(self, comment: Comment) -> Comment:
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def get_comment_by_id(self, comment_id: UUID, tenant_id: UUID) -> Comment | None:
        result = await self.db.execute(
            select(Comment)
            .where(
                Comment.id == comment_id,
                Comment.tenant_id == tenant_id,
            )
            .options(
                selectinload(Comment.author),
                selectinload(Comment.parent_comment).selectinload(Comment.author),
                selectinload(Comment.replies).selectinload(Comment.author),
                selectinload(Comment.attachments),
                selectinload(Comment.reactions).selectinload(CommentReaction.user),
            )
        )
        return result.scalar_one_or_none()

    async def get_comments_for_entity(
        self,
        entity_type: CommentableEntityType,
        entity_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        include_replies: bool = False,
        comment_type: CommentType | None = None,
    ) -> tuple[list[Comment], int]:
        query = select(Comment).where(
            Comment.entity_type == entity_type,
            Comment.entity_id == entity_id,
            Comment.tenant_id == tenant_id,
            Comment.parent_comment_id.is_(None) if not include_replies else True,
        )
        count_query = select(func.count(Comment.id)).where(
            Comment.entity_type == entity_type,
            Comment.entity_id == entity_id,
            Comment.tenant_id == tenant_id,
            Comment.parent_comment_id.is_(None) if not include_replies else True,
        )

        if comment_type:
            query = query.where(Comment.comment_type == comment_type)
            count_query = count_query.where(Comment.comment_type == comment_type)

        query = query.order_by(Comment.created_at.desc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(Comment.author),
                selectinload(Comment.replies).selectinload(Comment.author),
                selectinload(Comment.attachments),
                selectinload(Comment.reactions).selectinload(CommentReaction.user),
            )
        )
        comments = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(comments), total

    async def get_comment_thread(
        self, comment_id: UUID, tenant_id: UUID
    ) -> list[Comment]:
        # Get all replies recursively
        result = await self.db.execute(
            select(Comment)
            .where(
                Comment.parent_comment_id == comment_id,
                Comment.tenant_id == tenant_id,
            )
            .options(
                selectinload(Comment.author),
                selectinload(Comment.replies).selectinload(Comment.author),
                selectinload(Comment.attachments),
                selectinload(Comment.reactions).selectinload(CommentReaction.user),
            )
            .order_by(Comment.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_comment(self, comment: Comment) -> Comment:
        comment.is_edited = True
        comment.edited_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def delete_comment(self, comment: Comment) -> None:
        # Soft delete - mark as deleted in metadata
        comment.metadata = {**comment.metadata, "deleted": True, "deleted_at": datetime.now(UTC).isoformat()}
        comment.content = "[Deleted]"
        await self.db.flush()

    # Attachment methods
    async def create_attachment(self, attachment: CommentAttachment) -> CommentAttachment:
        self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(attachment)
        return attachment

    async def get_attachments_for_comment(self, comment_id: UUID, tenant_id: UUID) -> list[CommentAttachment]:
        result = await self.db.execute(
            select(CommentAttachment).where(
                CommentAttachment.comment_id == comment_id,
                CommentAttachment.tenant_id == tenant_id,
            )
        )
        return list(result.scalars().all())

    async def delete_attachment(self, attachment: CommentAttachment) -> None:
        await self.db.delete(attachment)
        await self.db.flush()

    # Reaction methods
    async def create_reaction(self, reaction: CommentReaction) -> CommentReaction:
        self.db.add(reaction)
        await self.db.flush()
        await self.db.refresh(reaction)
        return reaction

    async def get_reaction(
        self, comment_id: UUID, user_id: UUID, reaction_type: str, tenant_id: UUID
    ) -> CommentReaction | None:
        result = await self.db.execute(
            select(CommentReaction).where(
                CommentReaction.comment_id == comment_id,
                CommentReaction.user_id == user_id,
                CommentReaction.reaction_type == reaction_type,
                CommentReaction.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_reactions_for_comment(self, comment_id: UUID, tenant_id: UUID) -> list[CommentReaction]:
        result = await self.db.execute(
            select(CommentReaction)
            .where(
                CommentReaction.comment_id == comment_id,
                CommentReaction.tenant_id == tenant_id,
            )
            .options(selectinload(CommentReaction.user))
        )
        return list(result.scalars().all())

    async def delete_reaction(self, reaction: CommentReaction) -> None:
        await self.db.delete(reaction)
        await self.db.flush()

    async def toggle_reaction(
        self, comment_id: UUID, user_id: UUID, reaction_type: str, tenant_id: UUID
    ) -> tuple[CommentReaction, bool]:
        """Toggle reaction - returns (reaction, created) where created is True if new, False if removed"""
        existing = await self.get_reaction(comment_id, user_id, reaction_type, tenant_id)
        if existing:
            await self.delete_reaction(existing)
            return existing, False
        reaction = CommentReaction(
            comment_id=comment_id,
            user_id=user_id,
            reaction_type=reaction_type,
            tenant_id=tenant_id,
            created_by=user_id,
        )
        created = await self.create_reaction(reaction)
        return created, True


