"""Sliding window rate limiter implementation."""

from collections import deque
import time
from threading import Lock
from typing import Optional

from app.cache import get_redis
from redis.asyncio import Redis


class RateLimiter:
    """Sliding window rate limiter using Redis for storage.

    Maintains a rolling window of request timestamps per client.
    """

    def __init__(self, max_requests: int, window_seconds: int, client_provider=get_redis):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._get_client = client_provider

    async def _clean_old_requests(self, redis: Redis, key: str, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window_seconds
        await redis.zremrangebyscore(key, '-inf', cutoff)

    async def is_allowed(self, client_id: str) -> bool:
        """Check if the client is allowed to make a request.

        Cleans expired timestamps and adds current timestamp if allowed.
        """
        redis = await self._get_client()
        key = f"rate_limit:{client_id}"
        now = time.time()
        await self._clean_old_requests(redis, key, now)
        count = await redis.zcard(key)
        if count < self.max_requests:
            await redis.zadd(key, {str(now): 1})
            await redis.expire(key, int(self.window_seconds * 2))
            return True
        return False

    async def get_retry_after(self, client_id: str) -> Optional[float]:
        """Get seconds until the client can make another request.

        Returns None if allowed, otherwise seconds to wait.
        """
        redis = await self._get_client()
        key = f"rate_limit:{client_id}"
        now = time.time()
        await self._clean_old_requests(redis, key, now)
        count = await redis.zcard(key)
        if count < self.max_requests:
            return None
        # Get the oldest timestamp
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_time = oldest[0][1]
            return (oldest_time + self.window_seconds) - now
        return None

    async def get_request_count(self, client_id: str) -> int:
        """Get current request count in window for client."""
        redis = await self._get_client()
        key = f"rate_limit:{client_id}"
        now = time.time()
        await self._clean_old_requests(redis, key, now)
        return await redis.zcard(key)
