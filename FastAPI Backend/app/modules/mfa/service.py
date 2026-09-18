import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException, RateLimitException
from app.core.security.encryption import encrypt_field, decrypt_field
from app.modules.mfa.models import MFAEnrollment, MFAVerificationLog, MFALoginChallenge, MFAEnrollmentStatus, MFAMethod
from app.modules.mfa.repository import MFAEnrollmentRepository, MFAVerificationLogRepository, MFALoginChallengeRepository
from app.modules.mfa.schemas import (
    MFAEnrollmentCreate,
    MFAEnrollmentSetupResponse,
    MFAEnrollmentVerifyRequest,
    MFAEnrollmentDisableRequest,
    MFALoginChallengeCreate,
    MFALoginChallengeResponse,
    MFALoginChallengeResult,
    MFALoginChallengeVerify,
    MFARecoveryCodesResponse,
    MFARecoveryCodeVerifyRequest,
    MFAUserStatusResponse,
)
from app.modules.users.models import User
from app.core.tenancy import get_tenant_context


class MFAService:
    # Rate limiting constants
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    CHALLENGE_EXPIRY_MINUTES = 5
    VERIFICATION_WINDOW = 1  # Allow 1 period before/after for clock skew

    def __init__(self, db: AsyncSession):
        self.db = db
        self.enrollment_repo = MFAEnrollmentRepository(db)
        self.log_repo = MFAVerificationLogRepository(db)
        self.challenge_repo = MFALoginChallengeRepository(db)

    def _generate_totp_secret(self) -> str:
        return pyotp.random_base32()

    def _generate_backup_codes(self, count: int = 10, length: int = 8) -> list[str]:
        return [secrets.token_hex(length // 2).upper() for _ in range(count)]

    def _generate_qr_code(self, uri: str) -> str:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white", image_factory=qrcode.image.svg.SvgImage)
        buffer = BytesIO()
        img.save(buffer)
        return base64.b64encode(buffer.getvalue()).decode()

    def _get_totp_uri(self, secret: str, email: str, issuer: str) -> str:
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

    def _verify_totp(self, secret: str, code: str, algorithm: str = "SHA1", digits: int = 6, period: int = 30) -> bool:
        totp = pyotp.TOTP(secret, algorithm=algorithm, digits=digits, interval=period)
        return totp.verify(code, valid_window=self.VERIFICATION_WINDOW)

    def _hash_code(self, code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    async def _check_rate_limit(self, enrollment: MFAEnrollment) -> None:
        if enrollment.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            if enrollment.last_failed_at:
                lockout_end = enrollment.last_failed_at + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                if datetime.utcnow() < lockout_end:
                    raise RateLimitException(
                        detail=f"Too many failed attempts. Try again after {lockout_end.isoformat()}"
                    )
                else:
                    # Reset failed attempts after lockout period
                    enrollment.failed_attempts = 0
                    await self.enrollment_repo.update(enrollment)

    async def _record_failed_attempt(self, enrollment: MFAEnrollment) -> None:
        enrollment.failed_attempts += 1
        enrollment.last_failed_at = datetime.utcnow()
        if enrollment.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            enrollment.status = MFAEnrollmentStatus.LOCKED.value
            enrollment.locked_at = datetime.utcnow()
            enrollment.lock_reason = "Too many failed verification attempts"
        await self.enrollment_repo.update(enrollment)

    async def _record_success(self, enrollment: MFAEnrollment) -> None:
        enrollment.failed_attempts = 0
        enrollment.last_failed_at = None
        enrollment.last_used_at = datetime.utcnow()
        if enrollment.status == MFAEnrollmentStatus.LOCKED.value:
            enrollment.status = MFAEnrollmentStatus.ACTIVE.value
            enrollment.locked_at = None
            enrollment.lock_reason = None
        await self.enrollment_repo.update(enrollment)

    async def _log_verification(
        self,
        enrollment_id: UUID,
        user_id: UUID,
        method: MFAMethod,
        result: str,
        tenant_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        challenge_id: str | None = None,
    ) -> None:
        log = MFAVerificationLog(
            enrollment_id=enrollment_id,
            user_id=user_id,
            method=method,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            challenge_id=challenge_id,
            tenant_id=tenant_id,
            created_by=user_id,
        )
        await self.log_repo.create(log)

    # ============================================================================
    # Enrollment Methods
    # ============================================================================

    async def start_enrollment(self, user_id: UUID, tenant_id: UUID, data: MFAEnrollmentCreate, ip_address: str | None = None, user_agent: str | None = None) -> MFAEnrollmentSetupResponse:
        # Validate user
        user_result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise NotFoundException(detail="User not found")

        # Check if enrollment already exists
        existing = await self.enrollment_repo.get_by_user_and_method(user_id, data.method, tenant_id)
        if existing:
            if existing.status == MFAEnrollmentStatus.ACTIVE.value:
                raise ValidationException(detail=f"{data.method.value} is already enabled for this user")
            # Delete pending/disabled enrollment to start fresh
            await self.enrollment_repo.delete(existing)

        # Generate secret and backup codes
        secret = self._generate_totp_secret()
        backup_codes = self._generate_backup_codes()

        # Create enrollment with pending status
        enrollment = MFAEnrollment(
            user_id=user_id,
            method=data.method,
            status=MFAEnrollmentStatus.PENDING.value,
            totp_secret_encrypted=encrypt_field(secret.encode()),
            totp_algorithm=data.totp_algorithm,
            totp_digits=data.totp_digits,
            totp_period=data.totp_period,
            totp_issuer=data.totp_issuer,
            backup_codes_encrypted=encrypt_field(json.dumps(backup_codes).encode()),
            phone_number=data.phone_number,
            email=data.email,
            tenant_id=tenant_id,
            created_by=user_id,
            extra_metadata=data.extra_metadata,
        )
        await self.enrollment_repo.create(enrollment)

        # Generate QR code
        totp_uri = self._get_totp_uri(secret, user.email, data.totp_issuer)
        qr_code_url = self._generate_qr_code(totp_uri)

        return MFAEnrollmentSetupResponse(
            enrollment_id=enrollment.id,
            secret=secret,
            qr_code_url=f"data:image/svg+xml;base64,{qr_code_url}",
            backup_codes=backup_codes,
        )

    async def verify_enrollment(self, data: MFAEnrollmentVerifyRequest, tenant_id: UUID, ip_address: str | None = None, user_agent: str | None = None) -> MFAEnrollment:
        enrollment = await self.enrollment_repo.get_by_id(data.enrollment_id, tenant_id)
        if not enrollment:
            raise NotFoundException(detail="Enrollment not found")

        if enrollment.status != MFAEnrollmentStatus.PENDING.value:
            raise ValidationException(detail=f"Enrollment is not in pending status: {enrollment.status}")

        # Verify TOTP code
        secret = decrypt_field(enrollment.totp_secret_encrypted).decode()
        is_valid = self._verify_totp(secret, data.code, enrollment.totp_algorithm, enrollment.totp_digits, enrollment.totp_period)

        if not is_valid:
            await self._record_failed_attempt(enrollment)
            await self._log_verification(
                enrollment.id, enrollment.user_id, enrollment.method, "failed",
                tenant_id, ip_address, user_agent
            )
            raise ValidationException(detail="Invalid verification code")

        # Success
        enrollment.status = MFAEnrollmentStatus.ACTIVE.value
        enrollment.verified_at = datetime.utcnow()
        await self._record_success(enrollment)
        await self._log_verification(
            enrollment.id, enrollment.user_id, enrollment.method, "success",
            tenant_id, ip_address, user_agent
        )
        return await self.enrollment_repo.update(enrollment)

    async def get_enrollment(self, enrollment_id: UUID, tenant_id: UUID) -> MFAEnrollment:
        enrollment = await self.enrollment_repo.get_by_id(enrollment_id, tenant_id)
        if not enrollment:
            raise NotFoundException(detail="MFA enrollment not found")
        return enrollment

    async def get_user_enrollment(self, user_id: UUID, tenant_id: UUID) -> MFAEnrollment | None:
        return await self.enrollment_repo.get_by_user(user_id, tenant_id)

    async def disable_enrollment(self, data: MFAEnrollmentDisableRequest, tenant_id: UUID, disabled_by: UUID, ip_address: str | None = None, user_agent: str | None = None) -> MFAEnrollment:
        enrollment = await self.enrollment_repo.get_by_id(data.enrollment_id, tenant_id)
        if not enrollment:
            raise NotFoundException(detail="Enrollment not found")

        if enrollment.status != MFAEnrollmentStatus.ACTIVE.value:
            raise ValidationException(detail=f"Enrollment is not active: {enrollment.status}")

        # Verify code
        secret = decrypt_field(enrollment.totp_secret_encrypted).decode()
        is_valid = self._verify_totp(secret, data.code, enrollment.totp_algorithm, enrollment.totp_digits, enrollment.totp_period)

        if not is_valid:
            await self._record_failed_attempt(enrollment)
            await self._log_verification(
                enrollment.id, enrollment.user_id, enrollment.method, "failed",
                tenant_id, ip_address, user_agent
            )
            raise ValidationException(detail="Invalid verification code")

        # Success - disable
        enrollment.status = MFAEnrollmentStatus.DISABLED.value
        enrollment.disabled_at = datetime.utcnow()
        enrollment.disabled_by_id = disabled_by
        await self._record_success(enrollment)
        await self._log_verification(
            enrollment.id, enrollment.user_id, enrollment.method, "disabled",
            tenant_id, ip_address, user_agent
        )
        return await self.enrollment_repo.update(enrollment)

    async def regenerate_backup_codes(self, enrollment_id: UUID, tenant_id: UUID, user_id: UUID) -> MFARecoveryCodesResponse:
        enrollment = await self.enrollment_repo.get_by_id(enrollment_id, tenant_id)
        if not enrollment:
            raise NotFoundException(detail="Enrollment not found")

        if enrollment.user_id != user_id:
            raise ValidationException(detail="Not authorized to regenerate codes for this enrollment")

        backup_codes = self._generate_backup_codes()
        enrollment.backup_codes_encrypted = encrypt_field(json.dumps(backup_codes).encode())
        enrollment.backup_codes_used = []
        enrollment.updated_by = user_id
        await self.enrollment_repo.update(enrollment)

        return MFARecoveryCodesResponse(codes=backup_codes)

    async def verify_recovery_code(self, data: MFARecoveryCodeVerifyRequest, tenant_id: UUID, ip_address: str | None = None, user_agent: str | None = None) -> bool:
        enrollment = await self.enrollment_repo.get_by_id(data.enrollment_id, tenant_id)
        if not enrollment:
            raise NotFoundException(detail="Enrollment not found")

        if enrollment.status != MFAEnrollmentStatus.ACTIVE.value:
            raise ValidationException(detail=f"Enrollment is not active: {enrollment.status}")

        # Check backup codes
        backup_codes_json = decrypt_field(enrollment.backup_codes_encrypted).decode()
        backup_codes = json.loads(backup_codes_json)
        used_codes = set(enrollment.backup_codes_used)

        if data.code in used_codes:
            raise ValidationException(detail="Recovery code already used")

        if data.code not in backup_codes:
            await self._record_failed_attempt(enrollment)
            await self._log_verification(
                enrollment.id, enrollment.user_id, MFAMethod.BACKUP_CODES, "failed",
                tenant_id, ip_address, user_agent
            )
            raise ValidationException(detail="Invalid recovery code")

        # Mark code as used
        enrollment.backup_codes_used.append(data.code)
        enrollment.updated_by = enrollment.user_id
        await self.enrollment_repo.update(enrollment)

        await self._record_success(enrollment)
        await self._log_verification(
            enrollment.id, enrollment.user_id, MFAMethod.BACKUP_CODES, "success",
            tenant_id, ip_address, user_agent
        )
        return True

    # ============================================================================
    # Login Challenge Methods
    # ============================================================================

    async def create_login_challenge(self, user_id: UUID, tenant_id: UUID, data: MFALoginChallengeCreate, ip_address: str | None = None, user_agent: str | None = None) -> MFALoginChallengeResponse:
        # Get user's active enrollment
        enrollment = await self.enrollment_repo.get_by_user_and_method(user_id, data.method, tenant_id)
        if not enrollment or enrollment.status != MFAEnrollmentStatus.ACTIVE.value:
            raise ValidationException(detail=f"No active {data.method.value} enrollment found")

        # Clean up old pending challenges
        await self.challenge_repo.cleanup_expired(tenant_id)

        challenge_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=data.expires_in_minutes)

        if data.method == MFAMethod.TOTP:
            # Generate expected code hash for verification
            secret = decrypt_field(enrollment.totp_secret_encrypted).decode()
            totp = pyotp.TOTP(secret, algorithm=enrollment.totp_algorithm, digits=enrollment.totp_digits, interval=enrollment.totp_period)
            current_code = totp.now()
            code_hash = self._hash_code(current_code)

            challenge = MFALoginChallenge(
                user_id=user_id,
                challenge_id=challenge_id,
                method=data.method,
                status="pending",
                totp_code_hash=code_hash,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                tenant_id=tenant_id,
                created_by=user_id,
            )
        else:
            challenge = MFALoginChallenge(
                user_id=user_id,
                challenge_id=challenge_id,
                method=data.method,
                status="pending",
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                tenant_id=tenant_id,
                created_by=user_id,
            )

        await self.challenge_repo.create(challenge)

        # Generate QR code for TOTP if needed
        qr_code_url = None
        if data.method == MFAMethod.TOTP:
            secret = decrypt_field(enrollment.totp_secret_encrypted).decode()
            totp_uri = self._get_totp_uri(secret, enrollment.user.email, enrollment.totp_issuer)
            qr_code_url = f"data:image/svg+xml;base64,{self._generate_qr_code(totp_uri)}"

        return MFALoginChallengeResponse(
            challenge_id=challenge_id,
            method=data.method,
            expires_at=expires_at,
            qr_code_url=qr_code_url,
        )

    async def verify_login_challenge(self, data: MFALoginChallengeVerify, tenant_id: UUID, ip_address: str | None = None, user_agent: str | None = None) -> MFALoginChallengeResult:
        challenge = await self.challenge_repo.get_by_challenge_id(data.challenge_id, tenant_id)
        if not challenge:
            return MFALoginChallengeResult(success=False, error="Invalid or expired challenge")

        if challenge.status != "pending":
            return MFALoginChallengeResult(success=False, error="Challenge already used or cancelled")

        if challenge.expires_at < datetime.utcnow():
            challenge.status = "expired"
            await self.challenge_repo.update(challenge)
            return MFALoginChallengeResult(success=False, error="Challenge expired")

        enrollment = await self.enrollment_repo.get_by_user_and_method(challenge.user_id, challenge.method, tenant_id)
        if not enrollment or enrollment.status != MFAEnrollmentStatus.ACTIVE.value:
            return MFALoginChallengeResult(success=False, error="No active enrollment found")

        # Verify based on method
        is_valid = False
        if challenge.method == MFAMethod.TOTP:
            if challenge.totp_code_hash:
                is_valid = self._hash_code(data.code) == challenge.totp_code_hash
            else:
                secret = decrypt_field(enrollment.totp_secret_encrypted).decode()
                is_valid = self._verify_totp(secret, data.code, enrollment.totp_algorithm, enrollment.totp_digits, enrollment.totp_period)
        elif challenge.method == MFAMethod.BACKUP_CODES:
            is_valid = await self.verify_recovery_code(
                MFARecoveryCodeVerifyRequest(enrollment_id=enrollment.id, code=data.code),
                tenant_id, ip_address, user_agent
            )
        else:
            return MFALoginChallengeResult(success=False, error=f"Method {challenge.method.value} not supported for login challenge")

        if not is_valid:
            challenge.status = "failed"
            await self.challenge_repo.update(challenge)
            await self._record_failed_attempt(enrollment)
            await self._log_verification(
                enrollment.id, enrollment.user_id, challenge.method, "failed",
                tenant_id, ip_address, user_agent, challenge_id=challenge.challenge_id
            )
            return MFALoginChallengeResult(success=False, error="Invalid code")

        # Success
        challenge.status = "completed"
        challenge.completed_at = datetime.utcnow()
        await self.challenge_repo.update(challenge)

        await self._record_success(enrollment)
        await self._log_verification(
            enrollment.id, enrollment.user_id, challenge.method, "success",
            tenant_id, ip_address, user_agent, challenge_id=challenge.challenge_id
        )

        # Generate session token (in production, this would be a proper JWT)
        session_token = secrets.token_urlsafe(32)

        return MFALoginChallengeResult(success=True, session_token=session_token)

    # ============================================================================
    # Status Methods
    # ============================================================================

    async def get_user_status(self, user_id: UUID, tenant_id: UUID) -> MFAUserStatusResponse:
        enrollments_result = await self.db.execute(
            select(MFAEnrollment).where(
                MFAEnrollment.user_id == user_id,
                MFAEnrollment.tenant_id == tenant_id,
            )
        )
        enrollments = list(enrollments_result.scalars().all())

        mfa_enabled = any(e.status == MFAEnrollmentStatus.ACTIVE.value for e in enrollments)
        enrolled_methods = [e.method for e in enrollments if e.status == MFAEnrollmentStatus.ACTIVE.value]
        primary_method = enrolled_methods[0] if enrolled_methods else None

        backup_codes_remaining = 0
        for e in enrollments:
            if e.method == MFAMethod.TOTP and e.backup_codes_encrypted:
                backup_codes_json = decrypt_field(e.backup_codes_encrypted).decode()
                backup_codes = json.loads(backup_codes_json)
                used = set(e.backup_codes_used)
                backup_codes_remaining += len([c for c in backup_codes if c not in used])

        return MFAUserStatusResponse(
            user_id=user_id,
            mfa_enabled=mfa_enabled,
            enrolled_methods=enrolled_methods,
            primary_method=primary_method,
            backup_codes_remaining=backup_codes_remaining,
        )

    async def get_verification_logs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        enrollment_id: UUID | None = None,
        user_id: UUID | None = None,
        method: str | None = None,
        result: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[MFAVerificationLog], int]:
        return await self.log_repo.get_all(
            tenant_id, page, page_size, enrollment_id, user_id, method, result, date_from, date_to
        )