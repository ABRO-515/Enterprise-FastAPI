"""WebSocket event handlers for business logic.

All handlers follow the pattern:
1. Validate input using Pydantic models
2. Call appropriate mediator/service via DI
3. Emit response event(s) to socket or rooms
4. Handle errors gracefully with proper error events
"""

import json
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from fastapi import WebSocket
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError
from app.ws.constants_ws import (
    ALLOWED_CHANNELS,
    Channel,
    CloseCodes,
    ErrorCodes,
    Events,
    UserStatus,
    VALID_USER_STATUSES,
)
from app.ws.events_ws import (
    ConnectedResponse,
    ErrorResponse,
    MessageReceiveResponse,
    MessageSentResponse,
    NotificationMarkedReadResponse,
    NotificationAllMarkedReadResponse,
    NotificationResponse,
    SubscribedResponse,
    TypingStartedResponse,
    TypingStoppedResponse,
    UnsubscribedResponse,
    UserDeletedResponse,
    UserResponse,
    UserStatusChangedResponse,
    UserUpdatedResponse,
)
from app.ws.middleware_ws import WebSocketMiddleware, WebSocketValidationError
from app.ws.rooms_ws import RoomManager

if TYPE_CHECKING:
    from app.ws.server_ws import ConnectionManager

logger = logging.getLogger("app.ws.handlers")


class WebSocketHandlers:
    """
    All WebSocket event handlers organized as methods.

    Each handler receives:
    - websocket: The WebSocket connection
    - user: Dict with authenticated user info
    - data: Validated request data (Pydantic model)

    Handlers should:
    1. Validate input using Pydantic models
    2. Call appropriate mediator/service via DI container
    3. Emit response event(s) to socket or rooms
    4. Handle errors gracefully with proper error events
    5. Log operations with correlation IDs
    """

    def __init__(
        self,
        session: AsyncSession,
        connection_manager: "ConnectionManager",
        room_manager: RoomManager,
        middleware: WebSocketMiddleware,
        redis_client: Optional[Any] = None,
    ):
        self.session = session
        self.manager = connection_manager
        self.rooms = room_manager
        self.middleware = middleware
        self.redis = redis_client

        # Track active subscriptions per connection
        self._subscriptions: Dict[str, Set[str]] = {}

        # Track user statuses
        self._user_statuses: Dict[str, UserStatus] = {}

    async def _send_event(
        self,
        websocket: WebSocket,
        event: str,
        data: Dict[str, Any],
    ) -> None:
        """Send an event to a WebSocket client."""
        try:
            await websocket.send_json({
                "event": event,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to send event {event}: {e}")

    async def _send_error(
        self,
        websocket: WebSocket,
        message: str,
        code: ErrorCodes = ErrorCodes.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send error event to client."""
        await self._send_event(
            websocket,
            Events.ERROR,
            {
                "code": code.value,
                "message": message,
                "details": details,
            },
        )

    async def _broadcast_to_room(
        self,
        room_name: str,
        event: str,
        data: Dict[str, Any],
        exclude: Optional[str] = None,
    ) -> None:
        """Broadcast event to all connections in a room."""
        await self.manager.broadcast_to_room(
            room_name, event, data, exclude_connection=exclude
        )

    async def _broadcast_to_user(
        self,
        user_id: str,
        event: str,
        data: Dict[str, Any],
        exclude: Optional[str] = None,
    ) -> None:
        """Broadcast event to all connections of a user."""
        room_name = self.rooms.get_user_room_name(user_id)
        await self._broadcast_to_room(room_name, event, data, exclude)

    # =========================================================================
    # Connection Lifecycle Handlers
    # =========================================================================

    async def handle_connect(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        connection_id: str,
    ) -> None:
        """
        Handle new WebSocket connection.

        - Join user's personal room
        - Update user status to online
        - Emit connected event
        """
        user_id = user["id"]

        # Track subscription
        if connection_id not in self._subscriptions:
            self._subscriptions[connection_id] = set()

        # Set user status
        self._user_statuses[user_id] = UserStatus.ONLINE

        # Join user's personal room
        await self.rooms.join_user_room(connection_id, user_id, self.manager)

        # Join notification room
        await self.rooms.join_notification_room(connection_id, user_id, self.manager)

        # Join role room if applicable
        role = user.get("role")
        if role:
            await self.rooms.join_role_room(connection_id, role, self.manager)

        # Send connected event
        response = ConnectedResponse(
            user_id=user_id,
            email=user["email"],
            role=user["role"],
            status=UserStatus.ONLINE,
            connection_id=connection_id,
        )
        await self._send_event(websocket, Events.CONNECTED, response.model_dump())

        # Broadcast status change to user's room
        await self._broadcast_to_user(
            user_id,
            Events.USER_STATUS_CHANGED,
            {
                "user_id": user_id,
                "status": UserStatus.ONLINE.value,
            },
            exclude=connection_id,
        )

        logger.info(f"User {user_id} connected with connection {connection_id}")

    async def handle_disconnect(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        connection_id: str,
    ) -> None:
        """
        Handle WebSocket disconnection.

        - Leave all rooms
        - Update user status if no more connections
        - Clean up subscriptions
        """
        user_id = user["id"]

        # Leave all rooms
        await self.rooms.leave_all_rooms(connection_id)

        # Clean up subscriptions
        self._subscriptions.pop(connection_id, None)

        # Check if user has other connections
        user_connections = self.manager.get_user_connections(user_id)
        if not user_connections or connection_id in user_connections:
            # No more connections, set status to offline
            self._user_statuses[user_id] = UserStatus.OFFLINE

            # Broadcast status change
            await self._broadcast_to_user(
                user_id,
                Events.USER_STATUS_CHANGED,
                {
                    "user_id": user_id,
                    "status": UserStatus.OFFLINE.value,
                },
            )

        logger.info(f"User {user_id} disconnected connection {connection_id}")

    # =========================================================================
    # Subscription Handlers
    # =========================================================================

    async def handle_subscribe(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle subscribe event.

        Subscribe to a channel with optional filters.
        Joins appropriate rooms based on channel type.
        """
        try:
            channel = data.channel.value
            filters = data.filters or {}

            # Validate channel
            if channel not in ALLOWED_CHANNELS:
                await self._send_error(
                    websocket,
                    f"Invalid channel: {channel}",
                    ErrorCodes.INVALID_CHANNEL,
                )
                return

            # Track subscription
            if connection_id not in self._subscriptions:
                self._subscriptions[connection_id] = set()
            self._subscriptions[connection_id].add(channel)

            # Join rooms based on channel type
            if channel == Channel.USERS.value:
                # User channel - join specific user room if filter provided
                if filters.get("user_id"):
                    await self.rooms.join_room(
                        connection_id,
                        self.rooms.get_user_room_name(filters["user_id"]),
                        self.manager,
                    )

            elif channel == Channel.NOTIFICATIONS.value:
                # Notifications channel - already joined on connect
                pass

            elif channel == Channel.CHAT.value:
                # Chat channel - join conversation room if provided
                if filters.get("conversation_id"):
                    await self.rooms.join_chat_room(
                        connection_id,
                        filters["conversation_id"],
                        self.manager,
                    )

            # Send subscribed confirmation
            response = SubscribedResponse(channel=channel, filters=filters)
            await self._send_event(websocket, Events.SUBSCRIBED, response.model_dump())

            logger.debug(f"Connection {connection_id} subscribed to {channel}")

        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            await self._send_error(
                websocket,
                str(e),
                ErrorCodes.INTERNAL_ERROR,
            )

    async def handle_unsubscribe(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle unsubscribe event.

        Unsubscribe from a channel and leave associated rooms.
        """
        try:
            channel = data.channel.value

            # Remove from tracked subscriptions
            if connection_id in self._subscriptions:
                self._subscriptions[connection_id].discard(channel)

            # Leave channel-specific rooms
            rooms_to_leave = []
            for room_name in self.rooms.get_connection_rooms(connection_id):
                if room_name.startswith(f"{channel}:"):
                    rooms_to_leave.append(room_name)

            for room_name in rooms_to_leave:
                await self.rooms.leave_room(connection_id, room_name)

            # Send unsubscribed confirmation
            response = UnsubscribedResponse(channel=channel)
            await self._send_event(
                websocket, Events.UNSUBSCRIBED, response.model_dump()
            )

            logger.debug(f"Connection {connection_id} unsubscribed from {channel}")


        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    # =========================================================================
    # User Handlers
    # =========================================================================

    async def handle_user_get(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
    ) -> None:
        """
        Handle user:get event.

        Fetch user profile by ID.
        """
        try:
            target_user_id = data.user_id

            # Get user via mediator
            from app.mediators.user_mediator import UserMediator
            from app.repositories.user_repository import UserRepository
            from app.services.user_service import UserService

            repository = UserRepository(self.session)
            service = UserService(repository)
            mediator = UserMediator(service)

            user_data = await mediator.get_user(target_user_id)

            response = UserResponse.model_validate(user_data)
            await self._send_event(websocket, Events.USER_GET, response.model_dump())

        except NotFoundError:
            await self._send_error(
                websocket,
                "User not found",
                ErrorCodes.NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Get user error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    async def handle_user_update(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle user:update event.

        Update current user's profile and broadcast changes.
        """
        try:
            user_id = user["id"]
            updates = data.model_dump(exclude_unset=True, exclude_none=True)

            if not updates:
                await self._send_error(
                    websocket,
                    "No updates provided",
                    ErrorCodes.VALIDATION_ERROR,
                )
                return

            # Update user via mediator
            from app.mediators.user_mediator import UserMediator
            from app.repositories.user_repository import UserRepository
            from app.services.user_service import UserService

            repository = UserRepository(self.session)
            service = UserService(repository)
            mediator = UserMediator(service)

            updated_user = await mediator.update_user(user_id, updates)

            # Broadcast update to user's room
            response = UserUpdatedResponse(
                user_id=user_id,
                updates=updates,
            )
            await self._broadcast_to_user(
                user_id,
                Events.USER_UPDATED,
                response.model_dump(),
            )

            logger.info(f"User {user_id} updated profile")

        except Exception as e:
            logger.error(f"Update user error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    async def handle_user_status(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle user:status event.

        Update user's online status (online/away/busy/offline).
        """
        try:
            user_id = user["id"]
            new_status = data.status

            # Get previous status
            previous_status = self._user_statuses.get(user_id, UserStatus.ONLINE)

            # Update status
            self._user_statuses[user_id] = new_status

            # Broadcast status change
            response = UserStatusChangedResponse(
                user_id=user_id,
                status=new_status,
                previous_status=previous_status,
            )
            await self._broadcast_to_user(
                user_id,
                Events.USER_STATUS_CHANGED,
                response.model_dump(),
            )

            logger.debug(f"User {user_id} status changed to {new_status}")

        except Exception as e:
            logger.error(f"Status update error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    async def handle_user_delete(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle user:delete event.

        Delete user account and disconnect.
        """
        try:
            user_id = user["id"]

            # Delete user via mediator
            from app.mediators.user_mediator import UserMediator
            from app.repositories.user_repository import UserRepository
            from app.services.user_service import UserService

            repository = UserRepository(self.session)
            service = UserService(repository)
            mediator = UserMediator(service)

            success = await mediator.delete_user(user_id)

            if not success:
                await self._send_error(
                    websocket,
                    "Failed to delete user",
                    ErrorCodes.INTERNAL_ERROR,
                )
                return

            # Broadcast deletion
            response = UserDeletedResponse(user_id=user_id)
            await self._broadcast_to_user(
                user_id,
                Events.USER_DELETED,
                response.model_dump(),
            )

            # Clean up
            await self.handle_disconnect(websocket, user, connection_id)

            logger.info(f"User {user_id} deleted their account")

        except Exception as e:
            logger.error(f"Delete user error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    # =========================================================================
    # Chat Handlers
    # =========================================================================

    async def handle_message_send(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle message:send event.

        Send chat message to recipient.
        """
        try:
            sender_id = user["id"]
            recipient_id = data.recipient_id
            message = data.message
            message_type = data.message_type

            # Generate message ID
            message_id = str(uuid.uuid4())

            # Create message data
            message_data = MessageReceiveResponse(
                message_id=message_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                message=message,
                message_type=message_type,
            )

            # Send to recipient
            await self._broadcast_to_user(
                recipient_id,
                Events.MESSAGE_RECEIVE,
                message_data.model_dump(),
            )

            # Send confirmation to sender
            sent_response = MessageSentResponse(
                message_id=message_id,
                recipient_id=recipient_id,
            )
            await self._send_event(
                websocket,
                Events.MESSAGE_SENT,
                sent_response.model_dump(),
            )

            # Optionally persist to database or message queue
            if self.redis:
                try:
                    await self.redis.publish(
                        "chat:messages",
                        json.dumps({
                            "message_id": message_id,
                            "sender_id": sender_id,
                            "recipient_id": recipient_id,
                            "message": message,
                            "message_type": message_type,
                            "timestamp": datetime.utcnow().isoformat(),
                        }),
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish message to Redis: {e}")

            logger.debug(f"Message {message_id} sent from {sender_id} to {recipient_id}")

        except Exception as e:
            logger.error(f"Send message error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    async def handle_typing_start(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle typing:start event.

        Notify recipient that sender is typing.
        """
        try:
            sender_id = user["id"]
            recipient_id = data.recipient_id
            conversation_id = data.conversation_id

            response = TypingStartedResponse(
                user_id=sender_id,
                conversation_id=conversation_id,
            )

            # Send typing indicator to recipient
            await self._broadcast_to_user(
                recipient_id,
                Events.TYPING_STARTED,
                response.model_dump(),
            )

        except Exception as e:
            logger.error(f"Typing start error: {e}")

    async def handle_typing_stop(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
        connection_id: str,
    ) -> None:
        """
        Handle typing:stop event.

        Notify recipient that sender stopped typing.
        """
        try:
            sender_id = user["id"]
            recipient_id = data.recipient_id
            conversation_id = data.conversation_id

            response = TypingStoppedResponse(
                user_id=sender_id,
                conversation_id=conversation_id,
            )

            # Send stop typing indicator to recipient
            await self._broadcast_to_user(
                recipient_id,
                Events.TYPING_STOPPED,
                response.model_dump(),
            )

        except Exception as e:
            logger.error(f"Typing stop error: {e}")

    # =========================================================================
    # Notification Handlers
    # =========================================================================

    async def handle_notification_mark_read(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
    ) -> None:
        """
        Handle notification:mark-read event.

        Mark a specific notification as read.
        """
        try:
            notification_id = data.notification_id

            # In a real implementation, update notification in database
            # For now, just send confirmation

            response = NotificationMarkedReadResponse(
                notification_id=notification_id,
            )
            await self._send_event(
                websocket,
                Events.NOTIFICATION_MARKED_READ,
                response.model_dump(),
            )

        except Exception as e:
            logger.error(f"Mark notification read error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    async def handle_notification_mark_all_read(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
    ) -> None:
        """
        Handle notification:mark-all-read event.

        Mark all notifications as read for the user.
        """
        try:
            user_id = user["id"]

            # In a real implementation, update all notifications in database
            # For now, just send confirmation

            response = NotificationAllMarkedReadResponse(count=0)
            await self._send_event(
                websocket,
                Events.NOTIFICATION_ALL_MARKED_READ,
                response.model_dump(),
            )

        except Exception as e:
            logger.error(f"Mark all notifications read error: {e}")
            await self._send_error(websocket, str(e), ErrorCodes.INTERNAL_ERROR)

    # =========================================================================
    # System Handlers
    # =========================================================================

    async def handle_ping(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        data: BaseModel,
    ) -> None:
        """
        Handle ping event.

        Respond with pong for heartbeat.
        """
        from datetime import datetime

        await self._send_event(
            websocket,
            Events.PONG,
            {"timestamp": datetime.utcnow().isoformat()},
        )

    # =========================================================================
    # Event Router
    # =========================================================================

    async def handle_event(
        self,
        websocket: WebSocket,
        user: Dict[str, Any],
        connection_id: str,
        event: str,
        data: BaseModel,
    ) -> None:
        """
        Route event to appropriate handler.

        Args:
            websocket: WebSocket connection
            user: Authenticated user dict
            connection_id: Connection ID
            event: Event name
            data: Validated event data
        """
        handler_map = {
            Events.SUBSCRIBE: lambda: self.handle_subscribe(
                websocket, user, data, connection_id
            ),
            Events.UNSUBSCRIBE: lambda: self.handle_unsubscribe(
                websocket, user, data, connection_id
            ),
            Events.USER_GET: lambda: self.handle_user_get(websocket, user, data),
            Events.USER_UPDATE: lambda: self.handle_user_update(
                websocket, user, data, connection_id
            ),
            Events.USER_STATUS: lambda: self.handle_user_status(
                websocket, user, data, connection_id
            ),
            Events.USER_DELETE: lambda: self.handle_user_delete(
                websocket, user, data, connection_id
            ),
            Events.MESSAGE_SEND: lambda: self.handle_message_send(
                websocket, user, data, connection_id
            ),
            Events.TYPING_START: lambda: self.handle_typing_start(
                websocket, user, data, connection_id
            ),
            Events.TYPING_STOP: lambda: self.handle_typing_stop(
                websocket, user, data, connection_id
            ),
            Events.NOTIFICATION_MARK_READ: lambda: self.handle_notification_mark_read(
                websocket, user, data
            ),
            Events.NOTIFICATION_MARK_ALL_READ: lambda: self.handle_notification_mark_all_read(
                websocket, user, data
            ),
            Events.PING: lambda: self.handle_ping(websocket, user, data),
        }

        handler = handler_map.get(event)

        if handler:
            await handler()
        else:
            await self._send_error(
                websocket,
                f"Unknown event: {event}",
                ErrorCodes.INVALID_EVENT,
            )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_user_status(self, user_id: str) -> UserStatus:
        """Get current status for a user."""
        return self._user_statuses.get(user_id, UserStatus.OFFLINE)

    def get_connection_subscriptions(self, connection_id: str) -> Set[str]:
        """Get channels a connection is subscribed to."""
        return self._subscriptions.get(connection_id, set()).copy()
