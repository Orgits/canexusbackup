from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException, ValidationException
from app.modules.reviews.models import (
    ReviewRequest,
    ReviewComment,
    ReviewHistory,
    ReviewType,
    ReviewStage,
    ReviewStatus,
)
from app.modules.reviews.schemas import (
    ReviewRequestCreate,
    ReviewRequestUpdate,
    ReviewCommentCreate,
    ReviewCommentUpdate,
    ReviewActionRequest,
)
from app.modules.reviews.repository import ReviewRepository
from app.modules.users.models import User


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ReviewRepository(db)

    async def create_request(
        self, data: ReviewRequestCreate, tenant_id: UUID, created_by: UUID
    ) -> ReviewRequest:
        # Check if review already exists for this source and stage
        existing = await self.repository.get_request_by_source(
            ReviewType(data.source_object_type), data.source_object_id, data.stage, tenant_id
        )
        if existing:
            raise ConflictException(detail="Review request already exists for this source and stage")

        request = ReviewRequest(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=ReviewStatus.PENDING,
            stage=ReviewStage(data.stage) if data.stage else ReviewStage.DRAFT,
        )
        return await self.repository.create_request(request)

    async def get_request_by_id(self, request_id: UUID, tenant_id: UUID) -> ReviewRequest:
        request = await self.repository.get_request_by_id(request_id, tenant_id)
        if not request:
            raise NotFoundException(detail="Review request not found")
        return request

    async def get_all_requests(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[UUID] = None,
        stage: Optional[str] = None,
        status: Optional[str] = None,
        reviewer_id: Optional[UUID] = None,
        reviewer_team_id: Optional[UUID] = None,
        submitted_by_id: Optional[UUID] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[ReviewRequest], int]:
        source_type_enum = None
        if source_type:
            try:
                source_type_enum = ReviewType(source_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid source_type: {source_type}")

        stage_enum = None
        if stage:
            try:
                stage_enum = ReviewStage(stage)
            except ValueError:
                raise ValidationException(detail=f"Invalid stage: {stage}")

        status_enum = None
        if status:
            try:
                status_enum = ReviewStatus(status)
            except ValueError:
                raise ValidationException(detail=f"Invalid status: {status}")

        return await self.repository.get_all_requests(
            tenant_id,
            page,
            page_size,
            search,
            source_type_enum,
            source_id,
            stage_enum,
            status_enum,
            reviewer_id,
            reviewer_team_id,
            submitted_by_id,
            due_date_from,
            due_date_to,
            sort_by,
            sort_order,
        )

    async def update_request(
        self, request_id: UUID, tenant_id: UUID, data: ReviewRequestUpdate, updated_by: UUID
    ) -> ReviewRequest:
        request = await self.get_request_by_id(request_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field in ["stage", "status"] and value:
                continue  # Don't allow direct stage/status updates
            setattr(request, field, value)
        request.updated_by = updated_by
        return await self.repository.update_request(request)

    async def submit_for_review(
        self, request_id: UUID, tenant_id: UUID, actor_id: UUID, comment: Optional[str] = None
    ) -> ReviewRequest:
        request = await self.get_request_by_id(request_id, tenant_id)

        if request.stage != ReviewStage.DRAFT:
            raise ValidationException(detail="Review request is not in draft stage")

        if not request.reviewer_id and not request.reviewer_team_id:
            raise ValidationException(detail="No reviewer assigned")

        request.stage = ReviewStage.SUBMITTED
        request.status = ReviewStatus.IN_PROGRESS
        request.submitted_by_id = actor_id
        request.submitted_at = datetime.now(timezone.utc)
        request.updated_by = actor_id

        await self.repository.update_request(request)

        # Create history
        history = ReviewHistory(
            review_request_id=request.id,
            actor_id=actor_id,
            action="submit",
            from_stage=ReviewStage.DRAFT.value,
            to_stage=ReviewStage.SUBMITTED.value,
            from_status=ReviewStatus.PENDING.value,
            to_status=ReviewStatus.IN_PROGRESS.value,
            comment=comment,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return request

    async def approve(
        self, request_id: UUID, tenant_id: UUID, actor_id: UUID, comment: Optional[str] = None
    ) -> ReviewRequest:
        request = await self.get_request_by_id(request_id, tenant_id)

        if request.stage not in [ReviewStage.SUBMITTED, ReviewStage.UNDER_REVIEW, ReviewStage.REWORK]:
            raise ValidationException(detail=f"Cannot approve from stage {request.stage}")

        if request.reviewer_id and request.reviewer_id != actor_id:
            raise ValidationException(detail="Only assigned reviewer can approve")

        from_stage = request.stage
        request.stage = ReviewStage.APPROVED
        request.status = ReviewStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.updated_by = actor_id

        await self.repository.update_request(request)

        history = ReviewHistory(
            review_request_id=request.id,
            actor_id=actor_id,
            action="approve",
            from_stage=from_stage.value,
            to_stage=ReviewStage.APPROVED.value,
            from_status=request.status.value,
            to_status=ReviewStatus.COMPLETED.value,
            comment=comment,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        # Trigger workflow transition if linked
        if request.workflow_instance_id:
            from app.modules.workflow.service import WorkflowService
            workflow_service = WorkflowService(self.db)
            try:
                await workflow_service.transition(
                    request.workflow_instance_id,
                    tenant_id,
                    type('obj', (object,), {'transition_code': 'approve', 'comment': comment, 'reason': None, 'metadata': {}})(),
                    actor_id,
                )
            except Exception:
                pass  # Log but don't fail the approval

        return request

    async def reject(
        self, request_id: UUID, tenant_id: UUID, actor_id: UUID, comment: Optional[str] = None
    ) -> ReviewRequest:
        request = await self.get_request_by_id(request_id, tenant_id)

        if request.stage not in [ReviewStage.SUBMITTED, ReviewStage.UNDER_REVIEW, ReviewStage.REWORK]:
            raise ValidationException(detail=f"Cannot reject from stage {request.stage}")

        if request.reviewer_id and request.reviewer_id != actor_id:
            raise ValidationException(detail="Only assigned reviewer can reject")

        from_stage = request.stage
        request.stage = ReviewStage.REJECTED
        request.status = ReviewStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.updated_by = actor_id

        await self.repository.update_request(request)

        history = ReviewHistory(
            review_request_id=request.id,
            actor_id=actor_id,
            action="reject",
            from_stage=from_stage.value,
            to_stage=ReviewStage.REJECTED.value,
            from_status=request.status.value,
            to_status=ReviewStatus.COMPLETED.value,
            comment=comment,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        if request.workflow_instance_id:
            from app.modules.workflow.service import WorkflowService
            workflow_service = WorkflowService(self.db)
            try:
                await workflow_service.transition(
                    request.workflow_instance_id,
                    tenant_id,
                    type('obj', (object,), {'transition_code': 'reject', 'comment': comment, 'reason': None, 'metadata': {}})(),
                    actor_id,
                )
            except Exception:
                pass

        return request

    async def request_rework(
        self, request_id: UUID, tenant_id: UUID, actor_id: UUID, comment: Optional[str] = None
    ) -> ReviewRequest:
        request = await self.get_request_by_id(request_id, tenant_id)

        if request.stage not in [ReviewStage.SUBMITTED, ReviewStage.UNDER_REVIEW, ReviewStage.REWORK]:
            raise ValidationException(detail=f"Cannot request rework from stage {request.stage}")

        if request.reviewer_id and request.reviewer_id != actor_id:
            raise ValidationException(detail="Only assigned reviewer can request rework")

        from_stage = request.stage
        request.stage = ReviewStage.REWORK
        request.status = ReviewStatus.IN_PROGRESS
        request.updated_by = actor_id

        await self.repository.update_request(request)

        history = ReviewHistory(
            review_request_id=request.id,
            actor_id=actor_id,
            action="request_rework",
            from_stage=from_stage.value,
            to_stage=ReviewStage.REWORK.value,
            from_status=request.status.value,
            to_status=ReviewStatus.IN_PROGRESS.value,
            comment=comment,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        if request.workflow_instance_id:
            from app.modules.workflow.service import WorkflowService
            workflow_service = WorkflowService(self.db)
            try:
                await workflow_service.transition(
                    request.workflow_instance_id,
                    tenant_id,
                    type('obj', (object,), {'transition_code': 'rework', 'comment': comment, 'reason': None, 'metadata': {}})(),
                    actor_id,
                )
            except Exception:
                pass

        return request

    async def escalate(
        self, request_id: UUID, tenant_id: UUID, actor_id: UUID, comment: Optional[str] = None, metadata: Optional[dict] = None
    ) -> ReviewRequest:
        request = await self.get_request_by_id(request_id, tenant_id)

        from_stage = request.stage
        request.stage = ReviewStage.ESCALATED
        request.updated_by = actor_id
        if metadata:
            request.metadata.update(metadata)

        await self.repository.update_request(request)

        history = ReviewHistory(
            review_request_id=request.id,
            actor_id=actor_id,
            action="escalate",
            from_stage=from_stage.value,
            to_stage=ReviewStage.ESCALATED.value,
            comment=comment,
            extra_metadata=metadata or {},
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return request

    async def execute_action(
        self, request_id: UUID, tenant_id: UUID, action_data: ReviewActionRequest, actor_id: UUID
    ) -> ReviewRequest:
        action = action_data.action.lower()
        if action == "submit":
            return await self.submit_for_review(request_id, tenant_id, actor_id, action_data.comment)
        elif action == "approve":
            return await self.approve(request_id, tenant_id, actor_id, action_data.comment)
        elif action == "reject":
            return await self.reject(request_id, tenant_id, actor_id, action_data.comment)
        elif action == "request_rework":
            return await self.request_rework(request_id, tenant_id, actor_id, action_data.comment)
        elif action == "escalate":
            return await self.escalate(request_id, tenant_id, actor_id, action_data.comment, action_data.metadata)
        else:
            raise ValidationException(detail=f"Invalid action: {action}")

    # Comment methods
    async def add_comment(
        self, request_id: UUID, data: ReviewCommentCreate, tenant_id: UUID, author_id: UUID
    ) -> ReviewComment:
        request = await self.get_request_by_id(request_id, tenant_id)

        comment = ReviewComment(
            review_request_id=request.id,
            **data.model_dump(),
            author_id=author_id,
            tenant_id=tenant_id,
            created_by=author_id,
        )
        created = await self.repository.create_comment(comment)

        # Create history entry
        history = ReviewHistory(
            review_request_id=request.id,
            actor_id=author_id,
            action="comment",
            comment=data.content,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return created

    async def get_comments(
        self,
        request_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ReviewComment], int]:
        request = await self.get_request_by_id(request_id, tenant_id)
        return await self.repository.get_comments_for_request(request_id, tenant_id, page, page_size)

    async def update_comment(
        self, comment_id: UUID, tenant_id: UUID, data: ReviewCommentUpdate, updated_by: UUID
    ) -> ReviewComment:
        comment = await self.repository.get_comment_by_id(comment_id, tenant_id)
        if not comment:
            raise NotFoundException(detail="Comment not found")

        if comment.author_id != updated_by:
            raise ValidationException(detail="Only author can update comment")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(comment, field, value)
        comment.updated_by = updated_by
        return await self.repository.update_comment(comment)

    async def delete_comment(self, comment_id: UUID, tenant_id: UUID, actor_id: UUID) -> None:
        comment = await self.repository.get_comment_by_id(comment_id, tenant_id)
        if not comment:
            raise NotFoundException(detail="Comment not found")

        if comment.author_id != actor_id:
            raise ValidationException(detail="Only author can delete comment")

        await self.repository.delete_comment(comment)

    async def get_history(
        self,
        request_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ReviewHistory], int]:
        request = await self.get_request_by_id(request_id, tenant_id)
        return await self.repository.get_history_for_request(request_id, tenant_id, page, page_size)