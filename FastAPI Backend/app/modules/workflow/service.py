from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException, ValidationException
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
    WorkflowTransitionRequest,
)
from app.modules.workflow.repository import WorkflowRepository
from app.modules.users.models import User


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = WorkflowRepository(db)

    # Workflow Definition methods
    async def create_definition(
        self, data: WorkflowDefinitionCreate, tenant_id: UUID, created_by: UUID
    ) -> WorkflowDefinition:
        existing = await self.repository.get_definition_by_code(data.code, tenant_id)
        if existing:
            raise ConflictException(detail="Workflow definition with this code already exists")

        # Validate initial_state exists in states
        state_codes = [s.code for s in data.states]
        if data.initial_state not in state_codes:
            raise ValidationException(detail=f"Initial state '{data.initial_state}' not found in states")

        # Validate transitions reference valid states
        for t in data.transitions:
            if t.from_state not in state_codes:
                raise ValidationException(detail=f"Transition '{t.code}' references invalid from_state '{t.from_state}'")
            if t.to_state not in state_codes:
                raise ValidationException(detail=f"Transition '{t.code}' references invalid to_state '{t.to_state}'")

        definition = WorkflowDefinition(
            **data.model_dump(exclude={"states", "transitions"}),
            states=[s.model_dump() for s in data.states],
            transitions=[t.model_dump() for t in data.transitions],
            tenant_id=tenant_id,
            created_by=created_by,
        )

        created_definition = await self.repository.create_definition(definition)

        # Create transition definitions
        for t in data.transitions:
            transition_def = WorkflowTransitionDefinition(
                workflow_definition_id=created_definition.id,
                **t.model_dump(),
                tenant_id=tenant_id,
                created_by=created_by,
            )
            await self.repository.create_transition_definition(transition_def)

        # If this is the first default for this entity_type, make it default
        if data.is_default:
            await self._ensure_single_default(created_definition.entity_type, tenant_id, created_definition.id)

        await self.db.refresh(created_definition)
        return created_definition

    async def _ensure_single_default(self, entity_type: WorkflowEntityType, tenant_id: UUID, exclude_id: Optional[UUID] = None):
        # Find other defaults for this entity type
        result = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.entity_type == entity_type,
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.is_default == True,
            )
        )
        defaults = result.scalars().all()
        for d in defaults:
            if exclude_id and d.id == exclude_id:
                continue
            d.is_default = False
        await self.db.flush()

    async def get_definition_by_id(self, definition_id: UUID, tenant_id: UUID) -> WorkflowDefinition:
        definition = await self.repository.get_definition_by_id(definition_id, tenant_id)
        if not definition:
            raise NotFoundException(detail="Workflow definition not found")
        return definition

    async def get_all_definitions(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        entity_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[WorkflowDefinition], int]:
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = WorkflowEntityType(entity_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        return await self.repository.get_all_definitions(
            tenant_id, page, page_size, search, entity_type_enum, is_active, sort_by, sort_order
        )

    async def update_definition(
        self, definition_id: UUID, tenant_id: UUID, data: WorkflowDefinitionUpdate, updated_by: UUID
    ) -> WorkflowDefinition:
        definition = await self.get_definition_by_id(definition_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data:
            existing = await self.repository.get_definition_by_code(update_data["code"], tenant_id)
            if existing and existing.id != definition_id:
                raise ConflictException(detail="Workflow definition with this code already exists")

        if "is_default" in update_data and update_data["is_default"]:
            await self._ensure_single_default(definition.entity_type, tenant_id, definition_id)

        # Handle states and transitions updates
        if "states" in update_data:
            definition.states = [s.model_dump() if hasattr(s, 'model_dump') else s for s in update_data["states"]]
            del update_data["states"]

        if "transitions" in update_data:
            definition.transitions = [t.model_dump() if hasattr(t, 'model_dump') else t for t in update_data["transitions"]]
            # Recreate transition definitions
            await self.db.execute(
                select(WorkflowTransitionDefinition).where(
                    WorkflowTransitionDefinition.workflow_definition_id == definition_id
                ).delete()
            )
            for t in data.transitions:
                transition_def = WorkflowTransitionDefinition(
                    workflow_definition_id=definition_id,
                    **t.model_dump(),
                    tenant_id=tenant_id,
                    created_by=updated_by,
                )
                await self.repository.create_transition_definition(transition_def)
            del update_data["transitions"]

        for field, value in update_data.items():
            setattr(definition, field, value)
        definition.updated_by = updated_by
        return await self.repository.update_definition(definition)

    async def delete_definition(self, definition_id: UUID, tenant_id: UUID) -> None:
        definition = await self.get_definition_by_id(definition_id, tenant_id)
        if definition.is_system:
            raise ConflictException(detail="Cannot delete system workflow definition")
        await self.repository.delete_definition(definition)

    # Workflow Transition Definition methods
    async def create_transition_definition(
        self,
        workflow_definition_id: UUID,
        data: WorkflowTransitionDefinitionCreate,
        tenant_id: UUID,
        created_by: UUID,
    ) -> WorkflowTransitionDefinition:
        definition = await self.get_definition_by_id(workflow_definition_id, tenant_id)

        existing = await self.repository.get_transition_definition_by_code(workflow_definition_id, data.code, tenant_id)
        if existing:
            raise ConflictException(detail="Transition definition with this code already exists")

        # Validate states exist in definition
        state_codes = [s.get("code") for s in definition.states]
        if data.from_state not in state_codes:
            raise ValidationException(detail=f"from_state '{data.from_state}' not found in workflow states")
        if data.to_state not in state_codes:
            raise ValidationException(detail=f"to_state '{data.to_state}' not found in workflow states")

        transition = WorkflowTransitionDefinition(
            workflow_definition_id=workflow_definition_id,
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create_transition_definition(transition)

    async def get_transition_definition(self, transition_id: UUID, tenant_id: UUID) -> WorkflowTransitionDefinition:
        transition = await self.repository.get_transition_definition_by_id(transition_id, tenant_id)
        if not transition:
            raise NotFoundException(detail="Transition definition not found")
        return transition

    async def update_transition_definition(
        self, transition_id: UUID, tenant_id: UUID, data: WorkflowTransitionDefinitionUpdate, updated_by: UUID
    ) -> WorkflowTransitionDefinition:
        transition = await self.get_transition_definition(transition_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(transition, field, value)
        transition.updated_by = updated_by
        return await self.repository.update_transition_definition(transition)

    async def delete_transition_definition(self, transition_id: UUID, tenant_id: UUID) -> None:
        transition = await self.get_transition_definition(transition_id, tenant_id)
        await self.repository.delete_transition_definition(transition)

    # Workflow Instance methods
    async def create_instance(
        self, data: WorkflowInstanceCreate, tenant_id: UUID, created_by: UUID
    ) -> WorkflowInstance:
        definition = await self.get_definition_by_id(data.workflow_definition_id, tenant_id)

        # Check if instance already exists for this entity
        existing = await self.repository.get_instance_by_entity(data.entity_type, data.entity_id, tenant_id)
        if existing:
            raise ConflictException(detail="Workflow instance already exists for this entity")

        instance = WorkflowInstance(
            workflow_definition_id=data.workflow_definition_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            current_state=definition.initial_state,
            previous_state=None,
            assigned_user_id=data.assigned_user_id,
            assigned_team_id=data.assigned_team_id,
            context_data=data.context_data,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        created_instance = await self.repository.create_instance(instance)

        # Create initial history entry
        history = WorkflowTransitionHistory(
            workflow_instance_id=created_instance.id,
            from_state="",
            to_state=definition.initial_state,
            transition_code="INITIAL",
            actor_id=created_by,
            comment="Workflow instance created",
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return created_instance

    async def get_instance_by_id(self, instance_id: UUID, tenant_id: UUID) -> WorkflowInstance:
        instance = await self.repository.get_instance_by_id(instance_id, tenant_id)
        if not instance:
            raise NotFoundException(detail="Workflow instance not found")
        return instance

    async def get_instance_by_entity(self, entity_type: str, entity_id: UUID, tenant_id: UUID) -> WorkflowInstance:
        try:
            entity_type_enum = WorkflowEntityType(entity_type)
        except ValueError:
            raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        instance = await self.repository.get_instance_by_entity(entity_type_enum, entity_id, tenant_id)
        if not instance:
            raise NotFoundException(detail="Workflow instance not found for this entity")
        return instance

    async def get_or_create_instance(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID, created_by: UUID
    ) -> WorkflowInstance:
        try:
            return await self.get_instance_by_entity(entity_type, entity_id, tenant_id)
        except NotFoundException:
            entity_type_enum = WorkflowEntityType(entity_type)
            definition = await self.repository.get_default_definition(entity_type_enum, tenant_id)
            if not definition:
                raise NotFoundException(detail=f"No default workflow definition found for {entity_type}")
            return await self.create_instance(
                WorkflowInstanceCreate(
                    workflow_definition_id=definition.id,
                    entity_type=entity_type_enum,
                    entity_id=entity_id,
                ),
                tenant_id,
                created_by,
            )

    async def get_all_instances(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        entity_type: Optional[str] = None,
        workflow_definition_id: Optional[UUID] = None,
        current_state: Optional[str] = None,
        assigned_user_id: Optional[UUID] = None,
        assigned_team_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[WorkflowInstance], int]:
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = WorkflowEntityType(entity_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        return await self.repository.get_all_instances(
            tenant_id,
            page,
            page_size,
            search,
            entity_type_enum,
            workflow_definition_id,
            current_state,
            assigned_user_id,
            assigned_team_id,
            is_active,
            sort_by,
            sort_order,
        )

    async def update_instance(
        self, instance_id: UUID, tenant_id: UUID, data: WorkflowInstanceUpdate, updated_by: UUID
    ) -> WorkflowInstance:
        instance = await self.get_instance_by_id(instance_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(instance, field, value)
        instance.updated_by = updated_by
        return await self.repository.update_instance(instance)

    async def transition(
        self,
        instance_id: UUID,
        tenant_id: UUID,
        request: WorkflowTransitionRequest,
        actor_id: UUID,
        actor_team_id: Optional[UUID] = None,
    ) -> WorkflowInstance:
        instance = await self.get_instance_by_id(instance_id, tenant_id)

        if not instance.is_active:
            raise ValidationException(detail="Workflow instance is not active")

        if instance.completed_at:
            raise ValidationException(detail="Workflow instance is already completed")

        # Get available transitions from current state
        transitions = await self.repository.get_transitions_from_state(
            instance.workflow_definition_id, instance.current_state, tenant_id
        )

        # Find the requested transition
        transition_def = next((t for t in transitions if t.code == request.transition_code), None)
        if not transition_def:
            raise ValidationException(detail=f"Transition '{request.transition_code}' not available from current state")

        # Check permissions
        missing_permissions = []
        missing_roles = []

        if transition_def.required_permissions:
            # Check if actor has required permissions
            # This would integrate with the permission system
            pass

        if transition_def.required_roles:
            # Check if actor has required roles
            result = await self.db.execute(select(User).where(User.id == actor_id))
            user = result.scalar_one_or_none()
            if user:
                user_roles = [r.value for r in user.roles] if user.roles else []
                for role in transition_def.required_roles:
                    if role not in user_roles:
                        missing_roles.append(role)

        if missing_roles:
            raise ValidationException(detail=f"Missing required roles: {', '.join(missing_roles)}")

        from_state = instance.current_state
        to_state = transition_def.to_state

        # Update instance
        instance.previous_state = from_state
        instance.current_state = to_state
        instance.updated_by = actor_id

        if to_state in [s.get("code") for s in instance.definition.states if s.get("is_terminal")]:
            instance.is_active = False
            instance.completed_at = datetime.now(timezone.utc)

        await self.repository.update_instance(instance)

        # Create history entry
        history = WorkflowTransitionHistory(
            workflow_instance_id=instance.id,
            transition_definition_id=transition_def.id,
            from_state=from_state,
            to_state=to_state,
            transition_code=transition_def.code,
            actor_id=actor_id,
            actor_team_id=actor_team_id,
            comment=request.comment,
            reason=request.reason,
            extra_metadata=request.metadata,
            tenant_id=tenant_id,
        )
        await self.repository.create_history(history)

        return instance

    async def get_available_transitions(
        self, instance_id: UUID, tenant_id: UUID, actor_id: UUID
    ) -> List[WorkflowTransitionDefinition]:
        instance = await self.get_instance_by_id(instance_id, tenant_id)
        transitions = await self.repository.get_transitions_from_state(
            instance.workflow_definition_id, instance.current_state, tenant_id
        )
        # Filter by permissions/roles if needed
        return transitions

    async def get_history(
        self,
        instance_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[WorkflowTransitionHistory], int]:
        instance = await self.get_instance_by_id(instance_id, tenant_id)
        return await self.repository.get_history_for_instance(instance_id, tenant_id, page, page_size)