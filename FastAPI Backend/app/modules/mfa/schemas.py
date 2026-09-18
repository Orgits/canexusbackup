from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MFAMethod(str, Enum):
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"


class MFAEnrollmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"


class MFAEnrollmentBase(BaseModel):
    method: MFAMethod
    totp_algorithm: str = Field(default="SHA1", max_length=20)
    totp_digits: int = Field(default=6, ge=6, le=8)
    totp_period: int = Field(default=30, ge=15, le=120)
    totp_issuer: str = Field(default="CA Nexus", max_length=100)
    phone_number: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=320)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class MFAEnrollmentCreate(MFAEnrollmentBase):
    pass


class MFAEnrollmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    method: MFAMethod
    status: str
    totp_algorithm: str
    totp_digits: int
    totp_period: int
    totp_issuer: str
    phone_number: str | None
    email: str | None
    verified_at: datetime | None
    disabled_at: datetime | None
    disabled_by_id: UUID | None
    locked_at: datetime | None
    lock_reason: str | None
    last_used_at: datetime | None
    failed_attempts: int
    last_failed_at: datetime | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class MFAEnrollmentDetailResponse(MFAEnrollmentResponse):
    user: Any | None = None
    disabled_by: Any | None = None
    verification_logs_count: int = 0


class MFAEnrollmentSetupResponse(BaseModel):
    enrollment_id: UUID
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class MFAEnrollmentVerifyRequest(BaseModel):
    enrollment_id: UUID
    code: str = Field(..., min_length=6, max_length=8)


class MFAEnrollmentDisableRequest(BaseModel):
    enrollment_id: UUID
    code: str = Field(..., min_length=6, max_length=8)
    reason: str | None = None


class MFAVerificationLogResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    user_id: UUID
    method: MFAMethod
    result: str
    ip_address: str | None
    user_agent: str | None
    challenge_id: str | None
    metadata: dict[str, Any]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


class MFAVerificationLogListResponse(BaseModel):
    items: list[MFAVerificationLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MFALoginChallengeCreate(BaseModel):
    user_id: UUID
    method: MFAMethod
    expires_in_minutes: int = Field(default=5, ge=1, le=30)


class MFALoginChallengeResponse(BaseModel):
    challenge_id: str
    method: MFAMethod
    expires_at: datetime
    qr_code_url: str | None = None


class MFALoginChallengeVerify(BaseModel):
    challenge_id: str
    code: str = Field(..., min_length=4, max_length=8)


class MFALoginChallengeResult(BaseModel):
    success: bool
    session_token: str | None = None
    error: str | None = None


class MFARecoveryCodesResponse(BaseModel):
    codes: list[str]


class MFARecoveryCodeVerifyRequest(BaseModel):
    enrollment_id: UUID
    code: str = Field(..., min_length=8, max_length=16)


class MFAUserStatusResponse(BaseModel):
    user_id: UUID
    mfa_enabled: bool
    enrolled_methods: list[MFAMethod]
    primary_method: MFAMethod | None
    backup_codes_remaining: int