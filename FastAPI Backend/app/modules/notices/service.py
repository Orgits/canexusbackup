from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException, ValidationException
from app.modules.notices.models import (
    Notice,
    NoticeEscalation,
    NoticeAuthority,
    NoticeType,
    NoticeStatus,
    NoticePriority,
)
from app.modules.notices.schemas import (
    NoticeCreate,
    NoticeUpdate,
    NoticeStatusUpdate,
    NoticeResponseUpdate,
    NoticeClosureUpdate,
    NoticeEscalationCreate,
)
from app.modules.notices.repository import NoticeRepository
from app.modules.clients.models import Client


class NoticeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = NoticeRepository(db)

    async def create_notice(
        self, data: NoticeCreate, tenant_id: UUID, created_by: UUID
    ) -> Notice:
        # Verify client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        # Check for duplicate reference number
        existing = await self.repository.get_notice_by_ref(data.reference_number, tenant_id)
        if existing:
            raise ConflictException(detail="Notice with this reference number already exists")

        notice = Notice(
            **data.model_dump(
                exclude={"authority", "notice_type", "priority", "status"}
            ),
            authority=NoticeAuthority(data.authority),
            notice_type=NoticeType(data.notice_type),
            priority=NoticePriority(data.priority),
            status=NoticeStatus.RECEIVED,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create_notice(notice)

    async def get_notice_by_id(self, notice_id: UUID, tenant_id: UUID) -> Notice:
        notice = await self.repository.get_notice_by_id(notice_id, tenant_id)
        if not notice:
            raise NotFoundException(detail="Notice not found")
        return notice

    async def get_all_notices(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        authority: Optional[str] = None,
        notice_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        received_date_from: Optional[datetime] = None,
        received_date_to: Optional[datetime] = None,
        deadline_from: Optional[datetime] = None,
        deadline_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Notice], int]:
        authority_enum = None
        if authority:
            try:
                authority_enum = NoticeAuthority(authority)
            except ValueError:
                raise ValidationException(detail=f"Invalid authority: {authority}")

        notice_type_enum = None
        if notice_type:
            try:
                notice_type_enum = NoticeType(notice_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid notice_type: {notice_type}")

        status_enum = None
        if status:
            try:
                status_enum = NoticeStatus(status)
            except ValueError:
                raise ValidationException(detail=f"Invalid status: {status}")

        priority_enum = None
        if priority:
            try:
                priority_enum = NoticePriority(priority)
            except ValueError:
                raise ValidationException(detail=f"Invalid priority: {priority}")

        return await self.repository.get_all_notices(
            tenant_id,
            page,
            page_size,
            search,
            client_id,
            authority_enum,
            notice_type_enum,
            status_enum,
            priority_enum,
            assignee_id,
            team_id,
            received_date_from,
            received_date_to,
            deadline_from,
            deadline_to,
            sort_by,
            sort_order,
        )

    async def update_notice(
        self, notice_id: UUID, tenant_id: UUID, data: NoticeUpdate, updated_by: UUID
    ) -> Notice:
        notice = await self.get_notice_by_id(notice_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        # Handle enum fields
        if "authority" in update_data:
            try:
                notice.authority = NoticeAuthority(update_data.pop("authority"))
            except ValueError:
                raise ValidationException(detail="Invalid authority")

        if "notice_type" in update_data:
            try:
                notice.notice_type = NoticeType(update_data.pop("notice_type"))
            except ValueError:
                raise ValidationException(detail="Invalid notice_type")

        if "status" in update_data:
            try:
                notice.status = NoticeStatus(update_data.pop("status"))
            except ValueError:
                raise ValidationException(detail="Invalid status")

        if "priority" in update_data:
            try:
                notice.priority = NoticePriority(update_data.pop("priority"))
            except ValueError:
                raise ValidationException(detail="Invalid priority")

        for field, value in update_data.items():
            setattr(notice, field, value)
        notice.updated_by = updated_by
        return await self.repository.update_notice(notice)

    async def update_status(
        self, notice_id: UUID, tenant_id: UUID, data: NoticeStatusUpdate, actor_id: UUID
    ) -> Notice:
        notice = await self.get_notice_by_id(notice_id, tenant_id)

        try:
            new_status = NoticeStatus(data.status)
        except ValueError:
            raise ValidationException(detail=f"Invalid status: {data.status}")

        # Validate status transitions
        valid_transitions = {
            NoticeStatus.RECEIVED: [NoticeStatus.ACKNOWLEDGED, NoticeStatus.UNDER_REVIEW, NoticeStatus.ESCALATED],
            NoticeStatus.ACKNOWLEDGED: [NoticeStatus.UNDER_REVIEW, NoticeStatus.RESPONSE_DRAFTING, NoticeStatus.ESCALATED],
            NoticeStatus.UNDER_REVIEW: [NoticeStatus.RESPONSE_DRAFTING, NoticeStatus.ESCALATED],
            NoticeStatus.RESPONSE_DRAFTING: [NoticeStatus.RESPONSE_REVIEW, NoticeStatus.ESCALATED],
            NoticeStatus.RESPONSE_REVIEW: [NoticeStatus.RESPONSE_APPROVED, NoticeStatus.RESPONSE_DRAFTING, NoticeStatus.ESCALATED],
            NoticeStatus.RESPONSE_APPROVED: [NoticeStatus.RESPONDED, NoticeStatus.ESCALATED],
            NoticeStatus.RESPONDED: [NoticeStatus.HEARING_SCHEDULED, NoticeStatus.ORDER_RECEIVED, NoticeStatus.CLOSED, NoticeStatus.ESCALATED],
            NoticeStatus.HEARING_SCHEDULED: [NoticeStatus.HEARING_COMPLETED, NoticeStatus.ESCALATED],
            NoticeStatus.HEARING_COMPLETED: [NoticeStatus.ORDER_RECEIVED, NoticeStatus.ESCALATED],
            NoticeStatus.ORDER_RECEIVED: [NoticeStatus.APPEAL_FILED, NoticeStatus.CLOSED, NoticeStatus.ESCALATED],
            NoticeStatus.APPEAL_FILED: [NoticeStatus.CLOSED, NoticeStatus.ESCALATED],
            NoticeStatus.ESCALATED: [NoticeStatus.UNDER_REVIEW, NoticeStatus.RESPONSE_DRAFTING, NoticeStatus.CLOSED],
            NoticeStatus.CLOSED: [],
        }

        if new_status not in valid_transitions.get(notice.status, []):
            raise ValidationException(detail=f"Invalid status transition from {notice.status} to {new_status}")

        notice.status = new_status
        notice.updated_by = actor_id

        if new_status == NoticeStatus.CLOSED:
            notice.closed_at = datetime.now(timezone.utc)
            notice.closed_by = actor_id

        return await self.repository.update_notice(notice)

    async def update_response(
        self, notice_id: UUID, tenant_id: UUID, data: NoticeResponseUpdate, actor_id: UUID
    ) -> Notice:
        notice = await self.get_notice_by_id(notice_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(notice, field, value)
        notice.updated_by = actor_id

        # Auto-update status if response filed
        if data.response_filed_date and notice.status == NoticeStatus.RESPONSE_APPROVED:
            notice.status = NoticeStatus.RESPONDED

        return await self.repository.update_notice(notice)

    async def close_notice(
        self, notice_id: UUID, tenant_id: UUID, data: NoticeClosureUpdate, actor_id: UUID
    ) -> Notice:
        notice = await self.get_notice_by_id(notice_id, tenant_id)

        if notice.status == NoticeStatus.CLOSED:
            raise ValidationException(detail="Notice is already closed")

        notice.status = NoticeStatus.CLOSED
        notice.closed_at = datetime.now(timezone.utc)
        notice.closed_by = actor_id
        notice.closure_reason = data.closure_reason
        notice.outcome = data.outcome
        notice.order_date = data.order_date
        notice.order_summary = data.order_summary
        notice.appeal_filed = data.appeal_filed
        notice.appeal_details = data.appeal_details
        notice.updated_by = actor_id

        return await self.repository.update_notice(notice)

    async def delete_notice(self, notice_id: UUID, tenant_id: UUID) -> None:
        notice = await self.get_notice_by_id(notice_id, tenant_id)
        await self.repository.delete_notice(notice)

    # Escalation methods
    async def escalate_notice(
        self, notice_id: UUID, tenant_id: UUID, data: NoticeEscalationCreate, actor_id: UUID
    ) -> NoticeEscalation:
        notice = await self.get_notice_by_id(notice_id, tenant_id)

        if notice.status == NoticeStatus.CLOSED:
            raise ValidationException(detail="Cannot escalate a closed notice")

        escalation = NoticeEscalation(
            notice_id=notice.id,
            escalated_from_id=notice.assignee_id,
            escalated_to_id=data.escalated_to_id,
            escalated_by_id=actor_id,
            reason=data.reason,
            previous_deadline=data.previous_deadline or notice.response_deadline,
            new_deadline=data.new_deadline,
            tenant_id=tenant_id,
            created_by=actor_id,
        )

        # Update notice
        notice.status = NoticeStatus.ESCALATED
        notice.escalated_to_id = data.escalated_to_id
        notice.assignee_id = data.escalated_to_id
        if data.new_deadline:
            notice.response_deadline = data.new_deadline
        notice.updated_by = actor_id

        await self.repository.update_notice(notice)
        return await self.repository.create_escalation(escalation)

    async def get_escalation_history(self, notice_id: UUID, tenant_id: UUID) -> List[NoticeEscalation]:
        await self.get_notice_by_id(notice_id, tenant_id)
        return await self.repository.get_escalations_for_notice(notice_id, tenant_id)

    async def resolve_escalation(
        self, escalation_id: UUID, tenant_id: UUID, actor_id: UUID
    ) -> NoticeEscalation:
        escalation = await self.repository.get_escalation_by_id(escalation_id, tenant_id)
        if not escalation:
            raise NotFoundException(detail="Escalation not found")

        escalation.is_resolved = True
        escalation.resolved_at = datetime.now(timezone.utc)
        escalation.resolved_by = actor_id
        escalation.updated_by = actor_id

        return await self.repository.update_escalation(escalation)

    async def get_summary(self, tenant_id: UUID) -> dict:
        return await self.repository.get_summary(tenant_id)