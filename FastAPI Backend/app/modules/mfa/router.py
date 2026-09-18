from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_tenant_db_session
from app.core.permissions.dependencies import require_permission
from app.core.permissions.registry import Permission
from app.core.tenancy import get_tenant_context
from app.modules.mfa.schemas import (
    MFAEnrollmentCreate,
    MFAEnrollmentDetailResponse,
    MFAEnrollmentResponse,
    MFAEnrollmentSetupResponse,
    MFAEnrollmentVerifyRequest,
    MFAEnrollmentDisableRequest,
    MFARecoveryCodesResponse,
    MFARecoveryCodeVerifyRequest,
    MFAUserStatusResponse,
    MFAVerificationLogListResponse,
    MFAVerificationLogResponse,
    MFALoginChallengeCreate,
    MFALoginChallengeResponse,
    MFALoginChallengeResult,
    MFALoginChallengeVerify,
)
from app.modules.mfa.service import MFAService
from app.modules.users.models import User

router = APIRouter(prefix="/mfa", tags=["Multi-Factor Authentication"])


# ============================================================================
# MFA Enrollment Endpoints
# ============================================================================

@router.post("/enroll", response_model=MFAEnrollmentSetupResponse)
async def start_mfa_enrollment(
    data: MFAEnrollmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Start MFA enrollment for a user (admin only) or self"""
    service = MFAService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    
    # If not admin, only allow self-enrollment
    if not current_user.has_permission(Permission.ADMIN_USERS_MANAGE):
        target_user_id = current_user.id
    else:
        target_user_id = data.user_id if hasattr(data, 'user_id') else current_user.id
    
    # Note: The schema doesn't have user_id, so we use current_user
    # In production, you might want a separate admin endpoint
    setup = await service.start_enrollment(
        current_user.id, tenant_context.tenant_id, data, ip_address, user_agent
    )
    return setup


@router.post("/enroll/verify", response_model=MFAEnrollmentResponse)
async def verify_mfa_enrollment(
    data: MFAEnrollmentVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Verify MFA enrollment with TOTP code"""
    service = MFAService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    
    enrollment = await service.verify_enrollment(data, tenant_context.tenant_id, ip_address, user_agent)
    return MFAEnrollmentResponse.model_validate(enrollment)


@router.get("/enrollments/me", response_model=MFAEnrollmentDetailResponse)
async def get_my_mfa_enrollment(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Get current user's MFA enrollment"""
    service = MFAService(db)
    enrollment = await service.get_user_enrollment(current_user.id, tenant_context.tenant_id)
    if not enrollment:
        raise NotFoundException(detail="No MFA enrollment found")
    return MFAEnrollmentDetailResponse.model_validate(enrollment)


@router.post("/enrollments/disable", response_model=MFAEnrollmentResponse)
async def disable_mfa_enrollment(
    data: MFAEnrollmentDisableRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Disable MFA enrollment"""
    service = MFAService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    
    enrollment = await service.disable_enrollment(data, tenant_context.tenant_id, current_user.id, ip_address, user_agent)
    return MFAEnrollmentResponse.model_validate(enrollment)


@router.post("/enrollments/{enrollment_id}/backup-codes", response_model=MFARecoveryCodesResponse)
async def regenerate_backup_codes(
    enrollment_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Regenerate backup codes"""
    service = MFAService(db)
    codes = await service.regenerate_backup_codes(enrollment_id, tenant_context.tenant_id, current_user.id)
    return codes


@router.post("/enrollments/verify-recovery-code", response_model=dict)
async def verify_recovery_code(
    data: MFARecoveryCodeVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Verify a recovery code"""
    service = MFAService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    
    success = await service.verify_recovery_code(data, tenant_context.tenant_id, ip_address, user_agent)
    return {"success": success}


# ============================================================================
# MFA Login Challenge Endpoints
# ============================================================================

@router.post("/challenge", response_model=MFALoginChallengeResponse)
async def create_login_challenge(
    data: MFALoginChallengeCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Create MFA login challenge"""
    service = MFAService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    
    challenge = await service.create_login_challenge(
        current_user.id, tenant_context.tenant_id, data, ip_address, user_agent
    )
    return challenge


@router.post("/challenge/verify", response_model=MFALoginChallengeResult)
async def verify_login_challenge(
    data: MFALoginChallengeVerify,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    # No permission required - this is called during login flow
):
    """Verify MFA login challenge"""
    service = MFAService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    
    result = await service.verify_login_challenge(data, tenant_context.tenant_id, ip_address, user_agent)
    return result


# ============================================================================
# MFA Status Endpoints
# ============================================================================

@router.get("/status/me", response_model=MFAUserStatusResponse)
async def get_my_mfa_status(
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Get current user's MFA status"""
    service = MFAService(db)
    return await service.get_user_status(current_user.id, tenant_context.tenant_id)


@router.get("/verification-logs", response_model=MFAVerificationLogListResponse)
async def list_verification_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    enrollment_id: UUID | None = None,
    user_id: UUID | None = None,
    method: str | None = None,
    result: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """List MFA verification logs"""
    service = MFAService(db)
    items, total = await service.get_verification_logs(
        tenant_context.tenant_id, page, page_size, enrollment_id, user_id,
        method, result, date_from, date_to
    )
    return MFAVerificationLogListResponse(
        items=[MFAVerificationLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# Admin endpoints for managing other users' MFA
@router.get("/enrollments/{user_id}", response_model=MFAEnrollmentDetailResponse)
async def get_user_mfa_enrollment(
    user_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Get user's MFA enrollment (admin)"""
    service = MFAService(db)
    enrollment = await service.get_user_enrollment(user_id, tenant_context.tenant_id)
    if not enrollment:
        raise NotFoundException(detail="No MFA enrollment found")
    return MFAEnrollmentDetailResponse.model_validate(enrollment)


@router.get("/status/{user_id}", response_model=MFAUserStatusResponse)
async def get_user_mfa_status(
    user_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
    tenant_context=Depends(get_tenant_context),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS_MANAGE)),
):
    """Get user's MFA status (admin)"""
    service = MFAService(db)
    return await service.get_user_status(user_id, tenant_context.tenant_id)