from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException, ValidationException
from app.modules.assignments.models import (
    Assignment,
    AssignmentHistory,
    Escalation,
    AssignableEntityType,
    AssignmentAction,
    EscalationReason,
)
from app.modules.assignments.schemas import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentReassignRequest,
    AssignmentUnassignRequest,
    EscalationCreate,
    EscalationUpdate,
    EscalationResolveRequest,
    BulkAssignmentRequest,
    BulkReassignmentRequest,
)
from app.modules.assignments.repository import AssignmentRepository
from app.modules.users.models import User


class AssignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AssignmentRepository(db)

    # Assignment methods
    async def create_assignment(
        self, data: AssignmentCreate, tenant_id: UUID, created_by: UUID
    ) -> Assignment:
        entity_type = AssignableEntityType(data.entity_type)

        # Check if active assignment already exists
        existing = await self.repository.get_active_assignment(entity_type, data.entity_id, tenant_id)
        if existing:
            raise ConflictException(detail="Entity already has an active assignment")

        # Validate user exists if provided
        if data.user_id:
            user_result = await self.db.execute(
                select(User).where(User.id == data.user_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="User not found")

        # Validate team exists if provided
        if data.team_id:
            team_result = await self.db.execute(
                select(Team).where(Team.id == data.team_id, Team.tenant_id == tenant_id)
            )
            if not team_result.scalar_one_or_none():
                raise NotFoundException(detail="Team not found")

        assignment = Assignment(
            entity_type=entity_type,
            entity_id=data.entity_id,
            user_id=data.user_id,
            team_id=data.team_id,
            assigned_by_id=created_by,
            assigned_at=datetime.now(timezone.utc),
            notes=data.notes,
            metadata=data.metadata,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        created = await self.repository.create_assignment(assignment)

        # Create history entry
        history = AssignmentHistory(
            assignment_id=created.id,
            action=AssignmentAction.ASSIGN,
            to_user_id=data.user_id,
            to_team_id=data.team_id,
            actor_id=created_by,
            reason=data.notes,
            metadata=data.metadata,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return created

    async def get_assignment(self, assignment_id: UUID, tenant_id: UUID) -> Assignment:
        assignment = await self.repository.get_assignment_by_id(assignment_id, tenant_id)
        if not assignment:
            raise NotFoundException(detail="Assignment not found")
        return assignment

    async def get_active_assignment(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> Assignment:
        try:
            entity_type_enum = AssignableEntityType(entity_type)
        except ValueError:
            raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        assignment = await self.repository.get_active_assignment(entity_type_enum, entity_id, tenant_id)
        if not assignment:
            raise NotFoundException(detail="No active assignment found for this entity")
        return assignment

    async def get_all_assignments(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Assignment], int]:
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = AssignableEntityType(entity_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        return await self.repository.get_all_assignments(
            tenant_id, page, page_size, entity_type_enum, entity_id, user_id, team_id, is_active, sort_by, sort_order
        )

    async def update_assignment(
        self, assignment_id: UUID, tenant_id: UUID, data: AssignmentUpdate, updated_by: UUID
    ) -> Assignment:
        assignment = await self.get_assignment(assignment_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        # Track changes for history
        old_user_id = assignment.user_id
        old_team_id = assignment.team_id
        old_is_active = assignment.is_active

        for field, value in update_data.items():
            setattr(assignment, field, value)
        assignment.updated_by = updated_by

        updated = await self.repository.update_assignment(assignment)

        # Create history entry if assignment changed
        if old_user_id != assignment.user_id or old_team_id != assignment.team_id:
            action = AssignmentAction.REASSIGN
            if old_user_id and not assignment.user_id:
                action = AssignmentAction.UNASSIGN
            elif not old_user_id and assignment.user_id:
                action = AssignmentAction.ASSIGN
            elif old_team_id and not assignment.team_id:
                action = AssignmentAction.REASSIGN
            elif not old_team_id and assignment.team_id:
                action = AssignmentAction.TEAM_ASSIGN

            history = AssignmentHistory(
                assignment_id=assignment.id,
                action=action,
                from_user_id=old_user_id,
                to_user_id=assignment.user_id,
                from_team_id=old_team_id,
                to_team_id=assignment.team_id,
                actor_id=updated_by,
                reason=data.notes,
                tenant_id=tenant_id,
            )
            await self.repository.create_history(history)

        if old_is_active != assignment.is_active:
            history = AssignmentHistory(
                assignment_id=assignment.id,
                action=AssignmentAction.UNASSIGN if not assignment.is_active else AssignmentAction.ASSIGN,
                from_user_id=assignment.user_id if not assignment.is_active else None,
                to_user_id=assignment.user_id if assignment.is_active else None,
                actor_id=updated_by,
                reason=data.notes,
                tenant_id=tenant_id,
            )
            await self.repository.create_history(history)

        return updated

    async def reassign(
        self, data: AssignmentReassignRequest, tenant_id: UUID, actor_id: UUID
    ) -> Assignment:
        try:
            entity_type_enum = AssignableEntityType(data.entity_type)
        except ValueError:
            raise ValidationException(detail=f"Invalid entity_type: {data.entity_type}")

        assignment = await self.repository.get_active_assignment(entity_type_enum, data.entity_id, tenant_id)
        if not assignment:
            raise NotFoundException(detail="No active assignment found for this entity")

        old_user_id = assignment.user_id
        old_team_id = assignment.team_id

        # Validate new user/team
        if data.new_user_id:
            user_result = await self.db.execute(
                select(User).where(User.id == data.new_user_id, User.tenant_id == tenant_id)
            )
            if not user_result.scalar_one_or_none():
                raise NotFoundException(detail="New user not found")

        if data.new_team_id:
            team_result = await self.db.execute(
                select(Team).where(Team.id == data.new_team_id, Team.tenant_id == tenant_id)
            )
            if not team_result.scalar_one_or_none():
                raise NotFoundException(detail="New team not found")

        # Update assignment
        assignment.user_id = data.new_user_id
        assignment.team_id = data.new_team_id
        assignment.updated_by = actor_id

        updated = await self.repository.update_assignment(assignment)

        # Create history
        history = AssignmentHistory(
            assignment_id=assignment.id,
            action=AssignmentAction.REASSIGN,
            from_user_id=old_user_id,
            to_user_id=data.new_user_id,
            from_team_id=old_team_id,
            to_team_id=data.new_team_id,
            actor_id=actor_id,
            reason=data.reason,
            metadata=data.metadata,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return updated

    async def unassign(
        self, data: AssignmentUnassignRequest, tenant_id: UUID, actor_id: UUID
    ) -> Assignment:
        try:
            entity_type_enum = AssignableEntityType(data.entity_type)
        except ValueError:
            raise ValidationException(detail=f"Invalid entity_type: {data.entity_type}")

        assignment = await self.repository.get_active_assignment(entity_type_enum, data.entity_id, tenant_id)
        if not assignment:
            raise NotFoundException(detail="No active assignment found for this entity")

        old_user_id = assignment.user_id
        old_team_id = assignment.team_id

        assignment.is_active = False
        assignment.unassigned_at = datetime.now(timezone.utc)
        assignment.unassigned_by_id = actor_id
        assignment.unassign_reason = data.reason
        assignment.updated_by = actor_id

        updated = await self.repository.update_assignment(assignment)

        # Create history
        history = AssignmentHistory(
            assignment_id=assignment.id,
            action=AssignmentAction.UNASSIGN,
            from_user_id=old_user_id,
            from_team_id=old_team_id,
            actor_id=actor_id,
            reason=data.reason,
            metadata=data.metadata,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return updated

    async def bulk_assign(
        self, data: BulkAssignmentRequest, tenant_id: UUID, actor_id: UUID
    ) -> List[Assignment]:
        results = []
        for assignment_data in data.assignments:
            try:
                result = await self.create_assignment(assignment_data, tenant_id, actor_id)
                results.append(result)
            except ConflictException:
                # Skip if already assigned
                continue
        return results

    async def get_assignment_history(
        self, assignment_id: UUID, tenant_id: UUID, page: int = 1, page_size: int = 50
    ) -> Tuple[List[AssignmentHistory], int]:
        assignment = await self.get_assignment(assignment_id, tenant_id)
        return await self.repository.get_history_for_assignment(assignment_id, tenant_id, page, page_size)

    async def get_entity_assignment_history(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> List[AssignmentHistory]:
        try:
            entity_type_enum = AssignableEntityType(entity_type)
        except ValueError:
            raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        return await self.repository.get_history_for_entity(entity_type_enum, entity_id, tenant_id)

    # Escalation methods
    async def create_escalation(
        self, data: EscalationCreate, tenant_id: UUID, created_by: UUID
    ) -> Escalation:
        try:
            entity_type_enum = AssignableEntityType(data.entity_type)
            reason_enum = EscalationReason(data.reason)
        except ValueError as e:
            raise ValidationException(detail=str(e))

        # Get current assignment to find previous assignee
        current_assignment = await self.repository.get_active_assignment(entity_type_enum, data.entity_id, tenant_id)
        previous_assignee_id = current_assignment.user_id if current_assignment else None
        previous_team_id = current_assignment.team_id if current_assignment else None

        # Validate escalated_to user
        user_result = await self.db.execute(
            select(User).where(User.id == data.escalated_to_id, User.tenant_id == tenant_id)
        )
        if not user_result.scalar_one_or_none():
            raise NotFoundException(detail="Escalated to user not found")

        escalation = Escalation(
            entity_type=entity_type_enum,
            entity_id=data.entity_id,
            escalated_from_id=previous_assignee_id,
            escalated_to_id=data.escalated_to_id,
            escalated_by_id=created_by,
            reason=reason_enum,
            description=data.description,
            previous_assignee_id=previous_assignee_id,
            previous_team_id=previous_team_id,
            metadata=data.metadata,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        created = await self.repository.create_escalation(escalation)

        # Update assignment if exists
        if current_assignment:
            current_assignment.user_id = data.escalated_to_id
            current_assignment.updated_by = created_by
            await self.repository.update_assignment(current_assignment)

            # Create assignment history
            history = AssignmentHistory(
                assignment_id=current_assignment.id,
                action=AssignmentAction.ESCALATE,
                from_user_id=previous_assignee_id,
                to_user_id=data.escalated_to_id,
                actor_id=created_by,
                reason=data.description,
                metadata=data.metadata,
                tenant_id=tenant_id,
            )
            await self.repository.create_history(history)

        return created

    async def get_escalation(self, escalation_id: UUID, tenant_id: UUID) -> Escalation:
        escalation = await self.repository.get_escalation_by_id(escalation_id, tenant_id)
        if not escalation:
            raise NotFoundException(detail="Escalation not found")
        return escalation

    async def get_all_escalations(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        entity_type: Optional[str] = None,
        escalated_to_id: Optional[UUID] = None,
        escalated_by_id: Optional[UUID] = None,
        is_resolved: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[Escalation], int]:
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = AssignableEntityType(entity_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        return await self.repository.get_all_escalations(
            tenant_id, page, page_size, entity_type_enum, escalated_to_id, escalated_by_id, is_resolved, sort_by, sort_order
        )

    async def get_escalations_for_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> List[Escalation]:
        try:
            entity_type_enum = AssignableEntityType(entity_type)
        except ValueError:
            raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        return await self.repository.get_escalations_for_entity(entity_type_enum, entity_id, tenant_id)

    async def resolve_escalation(
        self, escalation_id: UUID, tenant_id: UUID, data: EscalationResolveRequest, actor_id: UUID
    ) -> Escalation:
        escalation = await self.get_escalation(escalation_id, tenant_id)

        if escalation.is_resolved:
            raise ValidationException(detail="Escalation is already resolved")

        escalation.is_resolved = True
        escalation.resolved_at = datetime.now(timezone.utc)
        escalation.resolved_by_id = actor_id
        escalation.resolution_notes = data.resolution_notes
        escalation.metadata = {**escalation.metadata, **(data.metadata or {})}
        escalation.updated_by = actor_id

        return await self.repository.update_escalation(escalation)