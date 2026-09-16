from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.assignments.models import (
    AssignableEntityType,
    Assignment,
    AssignmentHistory,
    Escalation,
)


class AssignmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Assignment methods
    async def create_assignment(self, assignment: Assignment) -> Assignment:
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def get_assignment_by_id(self, assignment_id: UUID, tenant_id: UUID) -> Assignment | None:
        result = await self.db.execute(
            select(Assignment)
            .where(
                Assignment.id == assignment_id,
                Assignment.tenant_id == tenant_id,
            )
            .options(
                selectinload(Assignment.user),
                selectinload(Assignment.team),
                selectinload(Assignment.assigned_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_assignment(
        self, entity_type: AssignableEntityType, entity_id: UUID, tenant_id: UUID
    ) -> Assignment | None:
        result = await self.db.execute(
            select(Assignment).where(
                Assignment.entity_type == entity_type,
                Assignment.entity_id == entity_id,
                Assignment.tenant_id == tenant_id,
                Assignment.is_active == True,
            )
            .options(
                selectinload(Assignment.user),
                selectinload(Assignment.team),
                selectinload(Assignment.assigned_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_assignments(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        entity_type: AssignableEntityType | None = None,
        entity_id: UUID | None = None,
        user_id: UUID | None = None,
        team_id: UUID | None = None,
        is_active: bool | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Assignment], int]:
        query = select(Assignment).where(Assignment.tenant_id == tenant_id)
        count_query = select(func.count(Assignment.id)).where(Assignment.tenant_id == tenant_id)

        if entity_type:
            query = query.where(Assignment.entity_type == entity_type)
            count_query = count_query.where(Assignment.entity_type == entity_type)

        if entity_id:
            query = query.where(Assignment.entity_id == entity_id)
            count_query = count_query.where(Assignment.entity_id == entity_id)

        if user_id:
            query = query.where(Assignment.user_id == user_id)
            count_query = count_query.where(Assignment.user_id == user_id)

        if team_id:
            query = query.where(Assignment.team_id == team_id)
            count_query = count_query.where(Assignment.team_id == team_id)

        if is_active is not None:
            query = query.where(Assignment.is_active == is_active)
            count_query = count_query.where(Assignment.is_active == is_active)

        if sort_by and hasattr(Assignment, sort_by):
            column = getattr(Assignment, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(Assignment.assigned_at.desc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(Assignment.user),
                selectinload(Assignment.team),
                selectinload(Assignment.assigned_by),
            )
        )
        assignments = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(assignments), total

    async def update_assignment(self, assignment: Assignment) -> Assignment:
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def delete_assignment(self, assignment: Assignment) -> None:
        await self.db.delete(assignment)
        await self.db.flush()

    # Assignment History methods
    async def create_history(self, history: AssignmentHistory) -> AssignmentHistory:
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def get_history_for_assignment(
        self, assignment_id: UUID, tenant_id: UUID, page: int = 1, page_size: int = 50
    ) -> tuple[list[AssignmentHistory], int]:
        query = (
            select(AssignmentHistory)
            .where(
                AssignmentHistory.assignment_id == assignment_id,
                AssignmentHistory.tenant_id == tenant_id,
            )
            .order_by(AssignmentHistory.created_at.desc())
        )
        count_query = select(func.count(AssignmentHistory.id)).where(
            AssignmentHistory.assignment_id == assignment_id,
            AssignmentHistory.tenant_id == tenant_id,
        )

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query.options(selectinload(AssignmentHistory.actor)))
        history = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(history), total

    async def get_history_for_entity(
        self, entity_type: AssignableEntityType, entity_id: UUID, tenant_id: UUID
    ) -> list[AssignmentHistory]:
        result = await self.db.execute(
            select(AssignmentHistory)
            .join(Assignment, AssignmentHistory.assignment_id == Assignment.id)
            .where(
                Assignment.entity_type == entity_type,
                Assignment.entity_id == entity_id,
                Assignment.tenant_id == tenant_id,
            )
            .order_by(AssignmentHistory.created_at.desc())
            .options(selectinload(AssignmentHistory.actor))
        )
        return list(result.scalars().all())

    # Escalation methods
    async def create_escalation(self, escalation: Escalation) -> Escalation:
        self.db.add(escalation)
        await self.db.flush()
        await self.db.refresh(escalation)
        return escalation

    async def get_escalation_by_id(self, escalation_id: UUID, tenant_id: UUID) -> Escalation | None:
        result = await self.db.execute(
            select(Escalation)
            .where(
                Escalation.id == escalation_id,
                Escalation.tenant_id == tenant_id,
            )
            .options(
                selectinload(Escalation.escalated_from),
                selectinload(Escalation.escalated_to),
                selectinload(Escalation.escalated_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_escalations_for_entity(
        self, entity_type: AssignableEntityType, entity_id: UUID, tenant_id: UUID
    ) -> list[Escalation]:
        result = await self.db.execute(
            select(Escalation)
            .where(
                Escalation.entity_type == entity_type,
                Escalation.entity_id == entity_id,
                Escalation.tenant_id == tenant_id,
            )
            .options(
                selectinload(Escalation.escalated_from),
                selectinload(Escalation.escalated_to),
                selectinload(Escalation.escalated_by),
            )
            .order_by(Escalation.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all_escalations(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        entity_type: AssignableEntityType | None = None,
        escalated_to_id: UUID | None = None,
        escalated_by_id: UUID | None = None,
        is_resolved: bool | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Escalation], int]:
        query = select(Escalation).where(Escalation.tenant_id == tenant_id)
        count_query = select(func.count(Escalation.id)).where(Escalation.tenant_id == tenant_id)

        if entity_type:
            query = query.where(Escalation.entity_type == entity_type)
            count_query = count_query.where(Escalation.entity_type == entity_type)

        if escalated_to_id:
            query = query.where(Escalation.escalated_to_id == escalated_to_id)
            count_query = count_query.where(Escalation.escalated_to_id == escalated_to_id)

        if escalated_by_id:
            query = query.where(Escalation.escalated_by_id == escalated_by_id)
            count_query = count_query.where(Escalation.escalated_by_id == escalated_by_id)

        if is_resolved is not None:
            query = query.where(Escalation.is_resolved == is_resolved)
            count_query = count_query.where(Escalation.is_resolved == is_resolved)

        if sort_by and hasattr(Escalation, sort_by):
            column = getattr(Escalation, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(Escalation.created_at.desc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(Escalation.escalated_from),
                selectinload(Escalation.escalated_to),
                selectinload(Escalation.escalated_by),
            )
        )
        escalations = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(escalations), total

    async def update_escalation(self, escalation: Escalation) -> Escalation:
        await self.db.flush()
        await self.db.refresh(escalation)
        return escalation
