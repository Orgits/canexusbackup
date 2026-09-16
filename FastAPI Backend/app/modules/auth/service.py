import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis.client import (
    AccountLockout,
    LoginAttemptTracker,
    RefreshTokenStore,
    TokenBlacklist,
    get_redis,
)
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.users.models import User

settings = get_settings()

MIN_PASSWORD_LENGTH = 12
PASSWORD_POLICY_ERROR_PREFIX = "Password does not meet policy: "


class AuthService:
    # Account security settings
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_SECONDS = 15 * 60
    LOGIN_ATTEMPT_WINDOW_SECONDS = 15 * 60

    def __init__(self, db: AsyncSession):
        self.db = db

    def validate_password_policy(self, password: str) -> tuple[bool, list[str]]:
        """Validate password against policy.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append("Password must be at least 12 characters long")

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if not re.search(r"""[!@#$%^&*()_+\-=\[\]{};:'",.<>/?`~]""", password):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors

    async def authenticate(self, email: str, password: str) -> User | None:
        redis_client = await get_redis()
        lockout = AccountLockout(redis_client)
        if await lockout.is_locked(email):
            return None

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            tracker = LoginAttemptTracker(redis_client)
            await tracker.increment(email, self.LOGIN_ATTEMPT_WINDOW_SECONDS)
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.hashed_password):
            tracker = LoginAttemptTracker(redis_client)
            attempts = await tracker.increment(email, self.LOGIN_ATTEMPT_WINDOW_SECONDS)

            if attempts >= self.MAX_LOGIN_ATTEMPTS:
                await lockout.lock(email, self.LOCKOUT_DURATION_SECONDS)

            return None

        tracker = LoginAttemptTracker(redis_client)
        await tracker.reset(email)

        return user

    async def login(self, user: User) -> dict:
        permissions = user.get_all_permissions()
        roles = user.roles
        access_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            permissions=permissions,
            roles=roles,
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
        )

        refresh_payload = decode_token(refresh_token)
        if refresh_payload:
            redis_client = await get_redis()
            refresh_store = RefreshTokenStore(redis_client)
            refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            await refresh_store.store(str(user.id), refresh_payload.jti, refresh_ttl)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def refresh(self, refresh_token: str) -> dict | None:
        payload = decode_token(refresh_token)
        if not payload or payload.type != TokenType.REFRESH:
            return None

        user_id = UUID(payload.sub)
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None

        redis_client = await get_redis()
        refresh_store = RefreshTokenStore(redis_client)

        if not await refresh_store.is_valid(str(user_id), payload.jti):
            return None

        await refresh_store.invalidate(str(user_id), payload.jti)

        permissions = user.get_all_permissions()
        roles = user.roles
        access_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            permissions=permissions,
            roles=roles,
        )
        new_refresh_token = create_refresh_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
        )

        new_refresh_payload = decode_token(new_refresh_token)
        if new_refresh_payload:
            refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            await refresh_store.store(str(user.id), new_refresh_payload.jti, refresh_ttl)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, user: User, access_token_jti: str | None = None) -> bool:
        if access_token_jti:
            redis_client = await get_redis()
            blacklist = TokenBlacklist(redis_client)
            access_ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            await blacklist.add(access_token_jti, access_ttl)

        redis_client = await get_redis()
        refresh_store = RefreshTokenStore(redis_client)
        await refresh_store.invalidate_all_for_user(str(user.id))

        return True

    async def invalidate_all_user_tokens(self, user_id: UUID) -> bool:
        """Invalidate all tokens for a user (used on password change, role change, etc.)"""
        redis_client = await get_redis()

        refresh_store = RefreshTokenStore(redis_client)
        await refresh_store.invalidate_all_for_user(str(user_id))

        return True

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> tuple[bool, list[str]]:
        """Change user password with policy validation."""
        if not verify_password(current_password, user.hashed_password):
            return False, ["Current password is incorrect"]

        is_valid, errors = self.validate_password_policy(new_password)
        if not is_valid:
            return False, errors

        if verify_password(new_password, user.hashed_password):
            return False, ["New password must be different from current password"]

        user.hashed_password = hash_password(new_password)
        await self.db.flush()

        await self.invalidate_all_user_tokens(user.id)

        return True, []

    async def reset_password(self, email: str, new_password: str) -> tuple[bool, list[str]]:
        """Reset user password (admin or password reset flow)."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return False, ["User not found"]

        is_valid, errors = self.validate_password_policy(new_password)
        if not is_valid:
            return False, errors

        user.hashed_password = hash_password(new_password)
        await self.db.flush()

        await self.invalidate_all_user_tokens(user.id)

        return True, []

    async def unlock_account(self, email: str) -> bool:
        """Manually unlock an account (admin action)."""
        redis_client = await get_redis()
        lockout = AccountLockout(redis_client)
        await lockout.unlock(email)

        tracker = LoginAttemptTracker(redis_client)
        await tracker.reset(email)

        return True

    async def is_account_locked(self, email: str) -> bool:
        """Check if account is locked."""
        redis_client = await get_redis()
        lockout = AccountLockout(redis_client)
        return await lockout.is_locked(email)

    async def get_failed_login_attempts(self, email: str) -> int:
        """Get current failed login attempts count."""
        redis_client = await get_redis()
        tracker = LoginAttemptTracker(redis_client)
        return await tracker.get(email)

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        tenant_id: UUID,
        roles: list[str] | None = None,
    ) -> User:
        is_valid, errors = self.validate_password_policy(password)
        if not is_valid:
            raise ValueError(PASSWORD_POLICY_ERROR_PREFIX + ", ".join(errors))

        hashed_password = hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            tenant_id=tenant_id,
            roles=roles or ["associate"],
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()
        return user
