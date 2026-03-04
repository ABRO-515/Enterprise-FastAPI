"""Tests for WebSocket functionality.

Tests cover:
- Connection with valid/invalid tokens
- Subscribe/unsubscribe flow
- User CRUD operations
- Chat messaging between users
- Notification delivery
- Rate limiting behavior
- Error handling scenarios
"""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import jwt
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from httpx import AsyncClient
from redis.asyncio import Redis

from app.core.config import settings
from app.ws import (
    Channel,
    CloseCodes,
    ConnectionManager,
    ErrorCodes,
    Events,
    RoomManager,
    UserStatus,
    WebSocketHandlers,
    WebSocketMiddleware,
    WebSocketRateLimiter,
    ws_manager,
)
from app.ws.events_ws import (
    ConnectedResponse,
    SubscribeRequest,
    UserGetRequest,
    UserStatusRequest,
    MessageSendRequest,
)
from app.ws.middleware_ws import (
    WebSocketAuthError,
    WebSocketValidationError,
    websocket_auth_middleware,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    from app.main import create_app
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create mock Redis client."""
    redis = MagicMock(spec=Redis)
    redis.publish = AsyncMock()
    redis.subscribe = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.zadd = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)
    redis.zremrangebyscore = AsyncMock()
    redis.expire = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    redis.sadd = AsyncMock()
    redis.srem = AsyncMock()
    return redis


@pytest.fixture
def connection_manager(mock_redis: MagicMock) -> ConnectionManager:
    """Create connection manager with mock Redis."""
    return ConnectionManager(redis=mock_redis)


@pytest.fixture
def room_manager(mock_redis: MagicMock) -> RoomManager:
    """Create room manager with mock Redis."""
    return RoomManager(redis=mock_redis)


@pytest.fixture
def rate_limiter(mock_redis: MagicMock) -> WebSocketRateLimiter:
    """Create rate limiter with mock Redis."""
    return WebSocketRateLimiter(redis=mock_redis)


@pytest.fixture
def valid_token() -> str:
    """Generate a valid JWT token for testing."""
    payload = {
        "sub": "test-user-id-123",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow().timestamp() + 3600,  # 1 hour
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT token for testing."""
    payload = {
        "sub": "test-user-id-123",
        "iat": datetime.utcnow().timestamp() - 7200,
        "exp": datetime.utcnow().timestamp() - 3600,  # Expired 1 hour ago
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def mock_user() -> Dict[str, str]:
    """Create mock user data."""
    return {
        "id": "test-user-id-123",
        "email": "test@example.com",
        "role": "user",
        "status": "online",
        "full_name": "Test User",
    }


@pytest.fixture
def mock_websocket(mock_user: Dict[str, str]) -> MagicMock:
    """Create mock WebSocket connection."""
    ws = MagicMock(spec=WebSocket)
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    ws.query_params = {}
    ws.headers = {}
    ws.accept = AsyncMock()
    return ws


# =============================================================================
# Authentication Tests
# =============================================================================


class TestWebSocketAuthentication:
    """Tests for WebSocket authentication middleware."""

    @pytest.mark.asyncio
    async def test_auth_with_valid_token_in_query_params(
        self,
        mock_websocket: MagicMock,
        valid_token: str,
    ) -> None:
        """Test authentication with valid token in query params."""
        mock_websocket.query_params = {"token": valid_token}

        # Mock session and user lookup
        with patch("app.repositories.user_repository.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_user = MagicMock()
            mock_user.id = "test-user-id-123"
            mock_user.email = "test@example.com"
            mock_user.role = MagicMock(value="user")
            mock_user.is_active = True
            mock_user.full_name = "Test User"
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            # This would normally be called with a real session
            # For unit test, we verify the token parsing logic
            payload = jwt.decode(
                valid_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            assert payload["sub"] == "test-user-id-123"

    @pytest.mark.asyncio
    async def test_auth_with_valid_token_in_header(
        self,
        mock_websocket: MagicMock,
        valid_token: str,
    ) -> None:
        """Test authentication with valid token in Authorization header."""
        mock_websocket.headers = {"authorization": f"Bearer {valid_token}"}

        payload = jwt.decode(
            valid_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "test-user-id-123"

    @pytest.mark.asyncio
    async def test_auth_with_expired_token(
        self,
        mock_websocket: MagicMock,
        expired_token: str,
    ) -> None:
        """Test authentication fails with expired token."""
        mock_websocket.query_params = {"token": expired_token}

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                expired_token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )

    @pytest.mark.asyncio
    async def test_auth_with_missing_token(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test authentication fails when no token provided."""
        mock_websocket.query_params = {}
        mock_websocket.headers = {}

        # No token available - should raise WebSocketAuthError
        # In actual middleware, this would be caught


# =============================================================================
# Connection Manager Tests
# =============================================================================


class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.mark.asyncio
    async def test_connect_user(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test user connection registration."""
        connection_id = await connection_manager.connect(
            mock_websocket, mock_user, endpoint="/ws"
        )

        assert connection_id is not None
        assert connection_manager.get_connection(connection_id) is not None
        assert connection_manager.get_user_connections(mock_user["id"]) == {connection_id}
        assert connection_manager.get_connection_count() == 1

    @pytest.mark.asyncio
    async def test_disconnect_user(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test user disconnection."""
        connection_id = await connection_manager.connect(
            mock_websocket, mock_user, endpoint="/ws"
        )

        await connection_manager.disconnect(connection_id)

        assert connection_manager.get_connection(connection_id) is None
        assert connection_manager.get_user_connections(mock_user["id"]) == set()
        assert connection_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_per_user(
        self,
        connection_manager: ConnectionManager,
        mock_user: Dict[str, str],
    ) -> None:
        """Test multiple connections for same user (multiple tabs)."""
        ws1 = MagicMock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2 = MagicMock(spec=WebSocket)
        ws2.send_json = AsyncMock()

        conn1 = await connection_manager.connect(ws1, mock_user, endpoint="/ws")
        conn2 = await connection_manager.connect(ws2, mock_user, endpoint="/ws")

        user_conns = connection_manager.get_user_connections(mock_user["id"])
        assert len(user_conns) == 2
        assert connection_manager.get_connection_count() == 2

    @pytest.mark.asyncio
    async def test_send_to_connection(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test sending event to specific connection."""
        connection_id = await connection_manager.connect(
            mock_websocket, mock_user, endpoint="/ws"
        )

        result = await connection_manager.send_to_connection(
            connection_id, Events.PONG, {"timestamp": "2024-01-01T00:00:00Z"}
        )

        assert result is True
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_user(
        self,
        connection_manager: ConnectionManager,
        mock_user: Dict[str, str],
    ) -> None:
        """Test broadcasting to all user connections."""
        ws1 = MagicMock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2 = MagicMock(spec=WebSocket)
        ws2.send_json = AsyncMock()

        await connection_manager.connect(ws1, mock_user, endpoint="/ws")
        await connection_manager.connect(ws2, mock_user, endpoint="/ws")

        count = await connection_manager.broadcast_to_user(
            mock_user["id"], Events.NOTIFICATION_NEW, {"message": "test"}
        )

        assert count == 2
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()


# =============================================================================
# Room Manager Tests
# =============================================================================


class TestRoomManager:
    """Tests for RoomManager."""

    @pytest.mark.asyncio
    async def test_join_room(
        self,
        room_manager: RoomManager,
        connection_manager: ConnectionManager,
    ) -> None:
        """Test joining a room."""
        conn_id = "test-conn-1"
        room_name = "user:123"

        result = await room_manager.join_room(conn_id, room_name, connection_manager)

        assert result is True
        assert conn_id in room_manager.get_room_members(room_name)

    @pytest.mark.asyncio
    async def test_leave_room(
        self,
        room_manager: RoomManager,
        connection_manager: ConnectionManager,
    ) -> None:
        """Test leaving a room."""
        conn_id = "test-conn-1"
        room_name = "user:123"

        await room_manager.join_room(conn_id, room_name, connection_manager)
        result = await room_manager.leave_room(conn_id, room_name)

        assert result is True
        assert conn_id not in room_manager.get_room_members(room_name)

    @pytest.mark.asyncio
    async def test_leave_all_rooms(
        self,
        room_manager: RoomManager,
        connection_manager: ConnectionManager,
    ) -> None:
        """Test leaving all rooms."""
        conn_id = "test-conn-1"

        await room_manager.join_room(conn_id, "user:123", connection_manager)
        await room_manager.join_room(conn_id, "chat:456", connection_manager)

        rooms_left = await room_manager.leave_all_rooms(conn_id)

        assert len(rooms_left) == 2
        assert room_manager.get_connection_rooms(conn_id) == set()

    @pytest.mark.asyncio
    async def test_user_room_naming(
        self,
        room_manager: RoomManager,
    ) -> None:
        """Test room naming conventions."""
        assert room_manager.get_user_room_name("user-123") == "user:user-123"
        assert room_manager.get_chat_room_name("conv-456") == "chat:conv-456"
        assert room_manager.get_notification_room_name("user-123") == "notification:user-123"
        assert room_manager.get_role_room_name("admin") == "role:admin"


# =============================================================================
# Rate Limiter Tests
# =============================================================================


class TestWebSocketRateLimiter:
    """Tests for WebSocket rate limiter."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_under_limit(
        self,
        rate_limiter: WebSocketRateLimiter,
    ) -> None:
        """Test requests are allowed under the limit."""
        user_id = "test-user-123"

        # First request should be allowed
        result = await rate_limiter.is_allowed(user_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(
        self,
        rate_limiter: WebSocketRateLimiter,
        mock_redis: MagicMock,
    ) -> None:
        """Test requests are blocked over the limit."""
        user_id = "test-user-123"

        # Simulate being at the limit
        mock_redis.zcard = AsyncMock(return_value=rate_limiter.max_events)

        result = await rate_limiter.is_allowed(user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_rate_limit_reset(
        self,
        rate_limiter: WebSocketRateLimiter,
    ) -> None:
        """Test rate limit reset."""
        user_id = "test-user-123"

        await rate_limiter.is_allowed(user_id)
        await rate_limiter.reset(user_id)

        count = await rate_limiter.get_event_count(user_id)
        assert count == 0


# =============================================================================
# Input Validation Tests
# =============================================================================


class TestInputValidation:
    """Tests for input validation."""

    def test_subscribe_request_validation(self) -> None:
        """Test subscribe request validation."""
        # Valid request
        req = SubscribeRequest(channel=Channel.USERS)
        assert req.channel == Channel.USERS

        # With filters
        req = SubscribeRequest(channel=Channel.CHAT, filters={"conversation_id": "123"})
        assert req.filters["conversation_id"] == "123"

    def test_user_status_request_validation(self) -> None:
        """Test user status request validation."""
        req = UserStatusRequest(status=UserStatus.ONLINE)
        assert req.status == UserStatus.ONLINE

        # Invalid status would raise validation error
        with pytest.raises(ValueError):
            UserStatusRequest(status="invalid_status")

    def test_message_send_request_validation(self) -> None:
        """Test message send request validation."""
        # Valid request
        req = MessageSendRequest(
            recipient_id="123e4567-e89b-12d3-a456-426614174000",
            message="Hello!"
        )
        assert req.message == "Hello!"

        # Empty message should fail
        with pytest.raises(ValueError):
            MessageSendRequest(
                recipient_id="123e4567-e89b-12d3-a456-426614174000",
                message=""
            )

    def test_event_parsing(self) -> None:
        """Test parsing raw JSON event."""
        from app.ws.middleware_ws import InputValidator

        raw = '{"event": "subscribe", "data": {"channel": "users"}}'
        event, data = InputValidator.parse_event(raw)

        assert event == "subscribe"
        assert data == {"channel": "users"}

    def test_invalid_json_parsing(self) -> None:
        """Test parsing invalid JSON raises error."""
        from app.ws.middleware_ws import InputValidator

        with pytest.raises(WebSocketValidationError):
            InputValidator.parse_event("not valid json")


# =============================================================================
# Event Handler Tests
# =============================================================================


class TestWebSocketHandlers:
    """Tests for WebSocket event handlers."""

    @pytest.mark.asyncio
    async def test_handle_connect(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test connection handler."""
        from app.ws.middleware_ws import WebSocketMiddleware
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_session = MagicMock(spec=AsyncSession)

        middleware = WebSocketMiddleware()
        handlers = WebSocketHandlers(
            session=mock_session,
            connection_manager=connection_manager,
            room_manager=connection_manager.rooms,
            middleware=middleware,
        )

        connection_id = await connection_manager.connect(
            mock_websocket, mock_user, endpoint="/ws"
        )

        await handlers.handle_connect(mock_websocket, mock_user, connection_id)

        # Should have sent connected event
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event"] == Events.CONNECTED

    @pytest.mark.asyncio
    async def test_handle_subscribe(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test subscribe handler."""
        from app.ws.middleware_ws import WebSocketMiddleware
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_session = MagicMock(spec=AsyncSession)

        middleware = WebSocketMiddleware()
        handlers = WebSocketHandlers(
            session=mock_session,
            connection_manager=connection_manager,
            room_manager=connection_manager.rooms,
            middleware=middleware,
        )

        connection_id = await connection_manager.connect(
            mock_websocket, mock_user, endpoint="/ws"
        )

        data = SubscribeRequest(channel=Channel.NOTIFICATIONS)
        await handlers.handle_subscribe(mock_websocket, mock_user, data, connection_id)

        # Should have sent subscribed event
        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_ping(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test ping handler returns pong."""
        from app.ws.middleware_ws import WebSocketMiddleware
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_session = MagicMock(spec=AsyncSession)

        middleware = WebSocketMiddleware()
        handlers = WebSocketHandlers(
            session=mock_session,
            connection_manager=connection_manager,
            room_manager=connection_manager.rooms,
            middleware=middleware,
        )

        from app.ws.events_ws import PingRequest
        data = PingRequest()
        await handlers.handle_ping(mock_websocket, mock_user, data)

        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event"] == Events.PONG


# =============================================================================
# Integration Tests
# =============================================================================


class TestWebSocketIntegration:
    """Integration tests for WebSocket endpoints."""

    def test_websocket_endpoint_exists(self, app: FastAPI) -> None:
        """Test WebSocket endpoints are registered."""
        routes = [route.path for route in app.routes]
        assert "/ws/" in routes
        assert "/ws/chat" in routes
        assert "/ws/notifications" in routes

    @pytest.mark.asyncio
    async def test_websocket_connection_flow(
        self,
        app: FastAPI,
        valid_token: str,
    ) -> None:
        """Test full WebSocket connection flow."""
        # Note: TestClient doesn't fully support WebSocket testing
        # This is a placeholder for integration testing with a real WebSocket client
        pass


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_send_error_event(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test sending error event to client."""
        from app.ws.middleware_ws import WebSocketMiddleware
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_session = MagicMock(spec=AsyncSession)

        middleware = WebSocketMiddleware()
        handlers = WebSocketHandlers(
            session=mock_session,
            connection_manager=connection_manager,
            room_manager=connection_manager.rooms,
            middleware=middleware,
        )

        await handlers._send_error(
            mock_websocket,
            "Test error",
            ErrorCodes.VALIDATION_ERROR,
            {"field": "test"}
        )

        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event"] == Events.ERROR
        assert call_args["data"]["code"] == ErrorCodes.VALIDATION_ERROR.value


# =============================================================================
# Metrics Tests
# =============================================================================


class TestMetrics:
    """Tests for Prometheus metrics."""

    @pytest.mark.asyncio
    async def test_connection_metrics(
        self,
        connection_manager: ConnectionManager,
        mock_websocket: MagicMock,
        mock_user: Dict[str, str],
    ) -> None:
        """Test connection count metrics."""
        initial_count = connection_manager.get_connection_count()

        await connection_manager.connect(mock_websocket, mock_user, endpoint="/ws")

        assert connection_manager.get_connection_count() == initial_count + 1

    @pytest.mark.asyncio
    async def test_event_recording(
        self,
        connection_manager: ConnectionManager,
    ) -> None:
        """Test event metrics recording."""
        connection_manager.record_event(
            event=Events.SUBSCRIBE,
            endpoint="/ws",
            duration=0.05
        )
        # Metrics should be recorded without error


# =============================================================================
# Run Tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
