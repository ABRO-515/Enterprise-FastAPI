"""WebSocket module for real-time communication.

This module provides production-ready WebSocket support for FastAPI applications.

Features:
- JWT authentication for WebSocket connections
- Rate limiting per user
- Room-based broadcasting
- Redis pub/sub for cross-instance communication
- Prometheus metrics integration
- Comprehensive event handling

Usage:
    from app.ws import ws_manager, ConnectionManager, setup_websocket_routes

    # In main.py
    from app.ws import ws_manager

    @app.on_event("startup")
    async def startup():
        await ws_manager.start()

    @app.on_event("shutdown")
    async def shutdown():
        await ws_manager.stop()

    app.include_router(ws_manager.get_router())

    # Send messages
    await ws_manager.send_to_user(user_id, "notification:new", {...})
    await ws_manager.broadcast("system:alert", {...})
"""

# Core components
from app.ws.server_ws import (
    ConnectionManager,
    ConnectionInfo,
    WebSocketManager,
    WebSocketRouteHandler,
    setup_websocket_routes,
    ws_manager,
)

# Middleware
from app.ws.middleware_ws import (
    InputValidator,
    PerformanceTracker,
    WebSocketAuthError,
    WebSocketMiddleware,
    WebSocketRateLimitError,
    WebSocketRateLimiter,
    WebSocketValidationError,
    create_error_response,
    websocket_auth_middleware,
)

# Handlers
from app.ws.handlers_ws import WebSocketHandlers

# Event models
from app.ws.events_ws import (
    # Base
    WebSocketEvent,
    EventPayload,
    # Requests
    SubscribeRequest,
    UnsubscribeRequest,
    UserGetRequest,
    UserUpdateRequest,
    UserStatusRequest,
    UserDeleteRequest,
    MessageSendRequest,
    TypingRequest,
    NotificationMarkReadRequest,
    NotificationMarkAllReadRequest,
    PingRequest,
    # Responses
    ConnectedResponse,
    SubscribedResponse,
    UnsubscribedResponse,
    UserResponse,
    UserUpdatedResponse,
    UserDeletedResponse,
    UserStatusChangedResponse,
    MessageReceiveResponse,
    MessageSentResponse,
    TypingStartedResponse,
    TypingStoppedResponse,
    NotificationResponse,
    NotificationMarkedReadResponse,
    NotificationAllMarkedReadResponse,
    ErrorResponse,
    PongResponse,
    # Redis messages
    RedisBroadcastMessage,
    RedisUserMessage,
)

# Room management
from app.ws.rooms_ws import RoomManager

# Constants
from app.ws.constants_ws import (
    Events,
    Channel,
    UserStatus,
    CloseCodes,
    ErrorCodes,
    ALLOWED_CHANNELS,
    VALID_USER_STATUSES,
    DEFAULT_RATE_LIMIT,
    RATE_LIMIT_WINDOW,
    WS_HEARTBEAT_INTERVAL,
    WS_CONNECTION_TIMEOUT,
    WS_MAX_MESSAGE_SIZE,
    REDIS_BROADCAST_CHANNEL,
    REDIS_USER_CHANNEL_PREFIX,
    REDIS_ROOM_CHANNEL_PREFIX,
)

__all__ = [
    # Core
    "ConnectionManager",
    "ConnectionInfo",
    "WebSocketManager",
    "WebSocketRouteHandler",
    "setup_websocket_routes",
    "ws_manager",
    # Middleware
    "InputValidator",
    "PerformanceTracker",
    "WebSocketAuthError",
    "WebSocketMiddleware",
    "WebSocketRateLimitError",
    "WebSocketRateLimiter",
    "WebSocketValidationError",
    "create_error_response",
    "websocket_auth_middleware",
    # Handlers
    "WebSocketHandlers",
    # Events
    "WebSocketEvent",
    "EventPayload",
    "SubscribeRequest",
    "UnsubscribeRequest",
    "UserGetRequest",
    "UserUpdateRequest",
    "UserStatusRequest",
    "UserDeleteRequest",
    "MessageSendRequest",
    "TypingRequest",
    "NotificationMarkReadRequest",
    "NotificationMarkAllReadRequest",
    "PingRequest",
    "ConnectedResponse",
    "SubscribedResponse",
    "UnsubscribedResponse",
    "UserResponse",
    "UserUpdatedResponse",
    "UserDeletedResponse",
    "UserStatusChangedResponse",
    "MessageReceiveResponse",
    "MessageSentResponse",
    "TypingStartedResponse",
    "TypingStoppedResponse",
    "NotificationResponse",
    "NotificationMarkedReadResponse",
    "NotificationAllMarkedReadResponse",
    "ErrorResponse",
    "PongResponse",
    "RedisBroadcastMessage",
    "RedisUserMessage",
    # Rooms
    "RoomManager",
    # Constants
    "Events",
    "Channel",
    "UserStatus",
    "CloseCodes",
    "ErrorCodes",
    "ALLOWED_CHANNELS",
    "VALID_USER_STATUSES",
    "DEFAULT_RATE_LIMIT",
    "RATE_LIMIT_WINDOW",
    "WS_HEARTBEAT_INTERVAL",
    "WS_CONNECTION_TIMEOUT",
    "WS_MAX_MESSAGE_SIZE",
    "REDIS_BROADCAST_CHANNEL",
    "REDIS_USER_CHANNEL_PREFIX",
    "REDIS_ROOM_CHANNEL_PREFIX",
]
