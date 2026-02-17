import redis
from redis.asyncio import Redis
from typing import Optional
import os

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """
    Get Redis client instance (singleton pattern)

    Connection details:
    - Host: localhost (default)
    - Port: 6379 (default)
    - DB: 0 (default)
    - Decode responses: True (get strings instead of bytes)
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = await Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            encoding="utf-8",
            decode_responses=True
        )

    return _redis_client


async def close_redis():
    """Close Redis connection (called on app shutdown)"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
