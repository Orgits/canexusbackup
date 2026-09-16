from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.security.dependencies import get_current_user, get_token_payload
from app.modules.auth.schemas import (
    AccountLockStatusResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    Token,
    UnlockAccountRequest,
    UnlockAccountResponse,
    UserMeResponse,
)
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
        # Check if account is locked
        if await auth_service.is_account_locked(request.email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account temporarily locked due to multiple failed login attempts. Try again later.",
            )
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
    payload=Depends(get_token_payload),
    db: AsyncSession = Depends(get_async_db),
):
    auth_service = AuthService(db)
    await auth_service.logout(current_user, access_token_jti=payload.jti)


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    auth_service = AuthService(db)
    success, errors = await auth_service.change_password(current_user, request.current_password, request.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )
    return ChangePasswordResponse(success=True, errors=[])


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    auth_service = AuthService(db)
    success, errors = await auth_service.reset_password(request.email, request.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )
    return ResetPasswordResponse(success=True, errors=[])


@router.post("/unlock-account", response_model=UnlockAccountResponse)
async def unlock_account(
    request: UnlockAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    auth_service = AuthService(db)
    await auth_service.unlock_account(request.email)
    return UnlockAccountResponse(success=True)


@router.get("/lock-status/{email}", response_model=AccountLockStatusResponse)
async def get_lock_status(
    email: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    auth_service = AuthService(db)
    is_locked = await auth_service.is_account_locked(email)
    failed_attempts = await auth_service.get_failed_login_attempts(email)
    return AccountLockStatusResponse(
        email=email,
        is_locked=is_locked,
        failed_attempts=failed_attempts,
    )


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
