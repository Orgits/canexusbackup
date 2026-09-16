from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.tasks.schemas import TaskAction, TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.modules.tasks.service import TaskService
from app.modules.users.models import User

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TASKS_CREATE)),
):
    service = TaskService(db)
    task = await service.create(data, tenant_context.tenant_id, current_user.id)
    return TaskResponse.model_validate(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    client_id: UUID = None,
    matter_id: UUID = None,
    status: str = None,
    priority: str = None,
    assignee_id: UUID = None,
    team_id: UUID = None,
    due_date_from: datetime = None,
    due_date_to: datetime = None,
    tags: str = None,
    overdue_only: bool = False,
    sort_by: str = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TASKS_READ)),
):
    service = TaskService(db)
    tag_list = tags.split(",") if tags else None
    items, total = await service.get_all(
        tenant_context.tenant_id, page, page_size, search, client_id, matter_id,
        status, priority, assignee_id, team_id, due_date_from, due_date_to,
        tag_list, overdue_only, sort_by, sort_order
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TASKS_READ)),
):
    service = TaskService(db)
    task = await service.get_by_id(task_id, tenant_context.tenant_id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TASKS_UPDATE)),
):
    service = TaskService(db)
    task = await service.update(task_id, tenant_context.tenant_id, data, current_user.id)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/action", response_model=TaskResponse)
async def perform_task_action(
    task_id: UUID,
    action: TaskAction,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TASKS_UPDATE)),
):
    service = TaskService(db)
    task = await service.perform_action(task_id, tenant_context.tenant_id, action, current_user.id)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.TASKS_DELETE)),
):
    service = TaskService(db)
    await service.delete(task_id, tenant_context.tenant_id)
