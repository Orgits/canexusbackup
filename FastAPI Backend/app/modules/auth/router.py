from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security.dependencies import get_current_user
from app.modules.auth.schemas import LoginRequest, RefreshRequest, Token, UserMeResponse
from app.modules.auth.service import AuthService
from app.modules.users.models import User

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_async_db),
):
    auth_service = AuthService(db)
    user = await auth_service.authenticate(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return await auth_service.login(user)


@router.post("/refresh", response_model=Token)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_async_db),
):
    auth_service = AuthService(db)
    tokens = await auth_service.refresh(request.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    auth_service = AuthService(db)
    await auth_service.logout(current_user)
    return None


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return UserMeResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        roles=current_user.roles,
        permissions=current_user.get_all_permissions(),
        tenant_id=str(current_user.tenant_id),
        tenant_name=current_user.tenant.name if current_user.tenant else "",
        is_active=current_user.is_active,
    )