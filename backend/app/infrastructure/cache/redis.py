"""Redis client management.

Provides a process-wide async Redis client and a FastAPI dependency for
request-scoped access. Redis serves two roles in CareerOS (per
`docs/adr/0004-redis-celery.md`): the Celery broker/result backend (wired
up starting Milestone 8) and short-lived caching (used starting Milestone
3+). This module provides the shared client either role builds on.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings


@lru_cache
def get_redis_pool() -> redis.ConnectionPool:
    """Return the process-wide Redis connection pool.

    Cached so all callers share one pool rather than opening a new
    connection per request.
    """
    settings = get_settings()
    return redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)


async def get_redis_client() -> AsyncGenerator[redis.Redis]:
    """FastAPI dependency yielding a Redis client bound to the shared pool."""
    client = redis.Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        await client.aclose()


async def dispose_redis_pool() -> None:
    """Disconnect the shared Redis connection pool.

    Called during application shutdown (see `app.main`'s lifespan handler).
    """
    await get_redis_pool().disconnect()
