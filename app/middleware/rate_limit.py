"""Rate limiting middleware for FastAPI."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware

from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce sliding window rate limiting."""

    def __init__(self, app, rate_limiter: RateLimiter, exempt_routes: list[str]):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.exempt_routes = exempt_routes

    async def dispatch(self, request, call_next):
        if request.url.path in self.exempt_routes:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        if not await self.rate_limiter.is_allowed(client_ip):
            retry_after = await self.rate_limiter.get_retry_after(client_ip)
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "retry_after": retry_after,
                },
            )
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(int(retry_after or 0))},
            )

        response = await call_next(request)
        return response
