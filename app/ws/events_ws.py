"""Pydantic models for WebSocket event validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ws.constants_ws import Channel, ErrorCodes, UserStatus


# =============================================================================
# Base Models
# =============================================================================


class WebSocketEvent(BaseModel):
    """Base wrapper for all WebSocket events."""

    event: str
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None
    correlation_id: Optional[str] = None


# =============================================================================
# Request Models (Client -> Server)
# =============================================================================


class SubscribeRequest(BaseModel):
    """Request to subscribe to a channel with optional filters."""

    channel: Channel
    filters: Optional[Dict[str, Any]] = None


class UnsubscribeRequest(BaseModel):
    """Request to unsubscribe from a channel."""

    channel: Channel


class UserGetRequest(BaseModel):
    """Request to get user profile by ID."""

    user_id: str = Field(..., min_length=1)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        # Allow UUID format validation
        try:
            UUID(v)
        except ValueError:
            raise ValueError("Invalid user ID format, must be UUID")
        return v


class UserUpdateRequest(BaseModel):
    """Request to update user profile."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class UserStatusRequest(BaseModel):
    """Request to update user online status."""

    status: UserStatus


class UserDeleteRequest(BaseModel):
    """Request to delete user account (empty - uses authenticated user)."""

    pass


class MessageSendRequest(BaseModel):
    """Request to send a chat message."""

    recipient_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="text", pattern="^(text|image|file|system)$")


    @field_validator("recipient_id")
    @classmethod
    def validate_recipient_id(cls, v: str) -> str:
        if v == "ai":   # ✅ allow AI special case
            return v
        try:
            UUID(v)
        except ValueError:
            raise ValueError("Invalid recipient ID format, must be UUID or 'ai'")
        return v

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class TypingRequest(BaseModel):
    """Request for typing indicator."""

    recipient_id: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None

    @field_validator("recipient_id")
    @classmethod
    def validate_recipient_id(cls, v: str) -> str:
        try:
            UUID(v)
        except ValueError:
            raise ValueError("Invalid recipient ID format, must be UUID")
        return v


class NotificationMarkReadRequest(BaseModel):
    """Request to mark a notification as read."""

    notification_id: str = Field(..., min_length=1)


class NotificationMarkAllReadRequest(BaseModel):
    """Request to mark all notifications as read."""

    pass


class PingRequest(BaseModel):
    """Ping/heartbeat request."""

    timestamp: Optional[datetime] = None


# =============================================================================
# Response Models (Server -> Client)
# =============================================================================


class ConnectedResponse(BaseModel):
    """Response sent on successful connection."""

    user_id: str
    email: str
    role: str
    status: UserStatus
    connection_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SubscribedResponse(BaseModel):
    """Response confirming subscription."""

    channel: Channel
    filters: Optional[Dict[str, Any]] = None


class UnsubscribedResponse(BaseModel):
    """Response confirming unsubscription."""

    channel: Channel


class UserResponse(BaseModel):
    """User profile data response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: str


class UserUpdatedResponse(BaseModel):
    """Response for user profile update broadcast."""

    user_id: str
    updates: Dict[str, Any]
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class UserDeletedResponse(BaseModel):
    """Response for user deletion."""

    user_id: str
    message: str = "User deleted successfully"


class UserStatusChangedResponse(BaseModel):
    """Response for user status change broadcast."""

    user_id: str
    status: UserStatus
    previous_status: Optional[UserStatus] = None


class MessageReceiveResponse(BaseModel):
    """Response for received chat message."""

    message_id: str
    sender_id: str
    recipient_id: str
    message: str
    message_type: str
    conversation_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    read: bool = False


class MessageSentResponse(BaseModel):
    """Response confirming message was sent."""

    message_id: str
    recipient_id: str
    status: str = "sent"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TypingStartedResponse(BaseModel):
    """Response for typing started indicator."""

    user_id: str
    conversation_id: Optional[str] = None


class TypingStoppedResponse(BaseModel):
    """Response for typing stopped indicator."""

    user_id: str
    conversation_id: Optional[str] = None


class NotificationResponse(BaseModel):
    """Response for new notification."""

    id: str
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class NotificationMarkedReadResponse(BaseModel):
    """Response for notification marked as read."""

    notification_id: str
    read: bool = True


class NotificationAllMarkedReadResponse(BaseModel):
    """Response for all notifications marked as read."""

    count: int
    message: str = "All notifications marked as read"


class ErrorResponse(BaseModel):
    """Error response sent to client."""

    code: ErrorCodes
    message: str
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class PongResponse(BaseModel):
    """Pong/heartbeat response."""

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# Event Payload Wrappers
# =============================================================================


class EventPayload(BaseModel):
    """Generic event payload wrapper for parsing incoming messages."""

    event: str
    data: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def validate_event(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "event" not in data:
                raise ValueError("Missing 'event' field")
            if "data" not in data:
                data["data"] = {}
        return data


# =============================================================================
# Redis Pub/Sub Messages
# =============================================================================


class RedisBroadcastMessage(BaseModel):
    """Message format for Redis pub/sub broadcast."""

    event: str
    data: Dict[str, Any]
    room: Optional[str] = None  # Target room, None for broadcast
    user_id: Optional[str] = None  # Target user, None for broadcast
    exclude_connections: Optional[List[str]] = None  # Connection IDs to exclude
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RedisUserMessage(BaseModel):
    """Message format for Redis user-specific messages."""

    user_id: str
    event: str
    data: Dict[str, Any]
    exclude_connections: Optional[List[str]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
