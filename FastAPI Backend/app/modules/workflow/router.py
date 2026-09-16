from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.security.dependencies import get_current_user, get_token_payload
from app.core.tenancy import get_tenant_context
from app.modules.users.models import User
from app.modules.workflow.schemas import (
    AvailableTransitionResponse,
    WorkflowDefinitionCreate,
    WorkflowDefinitionListResponse,
    WorkflowDefinitionResponse,
    WorkflowDefinitionUpdate,
    WorkflowInstanceCreate,
    WorkflowInstanceListResponse,
    WorkflowInstanceResponse,
    WorkflowInstanceUpdate,
    WorkflowTransitionDefinitionCreate,
    WorkflowTransitionDefinitionResponse,
    WorkflowTransitionDefinitionUpdate,
    WorkflowTransitionHistoryListResponse,
    WorkflowTransitionRequest,
)
from app.modules.workflow.service import WorkflowService

router = APIRouter(prefix="/workflow", tags=["Workflow Engine"])


# Dependency
def get_workflow_service(db: AsyncSession = Depends(get_tenant_db_session)) -> WorkflowService:
    return WorkflowService(db)


# Workflow Definition endpoints
@router.post(
    "/definitions",
    response_model=WorkflowDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow definition",
)
async def create_workflow_definition(
    data: WorkflowDefinitionCreate,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.create")),
):
    return await workflow_service.create_definition(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/definitions",
    response_model=WorkflowDefinitionListResponse,
    summary="List workflow definitions",
)
async def list_workflow_definitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    entity_type: str | None = None,
    is_active: bool | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    items, total = await workflow_service.get_all_definitions(
        tenant_context.tenant_id, page, page_size, search, entity_type, is_active, sort_by, sort_order
    )
    return WorkflowDefinitionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/definitions/default/{entity_type}",
    response_model=WorkflowDefinitionResponse,
    summary="Get default workflow definition for entity type",
)
async def get_default_workflow_definition(
    entity_type: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    from app.modules.workflow.models import WorkflowEntityType
    try:
        entity_type_enum = WorkflowEntityType(entity_type)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid entity_type: {entity_type}")

    definition = await workflow_service.repository.get_default_definition(entity_type_enum, tenant_context.tenant_id)
    if not definition:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No default workflow definition found for {entity_type}")
    return definition


@router.get(
    "/definitions/{definition_id}",
    response_model=WorkflowDefinitionResponse,
    summary="Get workflow definition by ID",
)
async def get_workflow_definition(
    definition_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    return await workflow_service.get_definition_by_id(definition_id, tenant_context.tenant_id)


@router.patch(
    "/definitions/{definition_id}",
    response_model=WorkflowDefinitionResponse,
    summary="Update workflow definition",
)
async def update_workflow_definition(
    definition_id: UUID,
    data: WorkflowDefinitionUpdate,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.update")),
):
    return await workflow_service.update_definition(definition_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/definitions/{definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workflow definition",
)
async def delete_workflow_definition(
    definition_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.delete")),
):
    await workflow_service.delete_definition(definition_id, tenant_context.tenant_id)


# Workflow Transition Definition endpoints
@router.post(
    "/definitions/{definition_id}/transitions",
    response_model=WorkflowTransitionDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transition definition",
)
async def create_transition_definition(
    definition_id: UUID,
    data: WorkflowTransitionDefinitionCreate,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.update")),
):
    return await workflow_service.create_transition_definition(definition_id, data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/definitions/{definition_id}/transitions",
    response_model=list[WorkflowTransitionDefinitionResponse],
    summary="List transitions for workflow definition",
)
async def list_transition_definitions(
    definition_id: UUID,
    is_active: bool | None = None,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    # Verify definition exists
    await workflow_service.get_definition_by_id(definition_id, tenant_context.tenant_id)
    return await workflow_service.repository.get_transitions_for_definition(definition_id, tenant_context.tenant_id, is_active)


@router.get(
    "/definitions/{definition_id}/transitions/from/{from_state}",
    response_model=list[WorkflowTransitionDefinitionResponse],
    summary="Get transitions from a specific state",
)
async def get_transitions_from_state(
    definition_id: UUID,
    from_state: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    await workflow_service.get_definition_by_id(definition_id, tenant_context.tenant_id)
    return await workflow_service.repository.get_transitions_from_state(definition_id, from_state, tenant_context.tenant_id)


@router.patch(
    "/transitions/{transition_id}",
    response_model=WorkflowTransitionDefinitionResponse,
    summary="Update transition definition",
)
async def update_transition_definition(
    transition_id: UUID,
    data: WorkflowTransitionDefinitionUpdate,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.update")),
):
    return await workflow_service.update_transition_definition(transition_id, tenant_context.tenant_id, data, current_user.id)


@router.delete(
    "/transitions/{transition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete transition definition",
)
async def delete_transition_definition(
    transition_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.delete")),
):
    await workflow_service.delete_transition_definition(transition_id, tenant_context.tenant_id)


# Workflow Instance endpoints
@router.post(
    "/instances",
    response_model=WorkflowInstanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow instance",
)
async def create_workflow_instance(
    data: WorkflowInstanceCreate,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.create")),
):
    return await workflow_service.create_instance(data, tenant_context.tenant_id, current_user.id)


@router.post(
    "/instances/get-or-create",
    response_model=WorkflowInstanceResponse,
    summary="Get or create workflow instance for entity",
)
async def get_or_create_workflow_instance(
    entity_type: str = Query(..., description="Entity type (matter, compliance_cycle, notice, review, task, audit_workpaper, document)"),
    entity_id: UUID = Query(..., description="Entity ID"),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.create")),
):
    return await workflow_service.get_or_create_instance(entity_type, entity_id, tenant_context.tenant_id, current_user.id)


@router.get(
    "/instances",
    response_model=WorkflowInstanceListResponse,
    summary="List workflow instances",
)
async def list_workflow_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    entity_type: str | None = None,
    workflow_definition_id: UUID | None = None,
    current_state: str | None = None,
    assigned_user_id: UUID | None = None,
    assigned_team_id: UUID | None = None,
    is_active: bool | None = None,
    sort_by: str | None = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    items, total = await workflow_service.get_all_instances(
        tenant_context.tenant_id,
        page,
        page_size,
        search,
        entity_type,
        workflow_definition_id,
        current_state,
        assigned_user_id,
        assigned_team_id,
        is_active,
        sort_by,
        sort_order,
    )
    return WorkflowInstanceListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/instances/by-entity/{entity_type}/{entity_id}",
    response_model=WorkflowInstanceResponse,
    summary="Get workflow instance by entity",
)
async def get_workflow_instance_by_entity(
    entity_type: str,
    entity_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    return await workflow_service.get_instance_by_entity(entity_type, entity_id, tenant_context.tenant_id)


@router.get(
    "/instances/{instance_id}",
    response_model=WorkflowInstanceResponse,
    summary="Get workflow instance by ID",
)
async def get_workflow_instance(
    instance_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    return await workflow_service.get_instance_by_id(instance_id, tenant_context.tenant_id)


@router.patch(
    "/instances/{instance_id}",
    response_model=WorkflowInstanceResponse,
    summary="Update workflow instance",
)
async def update_workflow_instance(
    instance_id: UUID,
    data: WorkflowInstanceUpdate,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.update")),
):
    return await workflow_service.update_instance(instance_id, tenant_context.tenant_id, data, current_user.id)


@router.post(
    "/instances/{instance_id}/transition",
    response_model=WorkflowInstanceResponse,
    summary="Execute workflow transition",
)
async def execute_workflow_transition(
    instance_id: UUID,
    request: WorkflowTransitionRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.transition")),
):
    return await workflow_service.transition(instance_id, tenant_context.tenant_id, request, current_user.id)


@router.get(
    "/instances/{instance_id}/available-transitions",
    response_model=list[AvailableTransitionResponse],
    summary="Get available transitions for current state",
)
async def get_available_transitions(
    instance_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    payload=Depends(get_token_payload),
    _: None = Depends(require_permission("workflow.read")),
):
    transitions = await workflow_service.get_available_transitions(instance_id, tenant_context.tenant_id, current_user.id)

    user_permissions = set(payload.permissions)
    user_roles = set(payload.roles)

    result = []
    for t in transitions:
        missing_permissions = []
        missing_roles = []

        for perm in t.required_permissions:
            if perm not in user_permissions:
                missing_permissions.append(perm)

        for role in t.required_roles:
            if role not in user_roles:
                missing_roles.append(role)

        can_execute = len(missing_permissions) == 0 and len(missing_roles) == 0

        result.append(AvailableTransitionResponse(
            transition=t,
            can_execute=can_execute,
            missing_permissions=missing_permissions,
            missing_roles=missing_roles,
        ))
    return result


@router.get(
    "/instances/{instance_id}/history",
    response_model=WorkflowTransitionHistoryListResponse,
    summary="Get workflow transition history",
)
async def get_workflow_history(
    instance_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow.read")),
):
    items, total = await workflow_service.get_history(instance_id, tenant_context.tenant_id, page, page_size)
    return WorkflowTransitionHistoryListResponse(items=items, total=total, page=page, page_size=page_size)
