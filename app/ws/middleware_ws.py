"""WebSocket middleware: authentication, rate limiting, validation, and performance tracking."""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Set, Type

import jwt
from fastapi import WebSocket
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.ws.constants_ws import (
    CloseCodes,
    DEFAULT_RATE_LIMIT,
    ErrorCodes,
    Events,
    RATE_LIMIT_WINDOW,
)
from app.ws.events_ws import ErrorResponse, EventPayload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.ws.middleware")


class WebSocketAuthError(Exception):
    """Exception raised when WebSocket authentication fails."""

    def __init__(self, message: str, code: CloseCodes = CloseCodes.UNAUTHORIZED):
        self.message = message
        self.code = code
        super().__init__(message)


class WebSocketRateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        self.code = CloseCodes.RATE_LIMITED
        super().__init__("Rate limit exceeded")


class WebSocketValidationError(Exception):
    """Exception raised when message validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details
        self.code = CloseCodes.INVALID_MESSAGE
        super().__init__(message)


# =============================================================================
# Authentication Middleware
# =============================================================================


async def websocket_auth_middleware(
    websocket: WebSocket,
    session: "AsyncSession",
) -> Dict[str, Any]:
    """
    JWT authentication for WebSocket connections.

    Extracts and validates JWT token from:
    1. Query parameter: ?token=xxx
    2. Header: Authorization: Bearer xxx
    3. First message after connect (if configured)

    Args:
        websocket: The WebSocket connection.
        session: Database session for user lookup.

    Returns:
        Dict with user info: id, email, role, status.

    Raises:
        WebSocketAuthError: If authentication fails.
    """
    token = None

    # Try query parameters first
    token = websocket.query_params.get("token")

    # Try headers if not in query params
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    # Try sec-websocket-protocol header (some clients use this)
    if not token:
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        for protocol in protocols.split(","):
            protocol = protocol.strip()
            if protocol.startswith("token."):
                token = protocol[6:]
                break

    if not token:
        raise WebSocketAuthError(
            "Missing authentication token", CloseCodes.UNAUTHORIZED
        )

    # Validate JWT
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise WebSocketAuthError("Token expired", CloseCodes.UNAUTHORIZED)
    except jwt.InvalidTokenError as e:
        raise WebSocketAuthError(f"Invalid token: {e}", CloseCodes.UNAUTHORIZED)

    # Extract user ID
    user_id = payload.get("sub")
    if not user_id:
        raise WebSocketAuthError("Invalid token subject", CloseCodes.UNAUTHORIZED)

    # Load user from database
    from app.repositories.user_repository import UserRepository

    repository = UserRepository(session)
    user = await repository.get_by_id(str(user_id))

    if not user:
        raise WebSocketAuthError("User not found", CloseCodes.UNAUTHORIZED)

    logger.info(f"WebSocket auth for user {user_id}: is_active={user.is_active}, email={user.email}")

    if not user.is_active:
        raise WebSocketAuthError("Account is not active", CloseCodes.FORBIDDEN)

    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "status": "online",  # Default status on connect
        "full_name": user.full_name,
    }


# =============================================================================
# Rate Limiting Middleware
# =============================================================================


class WebSocketRateLimiter:
    """
    Rate limiter for WebSocket events using Redis sliding window.

    Tracks events per user (not per connection) to prevent abuse
    across multiple simultaneous connections.
    """

    def __init__(
        self,
        redis: Optional[Redis] = None,
        max_events: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = RATE_LIMIT_WINDOW,
    ):
        self._redis = redis
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._local_cache: Dict[str, Set[float]] = {}
        self._lock = asyncio.Lock()

    async def _get_redis(self) -> Optional[Redis]:
        """Get Redis client lazily."""
        if self._redis is None:
            try:
                from app.cache import get_redis

                self._redis = await get_redis()
            except Exception:
                logger.warning("Redis not available for rate limiting")
        return self._redis

    async def is_allowed(self, user_id: str) -> bool:
        """
        Check if user is allowed to send an event.

        Args:
            user_id: The user ID to check.

        Returns:
            True if allowed, False if rate limited.
        """
        redis = await self._get_redis()
        key = f"ws_rate:{user_id}"
        now = time.time()
        cutoff = now - self.window_seconds

        if redis:
            try:
                # Use Redis sorted set for sliding window
                await redis.zremrangebyscore(key, "-inf", cutoff)
                count = await redis.zcard(key)
                if count < self.max_events:
                    await redis.zadd(key, {str(now): now})
                    await redis.expire(key, self.window_seconds * 2)
                    return True
                return False
            except Exception as e:
                logger.warning(f"Redis rate limit check failed: {e}")
                # Fall back to local on memory

        # Local fallback
        async with self._lock:
            if user_id not in self._local_cache:
                self._local_cache[user_id] = set()

            # Clean old entries
            self._local_cache[user_id] = {
                t for t in self._local_cache[user_id] if t > cutoff
            }

            if len(self._local_cache[user_id]) < self.max_events:
                self._local_cache[user_id].add(now)
                return True
            return False

    async def get_retry_after(self, user_id: str) -> Optional[float]:
        """
        Get seconds until user can send another event.

        Args:
            user_id: The user ID to check.

        Returns:
            Seconds to wait, or None if allowed.
        """
        redis = await self._get_redis()
        key = f"ws_rate:{user_id}"
        now = time.time()
        cutoff = now - self.window_seconds

        if redis:
            try:
                await redis.zremrangebyscore(key, "-inf", cutoff)
                count = await redis.zcard(key)
                if count < self.max_events:
                    return None
                # Get oldest entry
                oldest = await redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    return (oldest_time + self.window_seconds) - now
                return None
            except Exception:
                pass

        return None

    async def get_event_count(self, user_id: str) -> int:
        """Get current event count in window for user."""
        redis = await self._get_redis()
        key = f"ws_rate:{user_id}"
        now = time.time()
        cutoff = now - self.window_seconds

        if redis:
            try:
                await redis.zremrangebyscore(key, "-inf", cutoff)
                return await redis.zcard(key)
            except Exception:
                pass

        async with self._lock:
            if user_id not in self._local_cache:
                return 0
            self._local_cache[user_id] = {
                t for t in self._local_cache[user_id] if t > cutoff
            }
            return len(self._local_cache[user_id])

    async def reset(self, user_id: str) -> None:
        """Reset rate limit for a user."""
        redis = await self._get_redis()
        key = f"ws_rate:{user_id}"

        if redis:
            try:
                await redis.delete(key)
            except Exception:
                pass

        async with self._lock:
            self._local_cache.pop(user_id, None)


# =============================================================================
# Input Validation Middleware
# =============================================================================


class InputValidator:
    """
    Validates incoming WebSocket messages against Pydantic schemas.

    Maps event names to their corresponding request models and
    validates incoming data before passing to handlers.
    """

    # Event to request model mapping
    EVENT_MODELS: Dict[str, Type[BaseModel]] = {}

    @classmethod
    def register_model(cls, event: str, model: Type[BaseModel]) -> None:
        """Register a model for an event type."""
        cls.EVENT_MODELS[event] = model

    @classmethod
    def validate(cls, event: str, data: Dict[str, Any]) -> BaseModel:
        """
        Validate event data against registered model.

        Args:
            event: The event name.
            data: The event data to validate.

        Returns:
            Validated model instance.

        Raises:
            WebSocketValidationError: If validation fails.
        """
        # Import models here to avoid circular imports
        from app.ws.events_ws import (
            MessageSendRequest,
            NotificationMarkAllReadRequest,
            NotificationMarkReadRequest,
            PingRequest,
            SubscribeRequest,
            TypingRequest,
            UnsubscribeRequest,
            UserDeleteRequest,
            UserGetRequest,
            UserStatusRequest,
            UserUpdateRequest,
        )

        # Build model map on first use
        if not cls.EVENT_MODELS:
            cls.EVENT_MODELS = {
                Events.SUBSCRIBE: SubscribeRequest,
                Events.UNSUBSCRIBE: UnsubscribeRequest,
                Events.USER_GET: UserGetRequest,
                Events.USER_UPDATE: UserUpdateRequest,
                Events.USER_STATUS: UserStatusRequest,
                Events.USER_DELETE: UserDeleteRequest,
                Events.MESSAGE_SEND: MessageSendRequest,
                Events.TYPING_START: TypingRequest,
                Events.TYPING_STOP: TypingRequest,
                Events.NOTIFICATION_MARK_READ: NotificationMarkReadRequest,
                Events.NOTIFICATION_MARK_ALL_READ: NotificationMarkAllReadRequest,
                Events.PING: PingRequest,
            }

        model_class = cls.EVENT_MODELS.get(event)

        if model_class is None:
            # No validation model registered - allow raw data
            return data

        try:
            return model_class(**data)
        except ValidationError as e:
            errors = e.errors()
            details = {
                "errors": [
                    {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                    for err in errors
                ]
            }
            raise WebSocketValidationError("Validation failed", details)

    @classmethod
    def parse_event(cls, message: str) -> tuple[str, Dict[str, Any]]:
        """
        Parse raw WebSocket message into event name and data.

        Args:
            message: Raw JSON message string.

        Returns:
            Tuple of (event_name, data_dict).

        Raises:
            WebSocketValidationError: If parsing fails.
        """
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError as e:
            raise WebSocketValidationError(
                "Invalid JSON format", {"error": str(e)}
            )

        try:
            payload = EventPayload(**parsed)
        except ValidationError as e:
            raise WebSocketValidationError(
                "Invalid event format",
                {"errors": e.errors()}
            )

        return payload.event, payload.data


# =============================================================================
# Performance Tracking Middleware
# =============================================================================


class PerformanceTracker:
    """
    Tracks event processing duration and records to Prometheus.

    Usage:
        async with PerformanceTracker(event_name, metrics) as tracker:
            await handler(...)
            # Duration automatically recorded on exit
    """

    def __init__(
        self,
        event_name: str,
        endpoint: str = "/ws",
        metrics: Optional[Any] = None,
    ):
        self.event_name = event_name
        self.endpoint = endpoint
        self.metrics = metrics
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None

    async def __aenter__(self) -> "PerformanceTracker":
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time is not None:
            self.duration = time.perf_counter() - self.start_time

            # Record to Prometheus if available
            if self.metrics:
                try:
                    self.metrics.record_event_duration(
                        self.event_name, self.endpoint, self.duration
                    )
                except Exception as e:
                    logger.warning(f"Failed to record metrics: {e}")

            logger.debug(
                f"Event {self.event_name} processed in {self.duration:.4f}s"
            )


# =============================================================================
# Combined Middleware Pipeline
# =============================================================================


class WebSocketMiddleware:
    """
    Combined middleware for WebSocket connections.

    Orchestrates authentication, rate limiting, and validation
    in a consistent order.
    """

    def __init__(
        self,
        rate_limiter: Optional[WebSocketRateLimiter] = None,
        metrics: Optional[Any] = None,
    ):
        self.rate_limiter = rate_limiter or WebSocketRateLimiter()
        self.metrics = metrics
        self.validator = InputValidator()

    async def authenticate(
        self,
        websocket: WebSocket,
        session: "AsyncSession",
    ) -> Dict[str, Any]:
        """Authenticate WebSocket connection."""
        return await websocket_auth_middleware(websocket, session)

    async def check_rate_limit(self, user_id: str) -> None:
        """
        Check rate limit for user.

        Raises:
            WebSocketRateLimitError: If rate limit exceeded.
        """
        allowed = await self.rate_limiter.is_allowed(user_id)
        if not allowed:
            retry_after = await self.rate_limiter.get_retry_after(user_id)
            raise WebSocketRateLimitError(retry_after or 60.0)

    def validate_event(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> BaseModel:
        """Validate event data."""
        return self.validator.validate(event, data)

    def parse_message(self, message: str) -> tuple[str, Dict[str, Any]]:
        """Parse raw message into event and data."""
        return self.validator.parse_event(message)

    @asynccontextmanager
    async def track_performance(self, event_name: str):
        """Context manager for performance tracking."""
        async with PerformanceTracker(event_name, metrics=self.metrics) as tracker:
            yield tracker

    async def send_error(
        self,
        websocket: WebSocket,
        code: ErrorCodes,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Send error event to client."""
        error = ErrorResponse(
            code=code,
            message=message,
            details=details,
            correlation_id=correlation_id,
        )
        await websocket.send_json({
            "event": Events.ERROR,
            "data": error.model_dump(exclude_none=True),
        })


# =============================================================================
# Helper Functions
# =============================================================================


def create_error_response(
    code: ErrorCodes,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "event": Events.ERROR,
        "data": {
            "code": code.value,
            "message": message,
            "details": details,
            "correlation_id": correlation_id,
        },
    }
