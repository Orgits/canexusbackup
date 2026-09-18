from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
)


class AuditEngagementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, engagement: AuditEngagement) -> AuditEngagement:
        self.db.add(engagement)
        await self.db.flush()
        await self.db.refresh(engagement)
        return engagement

    async def get_by_id(self, engagement_id: UUID, tenant_id: UUID) -> AuditEngagement | None:
        result = await self.db.execute(
            select(AuditEngagement)
            .options(
                selectinload(AuditEngagement.client),
                selectinload(AuditEngagement.engagement_partner),
                selectinload(AuditEngagement.engagement_manager),
            )
            .where(AuditEngagement.id == engagement_id, AuditEngagement.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, engagement_number: str, tenant_id: UUID) -> AuditEngagement | None:
        result = await self.db.execute(
            select(AuditEngagement).where(
                AuditEngagement.engagement_number == engagement_number,
                AuditEngagement.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        status: AuditEngagementStatus | None = None,
        engagement_type: str | None = None,
        engagement_partner_id: UUID | None = None,
        engagement_manager_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[AuditEngagement], int]:
        query = (
            select(AuditEngagement)
            .options(
                selectinload(AuditEngagement.client),
                selectinload(AuditEngagement.engagement_partner),
                selectinload(AuditEngagement.engagement_manager),
            )
            .where(AuditEngagement.tenant_id == tenant_id)
        )
        count_query = select(func.count(AuditEngagement.id)).where(AuditEngagement.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                AuditEngagement.engagement_number.ilike(f"%{search}%"),
                AuditEngagement.scope.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if client_id:
            query = query.where(AuditEngagement.client_id == client_id)
            count_query = count_query.where(AuditEngagement.client_id == client_id)

        if status:
            query = query.where(AuditEngagement.status == status)
            count_query = count_query.where(AuditEngagement.status == status)

        if engagement_type:
            query = query.where(AuditEngagement.engagement_type == engagement_type)
            count_query = count_query.where(AuditEngagement.engagement_type == engagement_type)

        if engagement_partner_id:
            query = query.where(AuditEngagement.engagement_partner_id == engagement_partner_id)
            count_query = count_query.where(AuditEngagement.engagement_partner_id == engagement_partner_id)

        if engagement_manager_id:
            query = query.where(AuditEngagement.engagement_manager_id == engagement_manager_id)
            count_query = count_query.where(AuditEngagement.engagement_manager_id == engagement_manager_id)

        if date_from:
            query = query.where(AuditEngagement.period_start >= date_from)
            count_query = count_query.where(AuditEngagement.period_start >= date_from)

        if date_to:
            query = query.where(AuditEngagement.period_end <= date_to)
            count_query = count_query.where(AuditEngagement.period_end <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(AuditEngagement, sort_by):
            sort_column = getattr(AuditEngagement, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(AuditEngagement.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, engagement: AuditEngagement) -> AuditEngagement:
        await self.db.flush()
        await self.db.refresh(engagement)
        return engagement

    async def delete(self, engagement: AuditEngagement) -> None:
        await self.db.delete(engagement)
        await self.db.flush()


class AuditWorkingPaperRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, wp: AuditWorkingPaper) -> AuditWorkingPaper:
        self.db.add(wp)
        await self.db.flush()
        await self.db.refresh(wp)
        return wp

    async def get_by_id(self, wp_id: UUID, tenant_id: UUID) -> AuditWorkingPaper | None:
        result = await self.db.execute(
            select(AuditWorkingPaper)
            .options(
                selectinload(AuditWorkingPaper.engagement),
                selectinload(AuditWorkingPaper.prepared_by),
                selectinload(AuditWorkingPaper.reviewed_by),
            )
            .where(AuditWorkingPaper.id == wp_id, AuditWorkingPaper.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engagement_id: UUID | None = None,
        status: WorkingPaperStatus | None = None,
        working_paper_type: str | None = None,
        prepared_by_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[AuditWorkingPaper], int]:
        query = (
            select(AuditWorkingPaper)
            .options(
                selectinload(AuditWorkingPaper.engagement),
                selectinload(AuditWorkingPaper.prepared_by),
                selectinload(AuditWorkingPaper.reviewed_by),
            )
            .where(AuditWorkingPaper.tenant_id == tenant_id)
        )
        count_query = select(func.count(AuditWorkingPaper.id)).where(AuditWorkingPaper.tenant_id == tenant_id)

        if engagement_id:
            query = query.where(AuditWorkingPaper.engagement_id == engagement_id)
            count_query = count_query.where(AuditWorkingPaper.engagement_id == engagement_id)

        if status:
            query = query.where(AuditWorkingPaper.status == status)
            count_query = count_query.where(AuditWorkingPaper.status == status)

        if working_paper_type:
            query = query.where(AuditWorkingPaper.working_paper_type == working_paper_type)
            count_query = count_query.where(AuditWorkingPaper.working_paper_type == working_paper_type)

        if prepared_by_id:
            query = query.where(AuditWorkingPaper.prepared_by_id == prepared_by_id)
            count_query = count_query.where(AuditWorkingPaper.prepared_by_id == prepared_by_id)

        if date_from:
            query = query.where(AuditWorkingPaper.created_at >= date_from)
            count_query = count_query.where(AuditWorkingPaper.created_at >= date_from)

        if date_to:
            query = query.where(AuditWorkingPaper.created_at <= date_to)
            count_query = count_query.where(AuditWorkingPaper.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(AuditWorkingPaper, sort_by):
            sort_column = getattr(AuditWorkingPaper, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(AuditWorkingPaper.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, wp: AuditWorkingPaper) -> AuditWorkingPaper:
        await self.db.flush()
        await self.db.refresh(wp)
        return wp

    async def delete(self, wp: AuditWorkingPaper) -> None:
        await self.db.delete(wp)
        await self.db.flush()


class AuditEvidenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, evidence: AuditEvidence) -> AuditEvidence:
        self.db.add(evidence)
        await self.db.flush()
        await self.db.refresh(evidence)
        return evidence

    async def get_by_id(self, evidence_id: UUID, tenant_id: UUID) -> AuditEvidence | None:
        result = await self.db.execute(
            select(AuditEvidence)
            .options(
                selectinload(AuditEvidence.engagement),
                selectinload(AuditEvidence.working_paper),
                selectinload(AuditEvidence.document),
                selectinload(AuditEvidence.collected_by),
                selectinload(AuditEvidence.reviewed_by),
            )
            .where(AuditEvidence.id == evidence_id, AuditEvidence.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

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
    ) -> tuple[list[AuditEvidence], int]:
        query = (
            select(AuditEvidence)
            .options(
                selectinload(AuditEvidence.engagement),
                selectinload(AuditEvidence.working_paper),
                selectinload(AuditEvidence.document),
                selectinload(AuditEvidence.collected_by),
                selectinload(AuditEvidence.reviewed_by),
            )
            .where(AuditEvidence.tenant_id == tenant_id)
        )
        count_query = select(func.count(AuditEvidence.id)).where(AuditEvidence.tenant_id == tenant_id)

        if engagement_id:
            query = query.where(AuditEvidence.engagement_id == engagement_id)
            count_query = count_query.where(AuditEvidence.engagement_id == engagement_id)

        if working_paper_id:
            query = query.where(AuditEvidence.working_paper_id == working_paper_id)
            count_query = count_query.where(AuditEvidence.working_paper_id == working_paper_id)

        if status:
            query = query.where(AuditEvidence.status == status)
            count_query = count_query.where(AuditEvidence.status == status)

        if evidence_type:
            query = query.where(AuditEvidence.evidence_type == evidence_type)
            count_query = count_query.where(AuditEvidence.evidence_type == evidence_type)

        if date_from:
            query = query.where(AuditEvidence.created_at >= date_from)
            count_query = count_query.where(AuditEvidence.created_at >= date_from)

        if date_to:
            query = query.where(AuditEvidence.created_at <= date_to)
            count_query = count_query.where(AuditEvidence.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(AuditEvidence, sort_by):
            sort_column = getattr(AuditEvidence, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(AuditEvidence.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, evidence: AuditEvidence) -> AuditEvidence:
        await self.db.flush()
        await self.db.refresh(evidence)
        return evidence

    async def delete(self, evidence: AuditEvidence) -> None:
        await self.db.delete(evidence)
        await self.db.flush()


class AuditReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, review: AuditReview) -> AuditReview:
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def get_by_id(self, review_id: UUID, tenant_id: UUID) -> AuditReview | None:
        result = await self.db.execute(
            select(AuditReview)
            .options(
                selectinload(AuditReview.engagement),
                selectinload(AuditReview.working_paper),
                selectinload(AuditReview.evidence),
                selectinload(AuditReview.reviewer),
            )
            .where(AuditReview.id == review_id, AuditReview.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

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
    ) -> tuple[list[AuditReview], int]:
        query = (
            select(AuditReview)
            .options(
                selectinload(AuditReview.engagement),
                selectinload(AuditReview.working_paper),
                selectinload(AuditReview.evidence),
                selectinload(AuditReview.reviewer),
            )
            .where(AuditReview.tenant_id == tenant_id)
        )
        count_query = select(func.count(AuditReview.id)).where(AuditReview.tenant_id == tenant_id)

        if engagement_id:
            query = query.where(AuditReview.engagement_id == engagement_id)
            count_query = count_query.where(AuditReview.engagement_id == engagement_id)

        if working_paper_id:
            query = query.where(AuditReview.working_paper_id == working_paper_id)
            count_query = count_query.where(AuditReview.working_paper_id == working_paper_id)

        if evidence_id:
            query = query.where(AuditReview.evidence_id == evidence_id)
            count_query = count_query.where(AuditReview.evidence_id == evidence_id)

        if reviewer_id:
            query = query.where(AuditReview.reviewer_id == reviewer_id)
            count_query = count_query.where(AuditReview.reviewer_id == reviewer_id)

        if status:
            query = query.where(AuditReview.status == status)
            count_query = count_query.where(AuditReview.status == status)

        if review_type:
            query = query.where(AuditReview.review_type == review_type)
            count_query = count_query.where(AuditReview.review_type == review_type)

        if date_from:
            query = query.where(AuditReview.created_at >= date_from)
            count_query = count_query.where(AuditReview.created_at >= date_from)

        if date_to:
            query = query.where(AuditReview.created_at <= date_to)
            count_query = count_query.where(AuditReview.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(AuditReview, sort_by):
            sort_column = getattr(AuditReview, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(AuditReview.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, review: AuditReview) -> AuditReview:
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def delete(self, review: AuditReview) -> None:
        await self.db.delete(review)
        await self.db.flush()


class AuditSignOffRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, sign_off: AuditSignOff) -> AuditSignOff:
        self.db.add(sign_off)
        await self.db.flush()
        await self.db.refresh(sign_off)
        return sign_off

    async def get_by_id(self, sign_off_id: UUID, tenant_id: UUID) -> AuditSignOff | None:
        result = await self.db.execute(
            select(AuditSignOff)
            .options(
                selectinload(AuditSignOff.engagement),
                selectinload(AuditSignOff.signer),
            )
            .where(AuditSignOff.id == sign_off_id, AuditSignOff.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        engagement_id: UUID | None = None,
        signer_id: UUID | None = None,
        status: SignOffStatus | None = None,
        sign_off_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[AuditSignOff], int]:
        query = (
            select(AuditSignOff)
            .options(
                selectinload(AuditSignOff.engagement),
                selectinload(AuditSignOff.signer),
            )
            .where(AuditSignOff.tenant_id == tenant_id)
        )
        count_query = select(func.count(AuditSignOff.id)).where(AuditSignOff.tenant_id == tenant_id)

        if engagement_id:
            query = query.where(AuditSignOff.engagement_id == engagement_id)
            count_query = count_query.where(AuditSignOff.engagement_id == engagement_id)

        if signer_id:
            query = query.where(AuditSignOff.signer_id == signer_id)
            count_query = count_query.where(AuditSignOff.signer_id == signer_id)

        if status:
            query = query.where(AuditSignOff.status == status)
            count_query = count_query.where(AuditSignOff.status == status)

        if sign_off_type:
            query = query.where(AuditSignOff.sign_off_type == sign_off_type)
            count_query = count_query.where(AuditSignOff.sign_off_type == sign_off_type)

        if date_from:
            query = query.where(AuditSignOff.created_at >= date_from)
            count_query = count_query.where(AuditSignOff.created_at >= date_from)

        if date_to:
            query = query.where(AuditSignOff.created_at <= date_to)
            count_query = count_query.where(AuditSignOff.created_at <= date_to)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if sort_by and hasattr(AuditSignOff, sort_by):
            sort_column = getattr(AuditSignOff, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(AuditSignOff.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, sign_off: AuditSignOff) -> AuditSignOff:
        await self.db.flush()
        await self.db.refresh(sign_off)
        return sign_off

    async def delete(self, sign_off: AuditSignOff) -> None:
        await self.db.delete(sign_off)
        await self.db.flush()