"""Tests for rate limiter."""

import asyncio
import time
import pytest

import fakeredis.aioredis

from app.core.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_normal_flow():
    fake_redis = fakeredis.aioredis.FakeRedis()
    limiter = RateLimiter(max_requests=3, window_seconds=10, client_provider=lambda: fake_redis)
    client_id = "test_client"

    # First 3 requests should be allowed
    for _ in range(3):
        assert await limiter.is_allowed(client_id) is True

    # 4th should be denied
    assert await limiter.is_allowed(client_id) is False

    # Check retry_after
    retry_after = await limiter.get_retry_after(client_id)
    assert retry_after is not None
    assert 0 < retry_after <= 10


@pytest.mark.asyncio
async def test_rate_limiter_window_expiry():
    fake_redis = fakeredis.aioredis.FakeRedis()
    limiter = RateLimiter(max_requests=2, window_seconds=1, client_provider=lambda: fake_redis)
    client_id = "test_client"

    # Allow 2 requests
    assert await limiter.is_allowed(client_id) is True
    assert await limiter.is_allowed(client_id) is True

    # Third should be denied
    assert await limiter.is_allowed(client_id) is False

    # Wait for window to expire
    await asyncio.sleep(1.1)

    # Now should be allowed again
    assert await limiter.is_allowed(client_id) is True


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_requests():
    fake_redis = fakeredis.aioredis.FakeRedis()
    limiter = RateLimiter(max_requests=10, window_seconds=5, client_provider=lambda: fake_redis)
    client_id = "test_client"
    results = []

    async def make_requests():
        for _ in range(5):
            results.append(await limiter.is_allowed(client_id))
            await asyncio.sleep(0.01)  # Small delay to simulate

    # Run 2 concurrent tasks
    await asyncio.gather(make_requests(), make_requests())

    # Should have 10 True
    assert results.count(True) == 10
    assert results.count(False) == 0


@pytest.mark.asyncio
async def test_rate_limiter_get_request_count():
    fake_redis = fakeredis.aioredis.FakeRedis()
    limiter = RateLimiter(max_requests=5, window_seconds=10, client_provider=lambda: fake_redis)
    client_id = "test_client"

    # No requests yet
    assert await limiter.get_request_count(client_id) == 0

    # Add some requests
    for _ in range(3):
        await limiter.is_allowed(client_id)

    assert await limiter.get_request_count(client_id) == 3
