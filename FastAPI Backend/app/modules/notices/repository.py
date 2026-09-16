from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.notices.models import (
    Notice,
    NoticeAuthority,
    NoticeEscalation,
    NoticePriority,
    NoticeStatus,
    NoticeType,
)


class NoticeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Notice methods
    async def create_notice(self, notice: Notice) -> Notice:
        self.db.add(notice)
        await self.db.flush()
        await self.db.refresh(notice)
        return notice

    async def get_notice_by_id(self, notice_id: UUID, tenant_id: UUID) -> Notice | None:
        result = await self.db.execute(
            select(Notice)
            .where(
                Notice.id == notice_id,
                Notice.tenant_id == tenant_id,
            )
            .options(
                selectinload(Notice.client),
                selectinload(Notice.matter),
                selectinload(Notice.assignee),
                selectinload(Notice.team),
                selectinload(Notice.escalated_to),
                selectinload(Notice.escalation_history).selectinload(NoticeEscalation.escalated_from),
                selectinload(Notice.escalation_history).selectinload(NoticeEscalation.escalated_to),
                selectinload(Notice.escalation_history).selectinload(NoticeEscalation.escalated_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_notice_by_ref(self, reference_number: str, tenant_id: UUID) -> Notice | None:
        result = await self.db.execute(
            select(Notice).where(
                Notice.reference_number == reference_number,
                Notice.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_notices(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        authority: NoticeAuthority | None = None,
        notice_type: NoticeType | None = None,
        status: NoticeStatus | None = None,
        priority: NoticePriority | None = None,
        assignee_id: UUID | None = None,
        team_id: UUID | None = None,
        received_date_from: datetime | None = None,
        received_date_to: datetime | None = None,
        deadline_from: datetime | None = None,
        deadline_to: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Notice], int]:
        query = select(Notice).where(Notice.tenant_id == tenant_id)
        count_query = select(func.count(Notice.id)).where(Notice.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Notice.reference_number.ilike(search_term),
                    Notice.subject.ilike(search_term),
                    Notice.description.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    Notice.reference_number.ilike(search_term),
                    Notice.subject.ilike(search_term),
                    Notice.description.ilike(search_term),
                )
            )

        if client_id:
            query = query.where(Notice.client_id == client_id)
            count_query = count_query.where(Notice.client_id == client_id)

        if authority:
            query = query.where(Notice.authority == authority)
            count_query = count_query.where(Notice.authority == authority)

        if notice_type:
            query = query.where(Notice.notice_type == notice_type)
            count_query = count_query.where(Notice.notice_type == notice_type)

        if status:
            query = query.where(Notice.status == status)
            count_query = count_query.where(Notice.status == status)

        if priority:
            query = query.where(Notice.priority == priority)
            count_query = count_query.where(Notice.priority == priority)

        if assignee_id:
            query = query.where(Notice.assignee_id == assignee_id)
            count_query = count_query.where(Notice.assignee_id == assignee_id)

        if team_id:
            query = query.where(Notice.team_id == team_id)
            count_query = count_query.where(Notice.team_id == team_id)

        if received_date_from:
            query = query.where(Notice.received_date >= received_date_from)
            count_query = count_query.where(Notice.received_date >= received_date_from)

        if received_date_to:
            query = query.where(Notice.received_date <= received_date_to)
            count_query = count_query.where(Notice.received_date <= received_date_to)

        if deadline_from:
            query = query.where(Notice.response_deadline >= deadline_from)
            count_query = count_query.where(Notice.response_deadline >= deadline_from)

        if deadline_to:
            query = query.where(Notice.response_deadline <= deadline_to)
            count_query = count_query.where(Notice.response_deadline <= deadline_to)

        if sort_by and hasattr(Notice, sort_by):
            column = getattr(Notice, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(Notice.response_deadline.asc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(Notice.client),
                selectinload(Notice.matter),
                selectinload(Notice.assignee),
                selectinload(Notice.team),
            )
        )
        notices = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(notices), total

    async def update_notice(self, notice: Notice) -> Notice:
        await self.db.flush()
        await self.db.refresh(notice)
        return notice

    async def delete_notice(self, notice: Notice) -> None:
        await self.db.delete(notice)
        await self.db.flush()

    # Escalation methods
    async def create_escalation(self, escalation: NoticeEscalation) -> NoticeEscalation:
        self.db.add(escalation)
        await self.db.flush()
        await self.db.refresh(escalation)
        return escalation

    async def get_escalation_by_id(self, escalation_id: UUID, tenant_id: UUID) -> NoticeEscalation | None:
        result = await self.db.execute(
            select(NoticeEscalation)
            .where(
                NoticeEscalation.id == escalation_id,
                NoticeEscalation.tenant_id == tenant_id,
            )
            .options(
                selectinload(NoticeEscalation.escalated_from),
                selectinload(NoticeEscalation.escalated_to),
                selectinload(NoticeEscalation.escalated_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_escalations_for_notice(self, notice_id: UUID, tenant_id: UUID) -> list[NoticeEscalation]:
        result = await self.db.execute(
            select(NoticeEscalation)
            .where(
                NoticeEscalation.notice_id == notice_id,
                NoticeEscalation.tenant_id == tenant_id,
            )
            .options(
                selectinload(NoticeEscalation.escalated_from),
                selectinload(NoticeEscalation.escalated_to),
                selectinload(NoticeEscalation.escalated_by),
            )
            .order_by(NoticeEscalation.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_escalation(self, escalation: NoticeEscalation) -> NoticeEscalation:
        await self.db.flush()
        await self.db.refresh(escalation)
        return escalation

    async def get_summary(self, tenant_id: UUID) -> dict:
        from datetime import timedelta
        now = datetime.now(UTC)

        query = select(Notice).where(Notice.tenant_id == tenant_id)
        result = await self.db.execute(query)
        notices = result.scalars().all()

        total = len(notices)
        received = sum(1 for n in notices if n.status == NoticeStatus.RECEIVED)
        under_review = sum(1 for n in notices if n.status == NoticeStatus.UNDER_REVIEW)
        response_drafting = sum(1 for n in notices if n.status == NoticeStatus.RESPONSE_DRAFTING)
        responded = sum(1 for n in notices if n.status == NoticeStatus.RESPONDED)
        hearing_scheduled = sum(1 for n in notices if n.status == NoticeStatus.HEARING_SCHEDULED)
        closed = sum(1 for n in notices if n.status == NoticeStatus.CLOSED)
        escalated = sum(1 for n in notices if n.status == NoticeStatus.ESCALATED)

        overdue = sum(
            1 for n in notices
            if n.status not in [NoticeStatus.CLOSED, NoticeStatus.RESPONDED, NoticeStatus.APPEAL_FILED]
            and n.response_deadline < now
        )

        total_demand = sum(n.demand_amount or 0 for n in notices)

        # Upcoming deadlines (next 7 days)
        upcoming_date = now + timedelta(days=7)
        upcoming = [
            n for n in notices
            if n.status not in [NoticeStatus.CLOSED, NoticeStatus.RESPONDED, NoticeStatus.APPEAL_FILED]
            and n.response_deadline <= upcoming_date
        ]
        upcoming.sort(key=lambda x: x.response_deadline)

        return {
            "total_notices": total,
            "received": received,
            "under_review": under_review,
            "response_drafting": response_drafting,
            "responded": responded,
            "hearing_scheduled": hearing_scheduled,
            "closed": closed,
            "overdue": overdue,
            "escalated": escalated,
            "total_demand_amount": total_demand,
            "upcoming_deadlines": upcoming[:10],
        }
