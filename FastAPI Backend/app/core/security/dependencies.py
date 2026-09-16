from typing import TYPE_CHECKING, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_db
from app.core.redis.client import TokenBlacklist, get_redis
from app.core.security.jwt import TokenPayload, TokenType, decode_token

if TYPE_CHECKING:
    from app.modules.users.models import User

settings = get_settings()

security = HTTPBearer(auto_error=False)


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenPayload:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.type != TokenType.ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    redis_client = await get_redis()
    blacklist = TokenBlacklist(redis_client)
    if await blacklist.is_blacklisted(payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user(
    payload: TokenPayload = Depends(get_token_payload),
    db: AsyncSession = Depends(get_async_db),
) -> "User":
    from app.modules.users.models import User
    user_id = UUID(payload.sub)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def get_current_active_user(
    current_user: "User" = Depends(get_current_user),
) -> "User":
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_async_db),
) -> Optional["User"]:
    from app.modules.users.models import User
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or payload.type != TokenType.ACCESS:
        return None

    redis_client = await get_redis()
    blacklist = TokenBlacklist(redis_client)
    if await blacklist.is_blacklisted(payload.jti):
        return None

    try:
        user_id = UUID(payload.sub)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user
