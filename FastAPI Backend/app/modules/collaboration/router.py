from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.security.dependencies import get_current_user
from app.core.tenancy import get_tenant_context
from app.modules.collaboration.schemas import (
    CommentAttachmentCreate,
    CommentAttachmentResponse,
    CommentCreate,
    CommentListResponse,
    CommentReactionResponse,
    CommentResponse,
    CommentThreadResponse,
    CommentUpdate,
)
from app.modules.collaboration.service import CollaborationService
from app.modules.users.models import User

router = APIRouter(prefix="/collaboration", tags=["Collaboration & Comments"])


def get_collaboration_service(db: AsyncSession = Depends(get_tenant_db_session)) -> CollaborationService:
    return CollaborationService(db)


# Comment endpoints
@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create comment",
)
async def create_comment(
    data: CommentCreate,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.comment")),
):
    return await collab_service.create_comment(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "",
    response_model=CommentListResponse,
    summary="Get comments for entity",
)
async def get_comments(
    entity_type: str = Query(..., description="Entity type (matter, task, document, notice, review, client, compliance_cycle, mca_cycle, tds_cycle)"),
    entity_id: UUID = Query(..., description="Entity ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    include_replies: bool = Query(False, description="Include reply threads"),
    comment_type: str | None = Query(None, description="Filter by comment type (comment, internal_note, mention, system)"),
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.read")),
):
    items, total = await collab_service.get_comments(
        entity_type, entity_id, tenant_context.tenant_id, page, page_size, include_replies, comment_type
    )
    return CommentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/thread/{comment_id}",
    response_model=CommentThreadResponse,
    summary="Get comment thread (parent + all replies)",
)
async def get_comment_thread(
    comment_id: UUID,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.read")),
):
    comments = await collab_service.get_comment_thread(comment_id, tenant_context.tenant_id)
    return CommentThreadResponse(
        comments=comments,
        total=len(comments),
        page=1,
        page_size=len(comments),
    )


@router.get(
    "/{comment_id}",
    response_model=CommentResponse,
    summary="Get comment by ID",
)
async def get_comment(
    comment_id: UUID,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.read")),
):
    return await collab_service.get_comment(comment_id, tenant_context.tenant_id)


@router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
    summary="Update comment",
)
async def update_comment(
    comment_id: UUID,
    data: CommentUpdate,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.comment")),
):
    return await collab_service.update_comment(comment_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment",
)
async def delete_comment(
    comment_id: UUID,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.comment")),
):
    await collab_service.delete_comment(comment_id, tenant_context.tenant_id, current_user.id)


# Attachment endpoints
@router.post(
    "/{comment_id}/attachments",
    response_model=CommentAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add attachment to comment",
)
async def add_comment_attachment(
    comment_id: UUID,
    data: CommentAttachmentCreate,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.comment")),
):
    return await collab_service.add_attachment(comment_id, data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/{comment_id}/attachments",
    response_model=list[CommentAttachmentResponse],
    summary="Get comment attachments",
)
async def get_comment_attachments(
    comment_id: UUID,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.read")),
):
    return await collab_service.get_attachments(comment_id, tenant_context.tenant_id)


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment attachment",
)
async def delete_comment_attachment(
    attachment_id: UUID,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.comment")),
):
    await collab_service.delete_attachment(attachment_id, tenant_context.tenant_id, current_user.id)


# Reaction endpoints
@router.post(
    "/{comment_id}/reactions",
    response_model=CommentReactionResponse,
    summary="Toggle reaction on comment",
)
async def toggle_comment_reaction(
    comment_id: UUID,
    reaction_type: str = Query(..., description="Reaction type (like, thumbs_up, heart, etc.)"),
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.comment")),
):
    reaction, created = await collab_service.toggle_reaction(
        comment_id, reaction_type, tenant_context.tenant_id, current_user.id
    )
    return reaction


@router.get(
    "/{comment_id}/reactions",
    response_model=list[CommentReactionResponse],
    summary="Get comment reactions",
)
async def get_comment_reactions(
    comment_id: UUID,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.read")),
):
    return await collab_service.get_reactions(comment_id, tenant_context.tenant_id)


@router.delete(
    "/{comment_id}/reactions/{reaction_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove reaction from comment",
)
async def remove_comment_reaction(
    comment_id: UUID,
    reaction_type: str,
    collab_service: CollaborationService = Depends(get_collaboration_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("collaboration.comment")),
):
    await collab_service.remove_reaction(comment_id, reaction_type, tenant_context.tenant_id, current_user.id)
