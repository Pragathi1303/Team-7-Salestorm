import redis.asyncio as aioredis
import redis as sync_redis
from app.core.config import get_settings

settings = get_settings()

# Async Redis client for API handlers
_async_redis: aioredis.Redis | None = None

# Sync Redis client for workers
_sync_redis: sync_redis.Redis | None = None


def get_async_redis() -> aioredis.Redis:
    global _async_redis
    if _async_redis is None:
        _async_redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=100,
        )
    return _async_redis


def get_sync_redis() -> sync_redis.Redis:
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = sync_redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _sync_redis


async def close_redis():
    global _async_redis
    if _async_redis:
        await _async_redis.aclose()
        _async_redis = None
