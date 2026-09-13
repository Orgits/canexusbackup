from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import get_tenant_context
from app.core.security.dependencies import get_current_user
from app.core.permissions.dependencies import require_permission
from app.modules.reviews.service import ReviewService
from app.modules.reviews.schemas import (
    ReviewRequestCreate,
    ReviewRequestUpdate,
    ReviewRequestResponse,
    ReviewRequestDetailResponse,
    ReviewRequestListResponse,
    ReviewActionRequest,
    ReviewCommentCreate,
    ReviewCommentUpdate,
    ReviewCommentResponse,
    ReviewCommentListResponse,
    ReviewHistoryResponse,
    ReviewHistoryListResponse,
)
from app.modules.users.models import User

router = APIRouter(prefix="/reviews", tags=["Review & Approval Engine"])


def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    return ReviewService(db)


# Review Request endpoints
@router.post(
    "",
    response_model=ReviewRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review request",
)
async def create_review_request(
    data: ReviewRequestCreate,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.create")),
):
    return await review_service.create_request(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "",
    response_model=ReviewRequestListResponse,
    summary="List review requests",
)
async def list_review_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.read")),
):
    items, total = await review_service.get_all_requests(
        tenant_context.tenant_id,
        page,
        page_size,
        search,
        source_type,
        source_id,
        stage,
        status,
        reviewer_id,
        reviewer_team_id,
        submitted_by_id,
        due_date_from,
        due_date_to,
        sort_by,
        sort_order,
    )
    return ReviewRequestListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/{request_id}",
    response_model=ReviewRequestDetailResponse,
    summary="Get review request by ID",
)
async def get_review_request(
    request_id: UUID,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.read")),
):
    return await review_service.get_request_by_id(request_id, tenant_context.tenant_id)


@router.patch(
    "/{request_id}",
    response_model=ReviewRequestResponse,
    summary="Update review request",
)
async def update_review_request(
    request_id: UUID,
    data: ReviewRequestUpdate,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.update")),
):
    return await review_service.update_request(request_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review request",
)
async def delete_review_request(
    request_id: UUID,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.delete")),
):
    request = await review_service.get_request_by_id(request_id, tenant_context.tenant_id)
    await review_service.repository.delete_request(request)


@router.post(
    "/{request_id}/action",
    response_model=ReviewRequestResponse,
    summary="Execute review action (submit, approve, reject, rework, escalate)",
)
async def execute_review_action(
    request_id: UUID,
    action_data: ReviewActionRequest,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.transition")),
):
    return await review_service.execute_action(request_id, tenant_context.tenant_id, action_data, current_user.id)


# Review Comment endpoints
@router.post(
    "/{request_id}/comments",
    response_model=ReviewCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to review request",
)
async def add_review_comment(
    request_id: UUID,
    data: ReviewCommentCreate,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.comment")),
):
    return await review_service.add_comment(request_id, data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/{request_id}/comments",
    response_model=ReviewCommentListResponse,
    summary="Get comments for review request",
)
async def get_review_comments(
    request_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.read")),
):
    items, total = await review_service.get_comments(request_id, tenant_context.tenant_id, page, page_size)
    return ReviewCommentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.patch(
    "/comments/{comment_id}",
    response_model=ReviewCommentResponse,
    summary="Update review comment",
)
async def update_review_comment(
    comment_id: UUID,
    data: ReviewCommentUpdate,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.comment")),
):
    return await review_service.update_comment(comment_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review comment",
)
async def delete_review_comment(
    comment_id: UUID,
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.comment")),
):
    await review_service.delete_comment(comment_id, tenant_context.tenant_id, current_user.id)


# Review History endpoints
@router.get(
    "/{request_id}/history",
    response_model=ReviewHistoryListResponse,
    summary="Get review history",
)
async def get_review_history(
    request_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    review_service: ReviewService = Depends(get_review_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("reviews.read")),
):
    items, total = await review_service.get_history(request_id, tenant_context.tenant_id, page, page_size)
    return ReviewHistoryListResponse(items=items, total=total, page=page, page_size=page_size)