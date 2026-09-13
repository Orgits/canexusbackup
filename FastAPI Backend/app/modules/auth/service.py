from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, TokenType
from app.core.config import get_settings
from app.modules.users.models import User

settings = get_settings()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
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
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def refresh(self, refresh_token: str) -> Optional[dict]:
        payload = decode_token(refresh_token)
        if not payload or payload.type != TokenType.REFRESH:
            return None

        user_id = UUID(payload.sub)
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None

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
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, user: User) -> bool:
        return True

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        tenant_id: UUID,
        roles: list[str] = None,
    ) -> User:
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