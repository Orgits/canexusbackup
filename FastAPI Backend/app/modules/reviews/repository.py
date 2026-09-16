from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.reviews.models import (
    ReviewComment,
    ReviewHistory,
    ReviewRequest,
    ReviewStage,
    ReviewStatus,
    ReviewType,
)


class ReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Review Request methods
    async def create_request(self, request: ReviewRequest) -> ReviewRequest:
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_request_by_id(self, request_id: UUID, tenant_id: UUID) -> ReviewRequest | None:
        result = await self.db.execute(
            select(ReviewRequest)
            .where(
                ReviewRequest.id == request_id,
                ReviewRequest.tenant_id == tenant_id,
            )
            .options(
                selectinload(ReviewRequest.reviewer),
                selectinload(ReviewRequest.reviewer_team),
                selectinload(ReviewRequest.submitted_by),
                selectinload(ReviewRequest.workflow_instance),
            )
        )
        return result.scalar_one_or_none()

    async def get_request_by_source(
        self, source_type: ReviewType, source_id: UUID, stage: str | None, tenant_id: UUID
    ) -> ReviewRequest | None:
        query = select(ReviewRequest).where(
            ReviewRequest.source_object_type == source_type,
            ReviewRequest.source_object_id == source_id,
            ReviewRequest.tenant_id == tenant_id,
        )
        if stage:
            query = query.where(ReviewRequest.stage == ReviewStage(stage))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_requests(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        source_type: ReviewType | None = None,
        source_id: UUID | None = None,
        stage: ReviewStage | None = None,
        status: ReviewStatus | None = None,
        reviewer_id: UUID | None = None,
        reviewer_team_id: UUID | None = None,
        submitted_by_id: UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[ReviewRequest], int]:
        query = select(ReviewRequest).where(ReviewRequest.tenant_id == tenant_id)
        count_query = select(func.count(ReviewRequest.id)).where(ReviewRequest.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    ReviewRequest.title.ilike(search_term),
                    ReviewRequest.description.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    ReviewRequest.title.ilike(search_term),
                    ReviewRequest.description.ilike(search_term),
                )
            )

        if source_type:
            query = query.where(ReviewRequest.source_object_type == source_type)
            count_query = count_query.where(ReviewRequest.source_object_type == source_type)

        if source_id:
            query = query.where(ReviewRequest.source_object_id == source_id)
            count_query = count_query.where(ReviewRequest.source_object_id == source_id)

        if stage:
            query = query.where(ReviewRequest.stage == stage)
            count_query = count_query.where(ReviewRequest.stage == stage)

        if status:
            query = query.where(ReviewRequest.status == status)
            count_query = count_query.where(ReviewRequest.status == status)

        if reviewer_id:
            query = query.where(ReviewRequest.reviewer_id == reviewer_id)
            count_query = count_query.where(ReviewRequest.reviewer_id == reviewer_id)

        if reviewer_team_id:
            query = query.where(ReviewRequest.reviewer_team_id == reviewer_team_id)
            count_query = count_query.where(ReviewRequest.reviewer_team_id == reviewer_team_id)

        if submitted_by_id:
            query = query.where(ReviewRequest.submitted_by_id == submitted_by_id)
            count_query = count_query.where(ReviewRequest.submitted_by_id == submitted_by_id)

        if due_date_from:
            query = query.where(ReviewRequest.due_date >= due_date_from)
            count_query = count_query.where(ReviewRequest.due_date >= due_date_from)

        if due_date_to:
            query = query.where(ReviewRequest.due_date <= due_date_to)
            count_query = count_query.where(ReviewRequest.due_date <= due_date_to)

        if sort_by and hasattr(ReviewRequest, sort_by):
            column = getattr(ReviewRequest, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(ReviewRequest.created_at.desc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(ReviewRequest.reviewer),
                selectinload(ReviewRequest.reviewer_team),
                selectinload(ReviewRequest.submitted_by),
            )
        )
        requests = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(requests), total

    async def update_request(self, request: ReviewRequest) -> ReviewRequest:
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def delete_request(self, request: ReviewRequest) -> None:
        await self.db.delete(request)
        await self.db.flush()

    # Review Comment methods
    async def create_comment(self, comment: ReviewComment) -> ReviewComment:
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def get_comment_by_id(self, comment_id: UUID, tenant_id: UUID) -> ReviewComment | None:
        result = await self.db.execute(
            select(ReviewComment)
            .where(
                ReviewComment.id == comment_id,
                ReviewComment.tenant_id == tenant_id,
            )
            .options(selectinload(ReviewComment.author))
        )
        return result.scalar_one_or_none()

    async def get_comments_for_request(
        self,
        request_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        include_replies: bool = True,
    ) -> tuple[list[ReviewComment], int]:
        query = select(ReviewComment).where(
            ReviewComment.review_request_id == request_id,
            ReviewComment.tenant_id == tenant_id,
            ReviewComment.parent_comment_id.is_(None) if not include_replies else True,
        ).order_by(ReviewComment.created_at.asc())
        count_query = select(func.count(ReviewComment.id)).where(
            ReviewComment.review_request_id == request_id,
            ReviewComment.tenant_id == tenant_id,
            ReviewComment.parent_comment_id.is_(None) if not include_replies else True,
        )

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query.options(selectinload(ReviewComment.author), selectinload(ReviewComment.replies).selectinload(ReviewComment.author)))
        comments = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(comments), total

    async def update_comment(self, comment: ReviewComment) -> ReviewComment:
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def delete_comment(self, comment: ReviewComment) -> None:
        await self.db.delete(comment)
        await self.db.flush()

    # Review History methods
    async def create_history(self, history: ReviewHistory) -> ReviewHistory:
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def get_history_for_request(
        self,
        request_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ReviewHistory], int]:
        query = (
            select(ReviewHistory)
            .where(
                ReviewHistory.review_request_id == request_id,
                ReviewHistory.tenant_id == tenant_id,
            )
            .order_by(ReviewHistory.created_at.desc())
        )
        count_query = select(func.count(ReviewHistory.id)).where(
            ReviewHistory.review_request_id == request_id,
            ReviewHistory.tenant_id == tenant_id,
        )

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query.options(selectinload(ReviewHistory.actor)))
        history = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(history), total
