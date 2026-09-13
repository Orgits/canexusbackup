from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import get_tenant_context
from app.core.security.dependencies import get_current_user
from app.core.permissions.dependencies import require_permission
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.schemas import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
    AssignmentReassignRequest,
    AssignmentUnassignRequest,
    AssignmentHistoryResponse,
    AssignmentHistoryListResponse,
    EscalationCreate,
    EscalationUpdate,
    EscalationResponse,
    EscalationResolveRequest,
    EscalationListResponse,
    BulkAssignmentRequest,
    BulkReassignmentRequest,
)
from app.modules.users.models import User

router = APIRouter(prefix="/assignments", tags=["Assignment, Reassignment & Escalation"])


def get_assignment_service(db: AsyncSession = Depends(get_db)) -> AssignmentService:
    return AssignmentService(db)


# Assignment endpoints
@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create assignment",
)
async def create_assignment(
    data: AssignmentCreate,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.create")),
):
    return await assignment_service.create_assignment(data, tenant_context.tenant_id, current_user.id)


@router.post(
    "/bulk",
    response_model=List[AssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create assignments",
)
async def bulk_create_assignments(
    data: BulkAssignmentRequest,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.create")),
):
    return await assignment_service.bulk_assign(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "",
    response_model=List[AssignmentResponse],
    summary="List assignments",
)
async def list_assignments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    team_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    items, total = await assignment_service.get_all_assignments(
        tenant_context.tenant_id, page, page_size, entity_type, entity_id, user_id, team_id, is_active, sort_by, sort_order
    )
    return items


@router.get(
    "/active/{entity_type}/{entity_id}",
    response_model=AssignmentResponse,
    summary="Get active assignment for entity",
)
async def get_active_assignment(
    entity_type: str,
    entity_id: UUID,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    return await assignment_service.get_active_assignment(entity_type, entity_id, tenant_context.tenant_id)


@router.get(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Get assignment by ID",
)
async def get_assignment(
    assignment_id: UUID,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    return await assignment_service.get_assignment(assignment_id, tenant_context.tenant_id)


@router.patch(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Update assignment",
)
async def update_assignment(
    assignment_id: UUID,
    data: AssignmentUpdate,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.update")),
):
    return await assignment_service.update_assignment(assignment_id, tenant_context.tenant_id, data, current_user.id)


@router.post(
    "/reassign",
    response_model=AssignmentResponse,
    summary="Reassign entity",
)
async def reassign_entity(
    data: AssignmentReassignRequest,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.reassign")),
):
    return await assignment_service.reassign(data, tenant_context.tenant_id, current_user.id)


@router.post(
    "/unassign",
    response_model=AssignmentResponse,
    summary="Unassign entity",
)
async def unassign_entity(
    data: AssignmentUnassignRequest,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.reassign")),
):
    return await assignment_service.unassign(data, tenant_context.tenant_id, current_user.id)


@router.post(
    "/bulk-reassign",
    response_model=List[AssignmentResponse],
    summary="Bulk reassign entities",
)
async def bulk_reassign_entities(
    data: BulkReassignmentRequest,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.reassign")),
):
    results = []
    for reassignment in data.reassignments:
        try:
            result = await assignment_service.reassign(reassignment, tenant_context.tenant_id, current_user.id)
            results.append(result)
        except NotFoundException:
            continue
    return results


# Assignment History endpoints
@router.get(
    "/{assignment_id}/history",
    response_model=AssignmentHistoryListResponse,
    summary="Get assignment history",
)
async def get_assignment_history(
    assignment_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    items, total = await assignment_service.get_assignment_history(assignment_id, tenant_context.tenant_id, page, page_size)
    return AssignmentHistoryListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/history/entity/{entity_type}/{entity_id}",
    response_model=List[AssignmentHistoryResponse],
    summary="Get assignment history for entity",
)
async def get_entity_assignment_history(
    entity_type: str,
    entity_id: UUID,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    return await assignment_service.get_entity_assignment_history(entity_type, entity_id, tenant_context.tenant_id)


# Escalation endpoints
@router.post(
    "/escalate",
    response_model=EscalationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create escalation",
)
async def create_escalation(
    data: EscalationCreate,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.escalate")),
):
    return await assignment_service.create_escalation(data, tenant_context.tenant_id, current_user.id)


@router.get(
    "/escalations",
    response_model=EscalationListResponse,
    summary="List escalations",
)
async def list_escalations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = None,
    escalated_to_id: Optional[UUID] = None,
    escalated_by_id: Optional[UUID] = None,
    is_resolved: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    items, total = await assignment_service.get_all_escalations(
        tenant_context.tenant_id, page, page_size, entity_type, escalated_to_id, escalated_by_id, is_resolved, sort_by, sort_order
    )
    return EscalationListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/escalations/{escalation_id}",
    response_model=EscalationResponse,
    summary="Get escalation by ID",
)
async def get_escalation(
    escalation_id: UUID,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    return await assignment_service.get_escalation(escalation_id, tenant_context.tenant_id)


@router.get(
    "/escalations/entity/{entity_type}/{entity_id}",
    response_model=List[EscalationResponse],
    summary="Get escalations for entity",
)
async def get_escalations_for_entity(
    entity_type: str,
    entity_id: UUID,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.read")),
):
    return await assignment_service.get_escalations_for_entity(entity_type, entity_id, tenant_context.tenant_id)


@router.post(
    "/escalations/{escalation_id}/resolve",
    response_model=EscalationResponse,
    summary="Resolve escalation",
)
async def resolve_escalation(
    escalation_id: UUID,
    data: EscalationResolveRequest,
    assignment_service: AssignmentService = Depends(get_assignment_service),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("assignments.escalate")),
):
    return await assignment_service.resolve_escalation(escalation_id, tenant_context.tenant_id, data, current_user.id)