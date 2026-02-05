"""Redis cache helper.

Usage:
    from app.cache import cache, get_redis

    await cache.set("key", "value", ttl=60)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = logging.getLogger("app.cache")

_redis: Optional[Redis] = None
_lock = asyncio.Lock()


async def get_redis() -> Redis:
    """Return a lazily-initialised singleton Redis client (cluster or single)."""
    global _redis
    if _redis:
        return _redis

    async with _lock:
        if _redis:
            return _redis

        if settings.redis_cluster_nodes:
            # Cluster mode
            nodes = [node.strip() for node in settings.redis_cluster_nodes.split(",") if node.strip()]
            _redis = Redis.from_cluster(nodes=nodes, password=settings.redis_password, decode_responses=True)
        else:
            _redis = from_url(settings.redis_url, password=settings.redis_password, decode_responses=True)
        return _redis


class Cache:
    def __init__(self, client_provider=get_redis):
        self._get_client = client_provider

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        client = await self._get_client()
        payload = json.dumps(value, default=str)
        await client.set(key, payload, ex=ttl)

    async def get(self, key: str) -> Any | None:
        client = await self._get_client()
        data = await client.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        await client.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        client = await self._get_client()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)

    async def flush(self) -> None:
        client = await self._get_client()
        await client.flushdb()


cache = Cache()
