from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.audit_workspace.schemas import (
    AuditEngagementCreate,
    AuditEngagementDetailResponse,
    AuditEngagementListResponse,
    AuditEngagementResponse,
    AuditEngagementTransitionRequest,
    AuditEngagementUpdate,
    AuditEvidenceCreate,
    AuditEvidenceDetailResponse,
    AuditEvidenceListResponse,
    AuditEvidenceResponse,
    AuditEvidenceUpdate,
    AuditReviewCreate,
    AuditReviewDetailResponse,
    AuditReviewListResponse,
    AuditReviewResponse,
    AuditReviewUpdate,
    AuditSignOffCreate,
    AuditSignOffDetailResponse,
    AuditSignOffListResponse,
    AuditSignOffResponse,
    AuditSignOffUpdate,
    AuditWorkingPaperCreate,
    AuditWorkingPaperDetailResponse,
    AuditWorkingPaperListResponse,
    AuditWorkingPaperResponse,
    AuditWorkingPaperUpdate,
    AuditSignOffCreate,
    AuditSignOffResponse,
    AuditSignOffUpdate,
)
from app.modules.audit_workspace.service import (
    AuditEngagementService,
    AuditWorkingPaperService,
    AuditEvidenceService,
    AuditReviewService,
    AuditSignOffService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/audit-workspace", tags=["Audit Workspace"])


# ============================================================================
# Audit Engagement Endpoints
# ============================================================================

@router.post("/engagements", response_model=AuditEngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_engagement(
    data: AuditEngagementCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_ENGAGEMENT_CREATE)),
):
    service = AuditEngagementService(db)
    engagement = await service.create(data, tenant_context.tenant_id, current_user.id)
    return AuditEngagementResponse.model_validate(engagement)


@router.get("/engagements", response_model=AuditEngagementListResponse)
async def list_audit_engagements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    client_id: UUID | None = None,
    status: str | None = None,
    engagement_type: str | None = None,
    engagement_partner_id: UUID | None = None,
    engagement_manager_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_ENGAGEMENT_READ)),
):
    service = AuditEngagementService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, client_id, status,
        engagement_type, engagement_partner_id, engagement_manager_id,
        date_from, date_to, sort_by, sort_order
    )
    return AuditEngagementListResponse(
        items=[AuditEngagementResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/engagements/{engagement_id}", response_model=AuditEngagementDetailResponse)
async def get_audit_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_ENGAGEMENT_READ)),
):
    service = AuditEngagementService(db)
    engagement = await service.get_by_id(engagement_id, tenant_context.tenant_id)
    return AuditEngagementDetailResponse.model_validate(engagement)


@router.patch("/engagements/{engagement_id}", response_model=AuditEngagementResponse)
async def update_audit_engagement(
    engagement_id: UUID,
    data: AuditEngagementUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_ENGAGEMENT_UPDATE)),
):
    service = AuditEngagementService(db)
    engagement = await service.update(engagement_id, tenant_context.tenant_id, data, current_user.id)
    return AuditEngagementResponse.model_validate(engagement)


@router.post("/engagements/{engagement_id}/transition", response_model=AuditEngagementResponse)
async def transition_engagement_status(
    engagement_id: UUID,
    data: AuditEngagementTransitionRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_ENGAGEMENT_TRANSITION)),
):
    service = AuditEngagementService(db)
    engagement = await service.transition_status(engagement_id, tenant_context.tenant_id, data, current_user.id)
    return AuditEngagementResponse.model_validate(engagement)


@router.delete("/engagements/{engagement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_ENGAGEMENT_DELETE)),
):
    service = AuditEngagementService(db)
    await service.delete(engagement_id, tenant_context.tenant_id)


# ============================================================================
# Working Paper Endpoints
# ============================================================================

@router.post("/engagements/{engagement_id}/working-papers", response_model=AuditWorkingPaperResponse, status_code=status.HTTP_201_CREATED)
async def create_working_paper(
    engagement_id: UUID,
    data: AuditWorkingPaperCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_WORKING_PAPER_CREATE)),
):
    service = AuditWorkingPaperService(db)
    wp = await service.create(data, tenant_context.tenant_id, current_user.id)
    return AuditWorkingPaperResponse.model_validate(wp)


@router.get("/engagements/{engagement_id}/working-papers", response_model=AuditWorkingPaperListResponse)
async def list_working_papers(
    engagement_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    working_paper_type: str | None = None,
    prepared_by_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_WORKING_PAPER_READ)),
):
    service = AuditWorkingPaperService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, engagement_id, status,
        working_paper_type, prepared_by_id, date_from, date_to, sort_by, sort_order
    )
    return AuditWorkingPaperListResponse(
        items=[AuditWorkingPaperResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/engagements/{engagement_id}/working-papers/{wp_id}", response_model=AuditWorkingPaperDetailResponse)
async def get_working_paper(
    engagement_id: UUID,
    wp_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_WORKING_PAPER_READ)),
):
    service = AuditWorkingPaperService(db)
    wp = await service.get_by_id(wp_id, tenant_context.tenant_id)
    return AuditWorkingPaperDetailResponse.model_validate(wp)


@router.patch("/engagements/{engagement_id}/working-papers/{wp_id}", response_model=AuditWorkingPaperResponse)
async def update_working_paper(
    engagement_id: UUID,
    wp_id: UUID,
    data: AuditWorkingPaperUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_WORKING_PAPER_UPDATE)),
):
    service = AuditWorkingPaperService(db)
    wp = await service.update(wp_id, tenant_context.tenant_id, data, current_user.id)
    return AuditWorkingPaperResponse.model_validate(wp)


@router.post("/engagements/{engagement_id}/working-papers/{wp_id}/submit-for-review", response_model=AuditWorkingPaperResponse)
async def submit_working_paper_for_review(
    engagement_id: UUID,
    wp_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_WORKING_PAPER_UPDATE)),
):
    service = AuditWorkingPaperService(db)
    wp = await service.submit_for_review(wp_id, tenant_context.tenant_id, current_user.id)
    return AuditWorkingPaperResponse.model_validate(wp)


@router.delete("/engagements/{engagement_id}/working-papers/{wp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_working_paper(
    engagement_id: UUID,
    wp_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_WORKING_PAPER_DELETE)),
):
    service = AuditWorkingPaperService(db)
    await service.delete(wp_id, tenant_context.tenant_id)


# ============================================================================
# Evidence Endpoints
# ============================================================================

@router.post("/engagements/{engagement_id}/evidence", response_model=AuditEvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    engagement_id: UUID,
    data: AuditEvidenceCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_EVIDENCE_CREATE)),
):
    service = AuditEvidenceService(db)
    evidence = await service.create(data, tenant_context.tenant_id, current_user.id)
    return AuditEvidenceResponse.model_validate(evidence)


@router.get("/engagements/{engagement_id}/evidence", response_model=AuditEvidenceListResponse)
async def list_evidence(
    engagement_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    working_paper_id: UUID | None = None,
    status: str | None = None,
    evidence_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_EVIDENCE_READ)),
):
    service = AuditEvidenceService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, engagement_id, working_paper_id,
        status, evidence_type, date_from, date_to, sort_by, sort_order
    )
    return AuditEvidenceListResponse(
        items=[AuditEvidenceResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/engagements/{engagement_id}/evidence/{evidence_id}", response_model=AuditEvidenceDetailResponse)
async def get_evidence(
    engagement_id: UUID,
    evidence_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_EVIDENCE_READ)),
):
    service = AuditEvidenceService(db)
    evidence = await service.get_by_id(evidence_id, tenant_context.tenant_id)
    return AuditEvidenceDetailResponse.model_validate(evidence)


@router.patch("/engagements/{engagement_id}/evidence/{evidence_id}", response_model=AuditEvidenceResponse)
async def update_evidence(
    engagement_id: UUID,
    evidence_id: UUID,
    data: AuditEvidenceUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_EVIDENCE_UPDATE)),
):
    service = AuditEvidenceService(db)
    evidence = await service.update(evidence_id, tenant_context.tenant_id, data, current_user.id)
    return AuditEvidenceResponse.model_validate(evidence)


@router.delete("/engagements/{engagement_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    engagement_id: UUID,
    evidence_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_EVIDENCE_DELETE)),
):
    service = AuditEvidenceService(db)
    await service.delete(evidence_id, tenant_context.tenant_id)


# ============================================================================
# Review Endpoints
# ============================================================================

@router.post("/engagements/{engagement_id}/reviews", response_model=AuditReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    engagement_id: UUID,
    data: AuditReviewCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_REVIEW_CREATE)),
):
    service = AuditReviewService(db)
    review = await service.create(data, tenant_context.tenant_id, current_user.id)
    return AuditReviewResponse.model_validate(review)


@router.get("/engagements/{engagement_id}/reviews", response_model=AuditReviewListResponse)
async def list_reviews(
    engagement_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    working_paper_id: UUID | None = None,
    evidence_id: UUID | None = None,
    reviewer_id: UUID | None = None,
    status: str | None = None,
    review_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_REVIEW_READ)),
):
    service = AuditReviewService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, engagement_id, working_paper_id,
        evidence_id, reviewer_id, status, review_type, date_from, date_to, sort_by, sort_order
    )
    return AuditReviewListResponse(
        items=[AuditReviewResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/engagements/{engagement_id}/reviews/{review_id}", response_model=AuditReviewDetailResponse)
async def get_review(
    engagement_id: UUID,
    review_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_REVIEW_READ)),
):
    service = AuditReviewService(db)
    review = await service.get_by_id(review_id, tenant_context.tenant_id)
    return AuditReviewDetailResponse.model_validate(review)


@router.patch("/engagements/{engagement_id}/reviews/{review_id}", response_model=AuditReviewResponse)
async def update_review(
    engagement_id: UUID,
    review_id: UUID,
    data: AuditReviewUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_REVIEW_UPDATE)),
):
    service = AuditReviewService(db)
    review = await service.update(review_id, tenant_context.tenant_id, data, current_user.id)
    return AuditReviewResponse.model_validate(review)


@router.post("/engagements/{engagement_id}/reviews/{review_id}/start", response_model=AuditReviewResponse)
async def start_review(
    engagement_id: UUID,
    review_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_REVIEW_UPDATE)),
):
    service = AuditReviewService(db)
    review = await service.start_review(review_id, tenant_context.tenant_id, current_user.id)
    return AuditReviewResponse.model_validate(review)


@router.post("/engagements/{engagement_id}/reviews/{review_id}/complete", response_model=AuditReviewResponse)
async def complete_review(
    engagement_id: UUID,
    review_id: UUID,
    status: str,
    findings: str | None = None,
    recommendations: str | None = None,
    notes: str | None = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_REVIEW_TRANSITION)),
):
    service = AuditReviewService(db)
    review = await service.complete_review(review_id, tenant_context.tenant_id, status, current_user.id, findings, recommendations, notes)
    return AuditReviewResponse.model_validate(review)


@router.delete("/engagements/{engagement_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    engagement_id: UUID,
    review_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_REVIEW_DELETE)),
):
    service = AuditReviewService(db)
    await service.delete(review_id, tenant_context.tenant_id)


# ============================================================================
# Sign-Off Endpoints
# ============================================================================

@router.post("/engagements/{engagement_id}/sign-offs", response_model=AuditSignOffResponse, status_code=status.HTTP_201_CREATED)
async def create_sign_off(
    engagement_id: UUID,
    data: AuditSignOffCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_SIGN_OFF_CREATE)),
):
    service = AuditSignOffService(db)
    sign_off = await service.create(data, tenant_context.tenant_id, current_user.id)
    return AuditSignOffResponse.model_validate(sign_off)


@router.get("/engagements/{engagement_id}/sign-offs", response_model=AuditSignOffListResponse)
async def list_sign_offs(
    engagement_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    signer_id: UUID | None = None,
    status: str | None = None,
    sign_off_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_SIGN_OFF_READ)),
):
    service = AuditSignOffService(db)
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, engagement_id, signer_id,
        status, sign_off_type, date_from, date_to, sort_by, sort_order
    )
    return AuditSignOffListResponse(
        items=[AuditSignOffResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/engagements/{engagement_id}/sign-offs/{sign_off_id}", response_model=AuditSignOffDetailResponse)
async def get_sign_off(
    engagement_id: UUID,
    sign_off_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_SIGN_OFF_READ)),
):
    service = AuditSignOffService(db)
    sign_off = await service.get_by_id(sign_off_id, tenant_context.tenant_id)
    return AuditSignOffDetailResponse.model_validate(sign_off)


@router.patch("/engagements/{engagement_id}/sign-offs/{sign_off_id}", response_model=AuditSignOffResponse)
async def update_sign_off(
    engagement_id: UUID,
    sign_off_id: UUID,
    data: AuditSignOffUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_SIGN_OFF_UPDATE)),
):
    service = AuditSignOffService(db)
    sign_off = await service.update(sign_off_id, tenant_context.tenant_id, data, current_user.id)
    return AuditSignOffResponse.model_validate(sign_off)


@router.post("/engagements/{engagement_id}/sign-offs/{sign_off_id}/sign", response_model=AuditSignOffResponse)
async def sign_off(
    engagement_id: UUID,
    sign_off_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_SIGN_OFF_CREATE)),
):
    service = AuditSignOffService(db)
    sign_off = await service.sign(sign_off_id, tenant_context.tenant_id, current_user.id)
    return AuditSignOffResponse.model_validate(sign_off)


@router.delete("/engagements/{engagement_id}/sign-offs/{sign_off_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sign_off(
    engagement_id: UUID,
    sign_off_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.AUDIT_SIGN_OFF_DELETE)),
):
    service = AuditSignOffService(db)
    await service.delete(sign_off_id, tenant_context.tenant_id)