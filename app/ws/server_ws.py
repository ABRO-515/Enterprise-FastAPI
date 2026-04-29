"""WebSocket server: ConnectionManager, routes, and lifecycle management.

This module provides:
- ConnectionManager: Tracks active WebSocket connections
- WebSocket routes for different endpoints
- Redis pub/sub integration for cross-instance communication
- Prometheus metrics integration
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from prometheus_client import Counter, Gauge, Histogram
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.core.config import settings
from app.db.session import get_db_session
from app.ws.constants_ws import (
    CloseCodes,
    ErrorCodes,
    Events,
    REDIS_BROADCAST_CHANNEL,
    REDIS_USER_CHANNEL_PREFIX,
    WS_CONNECTION_TIMEOUT,
    WS_HEARTBEAT_INTERVAL,
    WS_MAX_MESSAGE_SIZE,
)
from app.ws.events_ws import RedisBroadcastMessage, RedisUserMessage
from app.ws.handlers_ws import WebSocketHandlers
from app.ws.middleware_ws import (
    WebSocketAuthError,
    WebSocketMiddleware,
    WebSocketRateLimitError,
    WebSocketValidationError,
)
from app.ws.rooms_ws import RoomManager

logger = logging.getLogger("app.ws.server")

# =============================================================================
# Prometheus Metrics
# =============================================================================

websocket_connections = Gauge(
    "websocket_active_connections",
    "Active WebSocket connections",
    ["endpoint"],
)

websocket_events_total = Counter(
    "websocket_events_total",
    "Total WebSocket events processed",
    ["event", "endpoint"],
)

websocket_event_duration = Histogram(
    "websocket_event_duration_seconds",
    "WebSocket event processing duration",
    ["event", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5],
)

websocket_errors = Counter(
    "websocket_errors_total",
    "WebSocket errors",
    ["type", "endpoint"],
)


# =============================================================================
# Connection Info Dataclass
# =============================================================================


@dataclass
class ConnectionInfo:
    """Information about an active WebSocket connection."""

    connection_id: str
    user_id: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=lambda: datetime.utcnow())
    last_activity: datetime = field(default_factory=lambda: datetime.utcnow())
    endpoint: str = "/ws"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()


# =============================================================================
# Connection Manager
# =============================================================================


class ConnectionManager:
    """
    Manages active WebSocket connections with thread-safe operations.

    Features:
    - Track connections by user_id and connection_id
    - Support multiple connections per user (multiple devices/tabs)
    - Thread-safe operations using asyncio locks
    - Redis pub/sub for cross-instance communication
    - Prometheus metrics integration

    Usage:
        manager = ConnectionManager(redis_client)
        await manager.connect(websocket, user_info)
        await manager.broadcast_to_room("user:123", "event", data)
    """

    def __init__(
        self,
        redis: Optional[Redis] = None,
        metrics_enabled: bool = True,
    ):
        self._redis = redis
        self._metrics_enabled = metrics_enabled

        # Connection tracking
        self._connections: Dict[str, ConnectionInfo] = {}
        self._user_connections: Dict[str, Set[str]] = {}

        # Room manager
        self.rooms = RoomManager(redis)

        # Locks for thread safety
        self._lock = asyncio.Lock()

        # Redis subscriber task
        self._subscriber_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def _get_redis(self) -> Optional[Redis]:
        """Get Redis client lazily."""
        if self._redis is None:
            try:
                self._redis = await get_redis()
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
        return self._redis

    # -------------------------------------------------------------------------
    # Connection Lifecycle
    # -------------------------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        endpoint: str = "/ws",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            user: Authenticated user dict with id, email, role.
            endpoint: The WebSocket endpoint path.
            metadata: Optional metadata for the connection.

        Returns:
            Unique connection ID.
        """
        connection_id = f"conn_{datetime.utcnow().timestamp()}_{id(websocket)}"
        user_id = user["id"]

        async with self._lock:
            # Create connection info
            conn_info = ConnectionInfo(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                endpoint=endpoint,
                metadata=metadata or {},
            )

            # Track connection
            self._connections[connection_id] = conn_info

            # Track user -> connections mapping
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

            # Update metrics
            if self._metrics_enabled:
                websocket_connections.labels(endpoint=endpoint).inc()

        logger.debug(f"Connection {connection_id} registered for user {user_id}")
        return connection_id

    async def disconnect(self, connection_id: str) -> Optional[ConnectionInfo]:
        """
        Unregister a WebSocket connection.

        Args:
            connection_id: The connection ID to remove.

        Returns:
            The removed ConnectionInfo, or None if not found.
        """
        async with self._lock:
            conn_info = self._connections.pop(connection_id, None)

            if conn_info:
                user_id = conn_info.user_id

                # Remove from user connections
                if user_id in self._user_connections:
                    self._user_connections[user_id].discard(connection_id)
                    if not self._user_connections[user_id]:
                        del self._user_connections[user_id]

                # Update metrics
                if self._metrics_enabled:
                    websocket_connections.labels(
                        endpoint=conn_info.endpoint
                    ).dec()

                logger.debug(f"Connection {connection_id} unregistered")

            return conn_info

    # -------------------------------------------------------------------------
    # Connection Queries
    # -------------------------------------------------------------------------

    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection info by ID."""
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> Set[str]:
        """Get all connection IDs for a user."""
        return self._user_connections.get(user_id, set()).copy()

    def get_all_connections(self) -> Dict[str, ConnectionInfo]:
        """Get all active connections."""
        return self._connections.copy()

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self._connections)

    def get_user_count(self) -> int:
        """Get number of unique users with active connections."""
        return len(self._user_connections)

    def get_connections_by_endpoint(self, endpoint: str) -> List[ConnectionInfo]:
        """Get all connections for a specific endpoint."""
        return [
            conn
            for conn in self._connections.values()
            if conn.endpoint == endpoint
        ]

    # -------------------------------------------------------------------------
    # Broadcasting
    # -------------------------------------------------------------------------

    async def send_to_connection(
        self,
        connection_id: str,
        event: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Send an event to a specific connection.

        Args:
            connection_id: Target connection ID.
            event: Event name.
            data: Event data.

        Returns:
            True if sent successfully, False if connection not found.
        """
        conn_info = self._connections.get(connection_id)
        if not conn_info:
            return False

        try:
            await conn_info.websocket.send_json({
                "event": event,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            })
            conn_info.touch()
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {connection_id}: {e}")
            return False

    async def broadcast_to_user(
        self,
        user_id: str,
        event: str,
        data: Dict[str, Any],
        exclude_connection: Optional[str] = None,
    ) -> int:
        """
        Broadcast an event to all connections of a user.

        Args:
            user_id: Target user ID.
            event: Event name.
            data: Event data.
            exclude_connection: Optional connection ID to exclude.

        Returns:
            Number of connections the event was sent to.
        """
        sent_count = 0
        connection_ids = self.get_user_connections(user_id)

        for conn_id in connection_ids:
            if conn_id == exclude_connection:
                continue
            if await self.send_to_connection(conn_id, event, data):
                sent_count += 1

        return sent_count

    async def broadcast_to_room(
        self,
        room_name: str,
        event: str,
        data: Dict[str, Any],
        exclude_connection: Optional[str] = None,
    ) -> int:
        """
        Broadcast an event to all connections in a room.

        Args:
            room_name: Target room name.
            event: Event name.
            data: Event data.
            exclude_connection: Optional connection ID to exclude.

        Returns:
            Number of connections the event was sent to.
        """
        sent_count = 0
        connection_ids = self.rooms.get_room_members(room_name)

        for conn_id in connection_ids:
            if conn_id == exclude_connection:
                continue
            if await self.send_to_connection(conn_id, event, data):
                sent_count += 1

        return sent_count

    async def broadcast_all(
        self,
        event: str,
        data: Dict[str, Any],
        exclude_connection: Optional[str] = None,
    ) -> int:
        """
        Broadcast an event to all active connections.

        Args:
            event: Event name.
            data: Event data.
            exclude_connection: Optional connection ID to exclude.

        Returns:
            Number of connections the event was sent to.
        """
        sent_count = 0

        for conn_id, conn_info in list(self._connections.items()):
            if conn_id == exclude_connection:
                continue
            try:
                await conn_info.websocket.send_json({
                    "event": event,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                conn_info.touch()
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast to {conn_id}: {e}")

        return sent_count

    # -------------------------------------------------------------------------
    # Redis Pub/Sub
    # -------------------------------------------------------------------------

    async def start_redis_subscriber(self) -> None:
        """Start Redis pub/sub subscriber for cross-instance communication."""
        redis = await self._get_redis()
        if not redis:
            logger.warning("Redis not available, pub/sub disabled")
            return

        async def subscriber():
            try:
                pubsub = redis.pubsub()
                await pubsub.subscribe(
                    REDIS_BROADCAST_CHANNEL,
                    f"{REDIS_USER_CHANNEL_PREFIX}*",
                )

                logger.info("Redis pub/sub subscriber started ✅")

                while not self._shutdown_event.is_set():
                    try:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=1.0,
                        )
                        if message:
                            await self._handle_redis_message(message)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Redis subscriber error: {e}")
                        await asyncio.sleep(1)

                await pubsub.unsubscribe()
                await pubsub.close()
                logger.info("Redis pub/sub subscriber stopped")

            except Exception as e:
                logger.error(f"Failed to start Redis subscriber: {e}")

        self._subscriber_task = asyncio.create_task(subscriber())

    async def stop_redis_subscriber(self) -> None:
        """Stop Redis pub/sub subscriber."""
        self._shutdown_event.set()
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass

    async def _handle_redis_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming Redis pub/sub message."""
        try:
            channel = message.get("channel", "")
            data = json.loads(message.get("data", "{}"))

            if channel == REDIS_BROADCAST_CHANNEL:
                # Broadcast to all connections
                msg = RedisBroadcastMessage(**data)
                await self.broadcast_all(
                    msg.event,
                    msg.data,
                    exclude_connection=msg.exclude_connections[0]
                    if msg.exclude_connections
                    else None,
                )

            elif channel.startswith(REDIS_USER_CHANNEL_PREFIX):
                # Send to specific user
                msg = RedisUserMessage(**data)
                await self.broadcast_to_user(
                    msg.user_id,
                    msg.event,
                    msg.data,
                    exclude_connection=msg.exclude_connections[0]
                    if msg.exclude_connections
                    else None,
                )

        except Exception as e:
            logger.error(f"Failed to handle Redis message: {e}")

    async def publish_to_redis(
        self,
        channel: str,
        event: str,
        data: Dict[str, Any],
        exclude_connections: Optional[List[str]] = None,
    ) -> None:
        """Publish message to Redis for cross-instance broadcast."""
        redis = await self._get_redis()
        if not redis:
            return

        try:
            message = RedisBroadcastMessage(
                event=event,
                data=data,
                exclude_connections=exclude_connections,
            )
            await redis.publish(channel, message.model_dump_json())
        except Exception as e:
            logger.warning(f"Failed to publish to Redis: {e}")

    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    def record_event(
        self,
        event: str,
        endpoint: str,
        duration: Optional[float] = None,
    ) -> None:
        """Record event metrics."""
        if not self._metrics_enabled:
            return

        websocket_events_total.labels(event=event, endpoint=endpoint).inc()

        if duration is not None:
            websocket_event_duration.labels(
                event=event, endpoint=endpoint
            ).observe(duration)

    def record_error(self, error_type: str, endpoint: str) -> None:
        """Record error metrics."""
        if not self._metrics_enabled:
            return

        websocket_errors.labels(type=error_type, endpoint=endpoint).inc()


# =============================================================================
# WebSocket Route Handler
# =============================================================================


class WebSocketRouteHandler:
    """
    Handles WebSocket connection lifecycle for a single endpoint.

    Manages:
    - Authentication
    - Rate limiting
    - Event routing
    - Connection cleanup
    """

    def __init__(
        self,
        manager: ConnectionManager,
        endpoint: str = "/ws",
    ):
        self.manager = manager
        self.endpoint = endpoint
        self.middleware = WebSocketMiddleware()

    async def __call__(
        self,
        websocket: WebSocket,
        session: AsyncSession,
    ) -> None:
        """
        Handle WebSocket connection lifecycle.

        Args:
            websocket: The WebSocket connection.
            session: Database session for authentication.
        """
        connection_id = None
        user = None

        try:
            # Accept connection
            await websocket.accept()

            # Authenticate
            try:
                user = await self.middleware.authenticate(websocket, session)
            except WebSocketAuthError as e:
                await websocket.close(code=e.code, reason=e.message)
                return

            # Register connection
            connection_id = await self.manager.connect(
                websocket, user, endpoint=self.endpoint
            )

            # Create handlers instance
            handlers = WebSocketHandlers(
                session=session,
                connection_manager=self.manager,
                room_manager=self.manager.rooms,
                middleware=self.middleware,
                redis_client=await self.manager._get_redis(),
            )

            # Handle connection
            await handlers.handle_connect(websocket, user, connection_id)

            # Message loop
            await self._message_loop(websocket, user, connection_id, handlers)

        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup
            if connection_id and user:
                await handlers.handle_disconnect(
                    websocket, user, connection_id
                )
            if connection_id:
                await self.manager.disconnect(connection_id)

    async def _message_loop(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        connection_id: str,
        handlers: WebSocketHandlers,
    ) -> None:
        """Process incoming WebSocket messages."""
        while True:
            try:
                # Receive message
                message = await websocket.receive_text()

                # Check message size
                if len(message) > WS_MAX_MESSAGE_SIZE:
                    await self._send_error(
                        websocket,
                        "Message too large",
                        ErrorCodes.VALIDATION_ERROR,
                    )
                    continue

                # Check rate limit
                try:
                    await self.middleware.check_rate_limit(user["id"])
                except WebSocketRateLimitError as e:
                    await self._send_error(
                        websocket,
                        f"Rate limit exceeded. Retry after {e.retry_after:.0f}s",
                        ErrorCodes.RATE_LIMITED,
                    )
                    continue

                # Parse event
                try:
                    event, data = self.middleware.parse_message(message)
                except WebSocketValidationError as e:
                    await self._send_error(
                        websocket,
                        e.message,
                        ErrorCodes.VALIDATION_ERROR,
                        e.details,
                    )
                    continue

                # Validate event data
                try:
                    validated_data = self.middleware.validate_event(event, data)
                except WebSocketValidationError as e:
                    await self._send_error(
                        websocket,
                        e.message,
                        ErrorCodes.VALIDATION_ERROR,
                        e.details,
                    )
                    continue

                # Track performance
                import time

                start_time = time.perf_counter()

                # Handle event
                await handlers.handle_event(
                    websocket, user, connection_id, event, validated_data
                )

                # Record metrics
                duration = time.perf_counter() - start_time
                self.manager.record_event(event, self.endpoint, duration)

            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                await self._send_error(
                    websocket,
                    "Internal server error",
                    ErrorCodes.INTERNAL_ERROR,
                )

    async def _send_error(
        self,
        websocket: WebSocket,
        message: str,
        code: ErrorCodes,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send error event to client."""
        try:
            await websocket.send_json({
                "event": Events.ERROR,
                "data": {
                    "code": code.value,
                    "message": message,
                    "details": details,
                },
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass


# =============================================================================
# Router Setup
# =============================================================================


def setup_websocket_routes(
    manager: Optional[ConnectionManager],
) -> APIRouter:
    """
    Create WebSocket router with all endpoints.

    Endpoints:
    - /ws - Main endpoint for user operations
    - /ws/chat - Chat messaging endpoint
    - /ws/notifications - Real-time notifications endpoint

    Args:
        manager: ConnectionManager instance.

    Returns:
        APIRouter with WebSocket routes.
    """
    router = APIRouter(prefix="/ws", tags=["websocket"])

    async def _get_manager() -> ConnectionManager:
        nonlocal manager
        if manager is None:
            redis = await get_redis()
            manager = ConnectionManager(redis)
            await manager.start_redis_subscriber()
        return manager

    # Main WebSocket endpoint
    @router.websocket("/")
    async def websocket_main(
        websocket: WebSocket,
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        handler = WebSocketRouteHandler(await _get_manager(), endpoint="/ws")
        await handler(websocket, session)

    # Chat WebSocket endpoint
    @router.websocket("/chat")
    async def websocket_chat(
        websocket: WebSocket,
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        handler = WebSocketRouteHandler(await _get_manager(), endpoint="/ws/chat")
        await handler(websocket, session)

    # Notifications WebSocket endpoint
    @router.websocket("/notifications")
    async def websocket_notifications(
        websocket: WebSocket,
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        handler = WebSocketRouteHandler(await _get_manager(), endpoint="/ws/notifications")
        await handler(websocket, session)

    return router


# =============================================================================
# Application Integration
# =============================================================================


class WebSocketManager:
    """
    High-level WebSocket manager for application integration.

    Usage:
        ws_manager = WebSocketManager()
        app.include_router(ws_manager.get_router())

        @app.on_event("startup")
        async def startup():
            await ws_manager.start()

        @app.on_event("shutdown")
        async def shutdown():
            await ws_manager.stop()
    """

    def __init__(self) -> None:
        self.connection_manager: Optional[ConnectionManager] = None
        self._router: Optional[APIRouter] = None

    async def start(self) -> None:
        """Initialize WebSocket manager."""
        redis = await get_redis()
        self.connection_manager = ConnectionManager(redis)
        await self.connection_manager.start_redis_subscriber()
        logger.info("WebSocket manager started ✅")

    async def stop(self) -> None:
        """Shutdown WebSocket manager."""
        if self.connection_manager:
            await self.connection_manager.stop_redis_subscriber()
        logger.info("WebSocket manager stopped ⏸️")

    def get_router(self) -> APIRouter:
        """Get WebSocket router for app inclusion."""
        if not self._router:
            self._router = setup_websocket_routes(self.connection_manager)
        return self._router

    async def broadcast(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> int:
        """Broadcast to all connections."""
        if not self.connection_manager:
            return 0
        return await self.connection_manager.broadcast_all(event, data)

    async def send_to_user(
        self,
        user_id: str,
        event: str,
        data: Dict[str, Any],
    ) -> int:
        """Send event to all connections of a user."""
        if not self.connection_manager:
            return 0
        return await self.connection_manager.broadcast_to_user(
            user_id, event, data
        )

    async def send_to_room(
        self,
        room_name: str,
        event: str,
        data: Dict[str, Any],
    ) -> int:
        """Send event to all connections in a room."""
        if not self.connection_manager:
            return 0
        return await self.connection_manager.broadcast_to_room(
            room_name, event, data
        )


# Global instance for convenience
ws_manager = WebSocketManager()
