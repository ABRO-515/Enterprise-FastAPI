"""Room management utilities for WebSocket connections.

Room naming conventions:
- user:{user_id} - User's personal room for direct messages/notifications
- chat:{conversation_id} - Chat conversation room
- notification:{user_id} - User's notification room
- role:{role} - All users with specific role
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from fastapi import WebSocket
from redis.asyncio import Redis

from app.ws.constants_ws import REDIS_ROOM_CHANNEL_PREFIX

if TYPE_CHECKING:
    from app.ws.server_ws import ConnectionManager

logger = logging.getLogger("app.ws.rooms")


class RoomManager:
    """
    Manages WebSocket rooms for targeted broadcasting.

    Rooms are logical groupings of connections for efficient message delivery.
    This manager tracks room membership both locally and in Redis for
    cross-instance communication.
    """

    def __init__(self, redis: Optional[Redis] = None):
        """
        Initialize room manager.

        Args:
            redis: Optional Redis client for distributed room tracking.
        """
        self._redis = redis
        # Local room tracking: room_name -> set of connection_ids
        self._rooms: Dict[str, Set[str]] = {}
        # Reverse mapping: connection_id -> set of room_names
        self._connection_rooms: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    def _user_room(self, user_id: str) -> str:
        """Generate user's personal room name."""
        return f"user:{user_id}"

    def _chat_room(self, conversation_id: str) -> str:
        """Generate chat conversation room name."""
        return f"chat:{conversation_id}"

    def _notification_room(self, user_id: str) -> str:
        """Generate user's notification room name."""
        return f"notification:{user_id}"

    def _role_room(self, role: str) -> str:
        """Generate role-based room name."""
        return f"role:{role}"

    async def join_room(
        self,
        connection_id: str,
        room_name: str,
        manager: "ConnectionManager",
    ) -> bool:
        """
        Add a connection to a room.

        Args:
            connection_id: The connection ID to add.
            room_name: The room to join.
            manager: Connection manager for accessing websocket instances.

        Returns:
            True if joined successfully, False if connection not found.
        """
        async with self._lock:
            # Track locally
            if room_name not in self._rooms:
                self._rooms[room_name] = set()
            self._rooms[room_name].add(connection_id)

            # Track reverse mapping
            if connection_id not in self._connection_rooms:
                self._connection_rooms[connection_id] = set()
            self._connection_rooms[connection_id].add(room_name)

            # Track in Redis for cross-instance
            if self._redis:
                try:
                    await self._redis.sadd(
                        f"ws_room:{room_name}", connection_id
                    )
                    await self._redis.sadd(
                        f"ws_conn_rooms:{connection_id}", room_name
                    )
                except Exception as e:
                    logger.warning(f"Failed to track room in Redis: {e}")

            logger.debug(f"Connection {connection_id} joined room {room_name}")
            return True

    async def leave_room(
        self,
        connection_id: str,
        room_name: str,
    ) -> bool:
        """
        Remove a connection from a room.

        Args:
            connection_id: The connection ID to remove.
            room_name: The room to leave.

        Returns:
            True if left successfully, False if not in room.
        """
        async with self._lock:
            # Remove from local tracking
            if room_name in self._rooms:
                self._rooms[room_name].discard(connection_id)
                if not self._rooms[room_name]:
                    del self._rooms[room_name]

            # Remove from reverse mapping
            if connection_id in self._connection_rooms:
                self._connection_rooms[connection_id].discard(room_name)
                if not self._connection_rooms[connection_id]:
                    del self._connection_rooms[connection_id]

            # Remove from Redis
            if self._redis:
                try:
                    await self._redis.srem(
                        f"ws_room:{room_name}", connection_id
                    )
                    await self._redis.srem(
                        f"ws_conn_rooms:{connection_id}", room_name
                    )
                except Exception as e:
                    logger.warning(f"Failed to remove room from Redis: {e}")

            logger.debug(f"Connection {connection_id} left room {room_name}")
            return True

    async def leave_all_rooms(self, connection_id: str) -> List[str]:
        """
        Remove a connection from all rooms.

        Args:
            connection_id: The connection ID to remove from all rooms.

        Returns:
            List of room names the connection was removed from.
        """
        async with self._lock:
            rooms_left = []

            # Get all rooms for this connection
            if connection_id in self._connection_rooms:
                rooms_left = list(self._connection_rooms[connection_id])

                # Remove from each room
                for room_name in rooms_left:
                    if room_name in self._rooms:
                        self._rooms[room_name].discard(connection_id)
                        if not self._rooms[room_name]:
                            del self._rooms[room_name]

                # Clear reverse mapping
                del self._connection_rooms[connection_id]

            # Clean up Redis
            if self._redis:
                try:
                    for room_name in rooms_left:
                        await self._redis.srem(
                            f"ws_room:{room_name}", connection_id
                        )
                    await self._redis.delete(
                        f"ws_conn_rooms:{connection_id}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to clean rooms in Redis: {e}")

            if rooms_left:
                logger.debug(
                    f"Connection {connection_id} left rooms: {rooms_left}"
                )
            return rooms_left

    def get_room_members(self, room_name: str) -> Set[str]:
        """
        Get all connection IDs in a room (local only).

        Args:
            room_name: The room to query.

        Returns:
            Set of connection IDs in the room.
        """
        return self._rooms.get(room_name, set()).copy()

    def get_connection_rooms(self, connection_id: str) -> Set[str]:
        """
        Get all rooms a connection is in.

        Args:
            connection_id: The connection ID to query.

        Returns:
            Set of room names the connection is in.
        """
        return self._connection_rooms.get(connection_id, set()).copy()

    async def get_room_members_distributed(self, room_name: str) -> Set[str]:
        """
        Get all connection IDs in a room across all instances.

        Args:
            room_name: The room to query.

        Returns:
            Set of connection IDs in the room across all instances.
        """
        # Start with local members
        members = self.get_room_members(room_name)

        # Add members from Redis if available
        if self._redis:
            try:
                remote_members = await self._redis.smembers(
                    f"ws_room:{room_name}"
                )
                members.update(remote_members)
            except Exception as e:
                logger.warning(f"Failed to get remote room members: {e}")

        return members

    async def join_user_room(
        self,
        connection_id: str,
        user_id: str,
        manager: "ConnectionManager",
    ) -> bool:
        """Join a user's personal room."""
        return await self.join_room(
            connection_id, self._user_room(user_id), manager
        )

    async def join_chat_room(
        self,
        connection_id: str,
        conversation_id: str,
        manager: "ConnectionManager",
    ) -> bool:
        """Join a chat conversation room."""
        return await self.join_room(
            connection_id, self._chat_room(conversation_id), manager
        )

    async def join_notification_room(
        self,
        connection_id: str,
        user_id: str,
        manager: "ConnectionManager",
    ) -> bool:
        """Join a user's notification room."""
        return await self.join_room(
            connection_id, self._notification_room(user_id), manager
        )

    async def join_role_room(
        self,
        connection_id: str,
        role: str,
        manager: "ConnectionManager",
    ) -> bool:
        """Join a role-based room."""
        return await self.join_room(
            connection_id, self._role_room(role), manager
        )

    def get_user_room_name(self, user_id: str) -> str:
        """Get the room name for a user."""
        return self._user_room(user_id)

    def get_chat_room_name(self, conversation_id: str) -> str:
        """Get the room name for a chat conversation."""
        return self._chat_room(conversation_id)

    def get_notification_room_name(self, user_id: str) -> str:
        """Get the room name for a user's notifications."""
        return self._notification_room(user_id)

    def get_role_room_name(self, role: str) -> str:
        """Get the room name for a role."""
        return self._role_room(role)

    async def get_room_count(self, room_name: str) -> int:
        """Get the number of connections in a room."""
        return len(await self.get_room_members_distributed(room_name))

    async def clear_room(self, room_name: str) -> int:
        """
        Clear all connections from a room.

        Args:
            room_name: The room to clear.

        Returns:
            Number of connections removed.
        """
        async with self._lock:
            count = 0

            # Get members and remove them
            if room_name in self._rooms:
                members = list(self._rooms[room_name])
                for conn_id in members:
                    if conn_id in self._connection_rooms:
                        self._connection_rooms[conn_id].discard(room_name)
                    count += 1
                del self._rooms[room_name]

            # Clear from Redis
            if self._redis:
                try:
                    members = await self._redis.smembers(f"ws_room:{room_name}")
                    for conn_id in members:
                        await self._redis.srem(
                            f"ws_conn_rooms:{conn_id}", room_name
                        )
                    await self._redis.delete(f"ws_room:{room_name}")
                except Exception as e:
                    logger.warning(f"Failed to clear room in Redis: {e}")

            logger.debug(f"Cleared room {room_name}, removed {count} connections")
            return count

    async def cleanup_connection(self, connection_id: str) -> List[str]:
        """
        Clean up all room membership for a disconnected connection.

        Args:
            connection_id: The connection ID to clean up.

        Returns:
            List of rooms the connection was removed from.
        """
        return await self.leave_all_rooms(connection_id)
