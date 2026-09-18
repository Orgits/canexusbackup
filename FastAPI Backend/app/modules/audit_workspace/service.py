from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.audit_workspace.models import (
    AuditEngagement,
    AuditEngagementStatus,
    AuditWorkingPaper,
    AuditEvidence,
    AuditReview,
    AuditSignOff,
    WorkingPaperStatus,
    EvidenceStatus,
    AuditReviewStatus,
    SignOffStatus,
    AuditEngagementType,
)
from app.modules.audit_workspace.repository import (
    AuditEngagementRepository,
    AuditWorkingPaperRepository,
    AuditEvidenceRepository,
    AuditReviewRepository,
    AuditSignOffRepository,
)
from app.modules.audit_workspace.schemas import (
    AuditEngagementCreate,
    AuditEngagementUpdate,
    AuditEngagementTransitionRequest,
    AuditWorkingPaperCreate,
    AuditWorkingPaperUpdate,
    AuditEvidenceCreate,
    AuditEvidenceUpdate,
    AuditReviewCreate,
    AuditReviewUpdate,
    AuditSignOffCreate,
    AuditSignOffUpdate,
)
from app.modules.clients.models import Client
from app.modules.users.models import User
from app.modules.documents.models import Document


class AuditEngagementService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditEngagementRepository(db)

    async def create(self, data: AuditEngagementCreate, tenant_id: UUID, created_by: UUID) -> AuditEngagement:
        # Validate client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        # Validate engagement partner if provided
        if data.engagement_partner_id:
            partner_result = await self.db.execute(
                select(User).where(User.id == data.engagement_partner_id, User.tenant_id == tenant_id)
            )
            if not partner_result.scalar_one_or_none():
                raise NotFoundException(detail="Engagement partner not found")

        # Validate engagement manager if provided
        if data.engagement_manager_id:
            manager_result = await self.db.execute(
                select(User).where(User.id == data.engagement_manager_id, User.tenant_id == tenant_id)
            )
            if not manager_result.scalar_one_or_none():
                raise NotFoundException(detail="Engagement manager not found")

        # Check for duplicate engagement number
        existing = await self.repository.get_by_number(data.engagement_number, tenant_id)
        if existing:
            raise ValidationException(detail="Engagement with this number already exists")

        engagement = AuditEngagement(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=AuditEngagementStatus.PLANNING,
        )
        return await self.repository.create(engagement)

    async def get_by_id(self, engagement_id: UUID, tenant_id: UUID) -> AuditEngagement:
        engagement = await self.repository.get_by_id(engagement_id, tenant_id)
        if not engagement:
            raise NotFoundException(detail="Audit engagement not found")
        return engagement

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        status: str | None = None,
        engagement_type: str | None = None,
        engagement_partner_id: UUID | None = None,
        engagement_manager_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, client_id, status, engagement_type,
            engagement_partner_id, engagement_manager_id, date_from, date_to, sort_by, sort_order
        )

    async def update(self, engagement_id: UUID, tenant_id: UUID, data: AuditEngagementUpdate, updated_by: UUID) -> AuditEngagement:
        engagement = await self.get_by_id(engagement_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == AuditEngagementStatus.COMPLETED.value and engagement.status != AuditEngagementStatus.COMPLETED.value:
                engagement.completed_at = datetime.now()
                engagement.completed_by = updated_by
            elif new_status == AuditEngagementStatus.ACTIVE.value and engagement.status == AuditEngagementStatus.PLANNING.value:
                # Starting fieldwork
                pass

        for field, value in update_data.items():
            setattr(engagement, field, value)

        engagement.updated_by = updated_by
        return await self.repository.update(engagement)

    async def transition_status(self, engagement_id: UUID, tenant_id: UUID, data: AuditEngagementTransitionRequest, updated_by: UUID) -> AuditEngagement:
        engagement = await self.get_by_id(engagement_id, tenant_id)
        new_status = data.new_status

        # Validate status transition
        valid_transitions = {
            AuditEngagementStatus.PLANNING.value: [AuditEngagementStatus.ACTIVE.value, AuditEngagementStatus.CANCELLED.value],
            AuditEngagementStatus.ACTIVE.value: [AuditEngagementStatus.IN_REVIEW.value, AuditEngagementStatus.CANCELLED.value],
            AuditEngagementStatus.IN_REVIEW.value: [AuditEngagementStatus.COMPLETED.value, AuditEngagementStatus.ACTIVE.value, AuditEngagementStatus.CANCELLED.value],
            AuditEngagementStatus.COMPLETED.value: [AuditEngagementStatus.ARCHIVED.value],
            AuditEngagementStatus.ARCHIVED.value: [],
            AuditEngagementStatus.CANCELLED.value: [],
        }

        current_status = engagement.status
        if new_status not in valid_transitions.get(current_status, []):
            raise ValidationException(detail=f"Invalid status transition from {current_status} to {new_status}")

        engagement.status = new_status
        engagement.updated_by = updated_by

        if new_status == AuditEngagementStatus.COMPLETED.value:
            engagement.completed_at = datetime.now()
            engagement.completed_by = updated_by

        return await self.repository.update(engagement)

    async def delete(self, engagement_id: UUID, tenant_id: UUID) -> None:
        engagement = await self.get_by_id(engagement_id, tenant_id)
        await self.repository.delete(engagement)


class AuditWorkingPaperService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditWorkingPaperRepository(db)

    async def create(self, data: AuditWorkingPaperCreate, tenant_id: UUID, created_by: UUID) -> AuditWorkingPaper:
        # Validate engagement exists
        engagement_result = await self.db.execute(
            select(AuditEngagement).where(AuditEngagement.id == data.engagement_id, AuditEngagement.tenant_id == tenant_id)
        )
        if not engagement_result.scalar_one_or_none():
            raise NotFoundException(detail="Audit engagement not found")

        # Validate prepared_by if provided
        if data.prepared_by_id:
            user_result = await self.db.execute(
                select(User).where(User.id == data.prepared_by_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="Prepared by user not found")

        wp = AuditWorkingPaper(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=WorkingPaperStatus.DRAFT,
        )
        return await self.repository.create(wp)

    async def get_by_id(self, wp_id: UUID, tenant_id: UUID) -> AuditWorkingPaper:
        wp = await self.repository.get_by_id(wp_id, tenant_id)
        if not wp:
            raise NotFoundException(detail="Working paper not found")
        return wp

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engagement_id: UUID | None = None,
        status: str | None = None,
        working_paper_type: str | None = None,
        prepared_by_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, engagement_id, status, working_paper_type,
            prepared_by_id, date_from, date_to, sort_by, sort_order
        )

    async def update(self, wp_id: UUID, tenant_id: UUID, data: AuditWorkingPaperUpdate, updated_by: UUID) -> AuditWorkingPaper:
        wp = await self.get_by_id(wp_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == WorkingPaperStatus.READY_FOR_REVIEW.value:
                wp.reviewed_at = None
            elif new_status == WorkingPaperStatus.REVIEWED.value:
                wp.reviewed_at = datetime.now()
                wp.reviewed_by_id = updated_by
            elif new_status == WorkingPaperStatus.APPROVED.value:
                wp.reviewed_at = datetime.now()
                wp.reviewed_by_id = updated_by

        for field, value in update_data.items():
            setattr(wp, field, value)

        wp.updated_by = updated_by
        return await self.repository.update(wp)

    async def submit_for_review(self, wp_id: UUID, tenant_id: UUID, submitted_by: UUID) -> AuditWorkingPaper:
        wp = await self.get_by_id(wp_id, tenant_id)
        if wp.status != WorkingPaperStatus.IN_PROGRESS.value:
            raise ValidationException(detail="Only in-progress working papers can be submitted for review")
        wp.status = WorkingPaperStatus.READY_FOR_REVIEW.value
        wp.updated_by = submitted_by
        return await self.repository.update(wp)

    async def delete(self, wp_id: UUID, tenant_id: UUID) -> None:
        wp = await self.get_by_id(wp_id, tenant_id)
        await self.repository.delete(wp)


class AuditEvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditEvidenceRepository(db)

    async def create(self, data: AuditEvidenceCreate, tenant_id: UUID, created_by: UUID) -> AuditEvidence:
        # Validate engagement
        engagement_result = await self.db.execute(
            select(AuditEngagement).where(AuditEngagement.id == data.engagement_id, AuditEngagement.tenant_id == tenant_id)
        )
        if not engagement_result.scalar_one_or_none():
            raise NotFoundException(detail="Audit engagement not found")

        # Validate working paper if provided
        if data.working_paper_id:
            wp_result = await self.db.execute(
                select(AuditWorkingPaper).where(AuditWorkingPaper.id == data.working_paper_id, AuditWorkingPaper.tenant_id == tenant_id)
            )
            if not wp_result.scalar_one_or_none():
                raise NotFoundException(detail="Working paper not found")

        # Validate document if provided
        if data.document_id:
            doc_result = await self.db.execute(
                select(Document).where(Document.id == data.document_id, Document.tenant_id == tenant_id)
            )
            if not doc_result.scalar_one_or_none():
                raise NotFoundException(detail="Document not found")

        # Validate collected_by if provided
        if data.collected_by_id:
            user_result = await self.db.execute(
                select(User).where(User.id == data.collected_by_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="Collected by user not found")

        evidence = AuditEvidence(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=EvidenceStatus.COLLECTED,
        )
        return await self.repository.create(evidence)

    async def get_by_id(self, evidence_id: UUID, tenant_id: UUID) -> AuditEvidence:
        evidence = await self.repository.get_by_id(evidence_id, tenant_id)
        if not evidence:
            raise NotFoundException(detail="Evidence not found")
        return evidence

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engagement_id: UUID | None = None,
        working_paper_id: UUID | None = None,
        status: str | None = None,
        evidence_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, engagement_id, working_paper_id,
            status, evidence_type, date_from, date_to, sort_by, sort_order
        )

    async def update(self, evidence_id: UUID, tenant_id: UUID, data: AuditEvidenceUpdate, updated_by: UUID) -> AuditEvidence:
        evidence = await self.get_by_id(evidence_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == EvidenceStatus.UNDER_REVIEW.value:
                evidence.reviewed_at = None
            elif new_status in [EvidenceStatus.ACCEPTED.value, EvidenceStatus.REJECTED.value, EvidenceStatus.INSUFFICIENT.value]:
                evidence.reviewed_at = datetime.now()
                evidence.reviewed_by_id = updated_by

        for field, value in update_data.items():
            setattr(evidence, field, value)

        evidence.updated_by = updated_by
        return await self.repository.update(evidence)

    async def delete(self, evidence_id: UUID, tenant_id: UUID) -> None:
        evidence = await self.get_by_id(evidence_id, tenant_id)
        await self.repository.delete(evidence)


class AuditReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditReviewRepository(db)

    async def create(self, data: AuditReviewCreate, tenant_id: UUID, created_by: UUID) -> AuditReview:
        # Validate engagement
        engagement_result = await self.db.execute(
            select(AuditEngagement).where(AuditEngagement.id == data.engagement_id, AuditEngagement.tenant_id == tenant_id)
        )
        if not engagement_result.scalar_one_or_none():
            raise NotFoundException(detail="Audit engagement not found")

        # Validate working paper if provided
        if data.working_paper_id:
            wp_result = await self.db.execute(
                select(AuditWorkingPaper).where(AuditWorkingPaper.id == data.working_paper_id, AuditWorkingPaper.tenant_id == tenant_id)
            )
            if not wp_result.scalar_one_or_none():
                raise NotFoundException(detail="Working paper not found")

        # Validate evidence if provided
        if data.evidence_id:
            ev_result = await self.db.execute(
                select(AuditEvidence).where(AuditEvidence.id == data.evidence_id, AuditEvidence.tenant_id == tenant_id)
            )
            if not ev_result.scalar_one_or_none():
                raise NotFoundException(detail="Evidence not found")

        # Validate reviewer
        reviewer_result = await self.db.execute(
            select(User).where(User.id == data.reviewer_id, User.tenant_id == tenant_id)
        )
        if not reviewer_result.scalar_one_or_none():
            raise NotFoundException(detail="Reviewer not found")

        review = AuditReview(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=AuditReviewStatus.PENDING,
        )
        return await self.repository.create(review)

    async def get_by_id(self, review_id: UUID, tenant_id: UUID) -> AuditReview:
        review = await self.repository.get_by_id(review_id, tenant_id)
        if not review:
            raise NotFoundException(detail="Audit review not found")
        return review

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engagement_id: UUID | None = None,
        working_paper_id: UUID | None = None,
        evidence_id: UUID | None = None,
        reviewer_id: UUID | None = None,
        status: str | None = None,
        review_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, engagement_id, working_paper_id,
            evidence_id, reviewer_id, status, review_type, date_from, date_to, sort_by, sort_order
        )

    async def update(self, review_id: UUID, tenant_id: UUID, data: AuditReviewUpdate, updated_by: UUID) -> AuditReview:
        review = await self.get_by_id(review_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == AuditReviewStatus.IN_PROGRESS.value:
                review.started_at = datetime.now()
            elif new_status in [AuditReviewStatus.APPROVED.value, AuditReviewStatus.REJECTED.value, AuditReviewStatus.REQUIRES_REWORK.value]:
                review.completed_at = datetime.now()

        for field, value in update_data.items():
            setattr(review, field, value)

        review.updated_by = updated_by
        return await self.repository.update(review)

    async def start_review(self, review_id: UUID, tenant_id: UUID, reviewer_id: UUID) -> AuditReview:
        review = await self.get_by_id(review_id, tenant_id)
        if review.status != AuditReviewStatus.PENDING.value:
            raise ValidationException(detail="Only pending reviews can be started")
        review.status = AuditReviewStatus.IN_PROGRESS.value
        review.started_at = datetime.now()
        review.reviewer_id = reviewer_id
        return await self.repository.update(review)

    async def complete_review(self, review_id: UUID, tenant_id: UUID, status: str, completed_by: UUID, findings: str | None = None, recommendations: str | None = None, review_notes: str | None = None) -> AuditReview:
        review = await self.get_by_id(review_id, tenant_id)
        if review.status != AuditReviewStatus.IN_PROGRESS.value:
            raise ValidationException(detail="Only in-progress reviews can be completed")

        if status not in [AuditReviewStatus.APPROVED.value, AuditReviewStatus.REJECTED.value, AuditReviewStatus.REQUIRES_REWORK.value]:
            raise ValidationException(detail="Invalid completion status")

        review.status = status
        review.completed_at = datetime.now()
        if findings:
            review.findings = findings
        if recommendations:
            review.recommendations = recommendations
        if review_notes:
            review.review_notes = review_notes
        review.updated_by = completed_by

        return await self.repository.update(review)

    async def delete(self, review_id: UUID, tenant_id: UUID) -> None:
        review = await self.get_by_id(review_id, tenant_id)
        await self.repository.delete(review)


class AuditSignOffService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AuditSignOffRepository(db)

    async def create(self, data: AuditSignOffCreate, tenant_id: UUID, created_by: UUID) -> AuditSignOff:
        # Validate engagement
        engagement_result = await self.db.execute(
            select(AuditEngagement).where(AuditEngagement.id == data.engagement_id, AuditEngagement.tenant_id == tenant_id)
        )
        if not engagement_result.scalar_one_or_none():
            raise NotFoundException(detail="Audit engagement not found")

        # Validate signer
        signer_result = await self.db.execute(
            select(User).where(User.id == data.signer_id, User.tenant_id == tenant_id)
        )
        if not signer_result.scalar_one_or_none():
            raise NotFoundException(detail="Signer not found")

        sign_off = AuditSignOff(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=SignOffStatus.PENDING,
        )
        return await self.repository.create(sign_off)

    async def get_by_id(self, sign_off_id: UUID, tenant_id: UUID) -> AuditSignOff:
        sign_off = await self.repository.get_by_id(sign_off_id, tenant_id)
        if not sign_off:
            raise NotFoundException(detail="Sign-off not found")
        return sign_off

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engagement_id: UUID | None = None,
        signer_id: UUID | None = None,
        status: str | None = None,
        sign_off_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list, int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, engagement_id, signer_id, status, sign_off_type, date_from, date_to, sort_by, sort_order
        )

    async def update(self, sign_off_id: UUID, tenant_id: UUID, data: AuditSignOffUpdate, updated_by: UUID) -> AuditSignOff:
        sign_off = await self.get_by_id(sign_off_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == SignOffStatus.SIGNED.value:
                sign_off.signed_at = datetime.now()
            elif new_status == SignOffStatus.REJECTED.value:
                sign_off.signed_at = None

        for field, value in update_data.items():
            setattr(sign_off, field, value)

        sign_off.updated_by = updated_by
        return await self.repository.update(sign_off)

    async def sign(self, sign_off_id: UUID, tenant_id: UUID, signer_id: UUID) -> AuditSignOff:
        sign_off = await self.get_by_id(sign_off_id, tenant_id)
        if sign_off.signer_id != signer_id:
            raise ValidationException(detail="Only the assigned signer can sign this document")
        if sign_off.status != SignOffStatus.PENDING.value:
            raise ValidationException(detail="Sign-off is not in pending status")

        sign_off.status = SignOffStatus.SIGNED.value
        sign_off.signed_at = datetime.now()
        sign_off.updated_by = signer_id

        return await self.repository.update(sign_off)

    async def delete(self, sign_off_id: UUID, tenant_id: UUID) -> None:
        sign_off = await self.get_by_id(sign_off_id, tenant_id)
        await self.repository.delete(sign_off)