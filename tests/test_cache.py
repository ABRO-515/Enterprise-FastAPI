import asyncio

import fakeredis.aioredis
import pytest

from app.cache import Cache


@pytest.mark.asyncio
async def test_cache_set_get_delete():
    redis_client = fakeredis.aioredis.FakeRedis()
    cache = Cache(lambda: asyncio.sleep(0) or redis_client)

    await cache.set("foo", {"bar": 1}, ttl=5)
    value = await cache.get("foo")
    assert value == {"bar": 1}

    await cache.delete("foo")
    assert await cache.get("foo") is None
