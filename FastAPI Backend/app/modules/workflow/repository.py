from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.modules.workflow.models import (
    WorkflowDefinition,
    WorkflowTransitionDefinition,
    WorkflowInstance,
    WorkflowTransitionHistory,
    WorkflowEntityType,
)
from app.modules.workflow.schemas import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowTransitionDefinitionCreate,
    WorkflowTransitionDefinitionUpdate,
    WorkflowInstanceCreate,
    WorkflowInstanceUpdate,
)


class WorkflowRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Workflow Definition methods
    async def create_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        self.db.add(definition)
        await self.db.flush()
        await self.db.refresh(definition)
        return definition

    async def get_definition_by_id(self, definition_id: UUID, tenant_id: UUID) -> Optional[WorkflowDefinition]:
        result = await self.db.execute(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.id == definition_id,
                WorkflowDefinition.tenant_id == tenant_id,
            )
            .options(selectinload(WorkflowDefinition.transitions_def))
        )
        return result.scalar_one_or_none()

    async def get_definition_by_code(self, code: str, tenant_id: UUID) -> Optional[WorkflowDefinition]:
        result = await self.db.execute(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.code == code,
                WorkflowDefinition.tenant_id == tenant_id,
            )
            .options(selectinload(WorkflowDefinition.transitions_def))
        )
        return result.scalar_one_or_none()

    async def get_default_definition(self, entity_type: WorkflowEntityType, tenant_id: UUID) -> Optional[WorkflowDefinition]:
        result = await self.db.execute(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.entity_type == entity_type,
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.is_default == True,
                WorkflowDefinition.is_active == True,
            )
            .options(selectinload(WorkflowDefinition.transitions_def))
        )
        return result.scalar_one_or_none()

    async def get_all_definitions(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        entity_type: Optional[WorkflowEntityType] = None,
        is_active: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[WorkflowDefinition], int]:
        query = select(WorkflowDefinition).where(WorkflowDefinition.tenant_id == tenant_id)
        count_query = select(func.count(WorkflowDefinition.id)).where(WorkflowDefinition.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    WorkflowDefinition.name.ilike(search_term),
                    WorkflowDefinition.code.ilike(search_term),
                    WorkflowDefinition.description.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    WorkflowDefinition.name.ilike(search_term),
                    WorkflowDefinition.code.ilike(search_term),
                    WorkflowDefinition.description.ilike(search_term),
                )
            )

        if entity_type:
            query = query.where(WorkflowDefinition.entity_type == entity_type)
            count_query = count_query.where(WorkflowDefinition.entity_type == entity_type)

        if is_active is not None:
            query = query.where(WorkflowDefinition.is_active == is_active)
            count_query = count_query.where(WorkflowDefinition.is_active == is_active)

        # Sorting
        if sort_by and hasattr(WorkflowDefinition, sort_by):
            column = getattr(WorkflowDefinition, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(WorkflowDefinition.created_at.desc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        definitions = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(definitions), total

    async def update_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        await self.db.flush()
        await self.db.refresh(definition)
        return definition

    async def delete_definition(self, definition: WorkflowDefinition) -> None:
        await self.db.delete(definition)
        await self.db.flush()

    # Workflow Transition Definition methods
    async def create_transition_definition(self, transition: WorkflowTransitionDefinition) -> WorkflowTransitionDefinition:
        self.db.add(transition)
        await self.db.flush()
        await self.db.refresh(transition)
        return transition

    async def get_transition_definition_by_id(
        self, transition_id: UUID, tenant_id: UUID
    ) -> Optional[WorkflowTransitionDefinition]:
        result = await self.db.execute(
            select(WorkflowTransitionDefinition).where(
                WorkflowTransitionDefinition.id == transition_id,
                WorkflowTransitionDefinition.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_transition_definition_by_code(
        self, workflow_definition_id: UUID, code: str, tenant_id: UUID
    ) -> Optional[WorkflowTransitionDefinition]:
        result = await self.db.execute(
            select(WorkflowTransitionDefinition).where(
                WorkflowTransitionDefinition.workflow_definition_id == workflow_definition_id,
                WorkflowTransitionDefinition.code == code,
                WorkflowTransitionDefinition.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_transitions_for_definition(
        self, workflow_definition_id: UUID, tenant_id: UUID, is_active: Optional[bool] = None
    ) -> List[WorkflowTransitionDefinition]:
        query = select(WorkflowTransitionDefinition).where(
            WorkflowTransitionDefinition.workflow_definition_id == workflow_definition_id,
            WorkflowTransitionDefinition.tenant_id == tenant_id,
        )
        if is_active is not None:
            query = query.where(WorkflowTransitionDefinition.is_active == is_active)
        query = query.order_by(WorkflowTransitionDefinition.created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_transitions_from_state(
        self, workflow_definition_id: UUID, from_state: str, tenant_id: UUID, is_active: bool = True
    ) -> List[WorkflowTransitionDefinition]:
        result = await self.db.execute(
            select(WorkflowTransitionDefinition).where(
                WorkflowTransitionDefinition.workflow_definition_id == workflow_definition_id,
                WorkflowTransitionDefinition.from_state == from_state,
                WorkflowTransitionDefinition.tenant_id == tenant_id,
                WorkflowTransitionDefinition.is_active == is_active,
            ).order_by(WorkflowTransitionDefinition.created_at)
        )
        return list(result.scalars().all())

    async def update_transition_definition(self, transition: WorkflowTransitionDefinition) -> WorkflowTransitionDefinition:
        await self.db.flush()
        await self.db.refresh(transition)
        return transition

    async def delete_transition_definition(self, transition: WorkflowTransitionDefinition) -> None:
        await self.db.delete(transition)
        await self.db.flush()

    # Workflow Instance methods
    async def create_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def get_instance_by_id(self, instance_id: UUID, tenant_id: UUID) -> Optional[WorkflowInstance]:
        result = await self.db.execute(
            select(WorkflowInstance)
            .where(
                WorkflowInstance.id == instance_id,
                WorkflowInstance.tenant_id == tenant_id,
            )
            .options(
                selectinload(WorkflowInstance.definition).selectinload(WorkflowDefinition.transitions_def),
                selectinload(WorkflowInstance.assigned_user),
            )
        )
        return result.scalar_one_or_none()

    async def get_instance_by_entity(self, entity_type: WorkflowEntityType, entity_id: UUID, tenant_id: UUID) -> Optional[WorkflowInstance]:
        result = await self.db.execute(
            select(WorkflowInstance)
            .where(
                WorkflowInstance.entity_type == entity_type,
                WorkflowInstance.entity_id == entity_id,
                WorkflowInstance.tenant_id == tenant_id,
            )
            .options(
                selectinload(WorkflowInstance.definition).selectinload(WorkflowDefinition.transitions_def),
                selectinload(WorkflowInstance.assigned_user),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_instances(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        entity_type: Optional[WorkflowEntityType] = None,
        workflow_definition_id: Optional[UUID] = None,
        current_state: Optional[str] = None,
        assigned_user_id: Optional[UUID] = None,
        assigned_team_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[WorkflowInstance], int]:
        query = select(WorkflowInstance).where(WorkflowInstance.tenant_id == tenant_id)
        count_query = select(func.count(WorkflowInstance.id)).where(WorkflowInstance.tenant_id == tenant_id)

        if entity_type:
            query = query.where(WorkflowInstance.entity_type == entity_type)
            count_query = count_query.where(WorkflowInstance.entity_type == entity_type)

        if workflow_definition_id:
            query = query.where(WorkflowInstance.workflow_definition_id == workflow_definition_id)
            count_query = count_query.where(WorkflowInstance.workflow_definition_id == workflow_definition_id)

        if current_state:
            query = query.where(WorkflowInstance.current_state == current_state)
            count_query = count_query.where(WorkflowInstance.current_state == current_state)

        if assigned_user_id:
            query = query.where(WorkflowInstance.assigned_user_id == assigned_user_id)
            count_query = count_query.where(WorkflowInstance.assigned_user_id == assigned_user_id)

        if assigned_team_id:
            query = query.where(WorkflowInstance.assigned_team_id == assigned_team_id)
            count_query = count_query.where(WorkflowInstance.assigned_team_id == assigned_team_id)

        if is_active is not None:
            query = query.where(WorkflowInstance.is_active == is_active)
            count_query = count_query.where(WorkflowInstance.is_active == is_active)

        if sort_by and hasattr(WorkflowInstance, sort_by):
            column = getattr(WorkflowInstance, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(WorkflowInstance.created_at.desc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(WorkflowInstance.definition),
                selectinload(WorkflowInstance.assigned_user),
            )
        )
        instances = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(instances), total

    async def update_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete_instance(self, instance: WorkflowInstance) -> None:
        await self.db.delete(instance)
        await self.db.flush()

    # Workflow Transition History methods
    async def create_history(self, history: WorkflowTransitionHistory) -> WorkflowTransitionHistory:
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def get_history_for_instance(
        self,
        instance_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[WorkflowTransitionHistory], int]:
        query = (
            select(WorkflowTransitionHistory)
            .where(
                WorkflowTransitionHistory.workflow_instance_id == instance_id,
                WorkflowTransitionHistory.tenant_id == tenant_id,
            )
            .order_by(WorkflowTransitionHistory.created_at.desc())
        )
        count_query = select(func.count(WorkflowTransitionHistory.id)).where(
            WorkflowTransitionHistory.workflow_instance_id == instance_id,
            WorkflowTransitionHistory.tenant_id == tenant_id,
        )

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(selectinload(WorkflowTransitionHistory.actor))
        )
        history = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(history), total