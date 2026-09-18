import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin
from app.core.database.encryption_mixin import PIIEncryptionMixin

if TYPE_CHECKING:
    from app.modules.users.models import User


class MFAMethod(str, PyEnum):
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"


class MFAEnrollmentStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"


class MFAEnrollment(Base, TenantBaseModelMixin, PIIEncryptionMixin):
    __tablename__ = "mfa_enrollments"
    __table_args__ = (
        Index("ix_mfa_enrollments_tenant_user", "tenant_id", "user_id", unique=True),
        Index("ix_mfa_enrollments_tenant_status", "tenant_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    method: Mapped[MFAMethod] = mapped_column(
        Enum(MFAMethod), nullable=False, index=True
    )

    status: Mapped[MFAEnrollmentStatus] = mapped_column(
        Enum(MFAEnrollmentStatus), default=MFAEnrollmentStatus.PENDING, nullable=False, index=True
    )

    totp_secret_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)

    totp_algorithm: Mapped[str] = mapped_column(String(20), default="SHA1", nullable=False)

    totp_digits: Mapped[int] = mapped_column(default=6, nullable=False)

    totp_period: Mapped[int] = mapped_column(default=30, nullable=False)

    totp_issuer: Mapped[str] = mapped_column(String(100), default="CA Nexus", nullable=False)

    backup_codes_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)

    backup_codes_used: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    disabled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lock_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)

    last_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    disabled_by: Mapped["User | None"] = relationship("User", foreign_keys=[disabled_by_id], lazy="selectin")
    verification_logs: Mapped[list["MFAVerificationLog"]] = relationship("MFAVerificationLog", back_populates="enrollment", lazy="dynamic", cascade="all, delete-orphan")


class MFAVerificationLog(Base, TenantBaseModelMixin):
    __tablename__ = "mfa_verification_logs"
    __table_args__ = (
        Index("ix_mfa_verification_logs_tenant_enrollment", "tenant_id", "enrollment_id"),
        Index("ix_mfa_verification_logs_tenant_user", "tenant_id", "user_id"),
        Index("ix_mfa_verification_logs_tenant_result", "tenant_id", "result"),
        Index("ix_mfa_verification_logs_tenant_created", "tenant_id", "created_at"),
    )

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mfa_enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    method: Mapped[MFAMethod] = mapped_column(Enum(MFAMethod), nullable=False)

    result: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    challenge_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    enrollment: Mapped["MFAEnrollment"] = relationship("MFAEnrollment", back_populates="verification_logs", lazy="selectin")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")


class MFALoginChallenge(Base, TenantBaseModelMixin):
    __tablename__ = "mfa_login_challenges"
    __table_args__ = (
        Index("ix_mfa_login_challenges_tenant_user", "tenant_id", "user_id"),
        Index("ix_mfa_login_challenges_tenant_challenge", "tenant_id", "challenge_id", unique=True),
        Index("ix_mfa_login_challenges_tenant_status", "tenant_id", "status"),
        Index("ix_mfa_login_challenges_tenant_expires", "tenant_id", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    challenge_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    method: Mapped[MFAMethod] = mapped_column(Enum(MFAMethod), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    totp_code_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", lazy="selectin")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")