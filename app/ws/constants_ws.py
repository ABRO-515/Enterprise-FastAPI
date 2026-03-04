"""WebSocket constants: event names, close codes, allowed channels, and configuration."""

from enum import Enum


class Events(str, Enum):
    """WebSocket event names for client-server communication."""

    # Client -> Server events
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    USER_GET = "user:get"
    USER_UPDATE = "user:update"
    USER_STATUS = "user:status"
    USER_DELETE = "user:delete"
    MESSAGE_SEND = "message:send"
    TYPING_START = "typing:start"
    TYPING_STOP = "typing:stop"
    NOTIFICATION_MARK_READ = "notification:mark-read"
    NOTIFICATION_MARK_ALL_READ = "notification:mark-all-read"
    PING = "ping"

    # Server -> Client events
    CONNECTED = "connected"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    USER_UPDATED = "user:updated"
    USER_DELETED = "user:deleted"
    USER_STATUS_CHANGED = "user:status-changed"
    MESSAGE_RECEIVE = "message:receive"
    MESSAGE_SENT = "message:sent"
    TYPING_STARTED = "typing:started"
    TYPING_STOPPED = "typing:stopped"
    NOTIFICATION_NEW = "notification:new"
    NOTIFICATION_MARKED_READ = "notification:marked-read"
    NOTIFICATION_ALL_MARKED_READ = "notification:all-marked-read"
    ERROR = "error"
    PONG = "pong"


class Channel(str, Enum):
    """Allowed subscription channels."""

    USERS = "users"
    NOTIFICATIONS = "notifications"
    CHAT = "chat"


class UserStatus(str, Enum):
    """Valid user online statuses."""

    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


class CloseCodes(int, Enum):
    """WebSocket close codes for application-level errors."""

    NORMAL = 1000
    GOING_AWAY = 1001
    UNAUTHORIZED = 4001
    FORBIDDEN = 4002
    RATE_LIMITED = 4003
    INVALID_MESSAGE = 4004
    SERVER_ERROR = 4500


class ErrorCodes(str, Enum):
    """Error codes for WebSocket error events."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_CHANNEL = "INVALID_CHANNEL"
    INVALID_EVENT = "INVALID_EVENT"


# Allowed channels for subscription
ALLOWED_CHANNELS = [channel.value for channel in Channel]

# Valid user statuses
VALID_USER_STATUSES = [status.value for status in UserStatus]

# Rate limits (events per minute per user)
DEFAULT_RATE_LIMIT = 100
RATE_LIMIT_WINDOW = 60  # seconds

# WebSocket configuration
WS_HEARTBEAT_INTERVAL = 30  # seconds
WS_CONNECTION_TIMEOUT = 300  # seconds (5 minutes idle)
WS_MAX_MESSAGE_SIZE = 65536  # 64KB

# Redis pub/sub channels
REDIS_BROADCAST_CHANNEL = "websocket:broadcast"
REDIS_USER_CHANNEL_PREFIX = "websocket:user:"
REDIS_ROOM_CHANNEL_PREFIX = "websocket:room:"
