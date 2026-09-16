from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.security.dependencies import get_current_active_user
from app.core.tenancy import get_tenant_context
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.modules.users.service import TeamService, UserService

router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = UserService(db)
    user = await service.create(data, tenant_context.tenant_id)
    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    is_active: bool = None,
    role: str = None,
    team_id: UUID = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = UserService(db)
    items, total = await service.get_all(tenant_context.tenant_id, page, page_size, search, is_active, role, team_id)
    return UserListResponse(
        items=[UserResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    return UserResponse.model_validate(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = UserService(db)
    user = await service.get_by_id(user_id, tenant_context.tenant_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = UserService(db)
    user = await service.update(user_id, tenant_context.tenant_id, data)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = UserService(db)
    await service.delete(user_id, tenant_context.tenant_id)


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    user_id: UUID,
    new_password: str,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = UserService(db)
    await service.update_password(user_id, tenant_context.tenant_id, new_password)


team_router = APIRouter(prefix="/teams", tags=["Teams"])


@team_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    name: str,
    description: str = None,
    department: str = None,
    specialization: list[str] = None,
    lead_id: UUID = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = TeamService(db)
    team = await service.create(
        tenant_context.tenant_id,
        name=name,
        description=description,
        department=department,
        specialization=specialization or [],
        lead_id=lead_id,
    )
    return UserResponse.model_validate(team)


@team_router.get("", response_model=UserListResponse)
async def list_teams(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = TeamService(db)
    items, total = await service.get_all(tenant_context.tenant_id, page, page_size, search, is_active)
    return UserListResponse(
        items=[UserResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@team_router.get("/{team_id}", response_model=UserResponse)
async def get_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = TeamService(db)
    team = await service.get_by_id(team_id, tenant_context.tenant_id)
    return UserResponse.model_validate(team)


@team_router.patch("/{team_id}", response_model=UserResponse)
async def update_team(
    team_id: UUID,
    name: str = None,
    description: str = None,
    department: str = None,
    specialization: list[str] = None,
    is_active: bool = None,
    lead_id: UUID = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = TeamService(db)
    team = await service.update(
        team_id,
        tenant_context.tenant_id,
        name=name,
        description=description,
        department=department,
        specialization=specialization,
        is_active=is_active,
        lead_id=lead_id,
    )
    return UserResponse.model_validate(team)


@team_router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    service = TeamService(db)
    await service.delete(team_id, tenant_context.tenant_id)


router.include_router(team_router)
