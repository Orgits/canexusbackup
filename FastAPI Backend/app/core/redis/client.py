from contextlib import asynccontextmanager

import redis.asyncio as redis
from app.core.config import get_settings
from redis.asyncio import Redis

settings = get_settings()

_redis_client: Redis | None = None


async def init_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
    return _redis_client


async def get_redis() -> Redis:
    if _redis_client is None:
        await init_redis()
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


@asynccontextmanager
async def redis_context() -> Redis:
    client = await get_redis()
    try:
        yield client
    finally:
        pass


class TokenBlacklist:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.prefix = "token:blacklist:"

    async def add(self, jti: str, ttl_seconds: int) -> None:
        key = f"{self.prefix}{jti}"
        await self.redis.set(key, "1", ex=ttl_seconds)

    async def is_blacklisted(self, jti: str) -> bool:
        key = f"{self.prefix}{jti}"
        return await self.redis.exists(key) > 0

    async def remove(self, jti: str) -> None:
        key = f"{self.prefix}{jti}"
        await self.redis.delete(key)


class RefreshTokenStore:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.prefix = "token:refresh:"

    async def store(self, user_id: str, jti: str, ttl_seconds: int) -> None:
        key = f"{self.prefix}{user_id}:{jti}"
        await self.redis.set(key, "1", ex=ttl_seconds)

    async def is_valid(self, user_id: str, jti: str) -> bool:
        key = f"{self.prefix}{user_id}:{jti}"
        return await self.redis.exists(key) > 0

    async def invalidate(self, user_id: str, jti: str) -> None:
        key = f"{self.prefix}{user_id}:{jti}"
        await self.redis.delete(key)

    async def invalidate_all_for_user(self, user_id: str) -> None:
        pattern = f"{self.prefix}{user_id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break


class LoginAttemptTracker:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.prefix = "auth:login_attempts:"

    async def increment(self, identifier: str, window_seconds: int) -> int:
        key = f"{self.prefix}{identifier}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, window_seconds)
        return count

    async def get(self, identifier: str) -> int:
        key = f"{self.prefix}{identifier}"
        val = await self.redis.get(key)
        return int(val) if val else 0

    async def reset(self, identifier: str) -> None:
        key = f"{self.prefix}{identifier}"
        await self.redis.delete(key)

    async def is_locked(self, identifier: str, max_attempts: int) -> bool:
        return await self.get(identifier) >= max_attempts


class AccountLockout:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.prefix = "auth:lockout:"

    async def lock(self, identifier: str, ttl_seconds: int) -> None:
        key = f"{self.prefix}{identifier}"
        await self.redis.set(key, "1", ex=ttl_seconds)

    async def is_locked(self, identifier: str) -> bool:
        key = f"{self.prefix}{identifier}"
        return await self.redis.exists(key) > 0

    async def unlock(self, identifier: str) -> None:
        key = f"{self.prefix}{identifier}"
        await self.redis.delete(key)
