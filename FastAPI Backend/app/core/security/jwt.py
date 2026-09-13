from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from jose import jwt
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    type: TokenType
    exp: int
    iat: int
    permissions: list[str] = []
    roles: list[str] = []


def create_token(
    subject: str,
    tenant_id: str,
    token_type: TokenType,
    expires_delta: timedelta,
    permissions: list[str] = None,
    roles: list[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    to_encode = {
        "sub": subject,
        "tenant_id": tenant_id,
        "type": token_type.value,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "permissions": permissions or [],
        "roles": roles or [],
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_access_token(
    subject: str,
    tenant_id: str,
    permissions: list[str] = None,
    roles: list[str] = None,
) -> str:
    return create_token(
        subject=subject,
        tenant_id=tenant_id,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        permissions=permissions,
        roles=roles,
    )


def create_refresh_token(
    subject: str,
    tenant_id: str,
) -> str:
    return create_token(
        subject=subject,
        tenant_id=tenant_id,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return TokenPayload(**payload)
    except Exception:
        return None