"""WebSocket Documentation and Testing Interface.

Provides a FastAPI-style documentation UI for WebSocket endpoints
with interactive testing capabilities.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.ws.constants_ws import Events


router = APIRouter(tags=["websocket-docs"])


# =============================================================================
# WebSocket Endpoint Documentation Data
# =============================================================================

WEBSOCKET_ENDPOINTS: List[Dict[str, Any]] = [
    {
        "id": "main",
        "path": "/ws/",
        "name": "Main WebSocket",
        "description": "Primary WebSocket endpoint for real-time user operations, notifications, and status updates.",
        "auth_required": True,
        "auth_method": "JWT Token",
        "auth_locations": [
            {
                "name": "Query Parameter",
                "example": "?token=YOUR_JWT_TOKEN",
                "description": "Pass token as query parameter"
            },
            {
                "name": "Authorization Header",
                "example": "Authorization: Bearer YOUR_JWT_TOKEN",
                "description": "Standard Bearer token in headers"
            },
            {
                "name": "Sec-WebSocket-Protocol",
                "example": "Sec-WebSocket-Protocol: token.YOUR_JWT_TOKEN",
                "description": "Token in WebSocket protocol header"
            }
        ],
        "connection_params": [
            {
                "name": "token",
                "type": "string",
                "required": True,
                "description": "JWT authentication token"
            }
        ],
        "client_events": [
            {
                "event": "subscribe",
                "description": "Subscribe to a channel with optional filters",
                "payload": {"event": "subscribe", "data": {"channel": "users", "filters": {"user_id": "uuid"}}},
                "response": {"event": "subscribed", "data": {"channel": "users", "filters": {"user_id": "uuid"}}}
            },
            {
                "event": "unsubscribe",
                "description": "Unsubscribe from a channel",
                "payload": {"event": "unsubscribe", "data": {"channel": "users"}},
                "response": {"event": "unsubscribed", "data": {"channel": "users"}}
            },
            {
                "event": "user:get",
                "description": "Fetch user profile by ID",
                "payload": {"event": "user:get", "data": {"user_id": "uuid"}},
                "response": {"event": "user:get", "data": {"id": "uuid", "email": "user@example.com", "role": "user"}}
            },
            {
                "event": "user:update",
                "description": "Update current user profile",
                "payload": {"event": "user:update", "data": {"full_name": "New Name"}},
                "response": {"event": "user:updated", "data": {"user_id": "uuid", "updates": {"full_name": "New Name"}}}
            },
            {
                "event": "user:status",
                "description": "Update user online status",
                "payload": {"event": "user:status", "data": {"status": "online"}},
                "response": {"event": "user:status-changed", "data": {"user_id": "uuid", "status": "online"}}
            },
            {
                "event": "ping",
                "description": "Heartbeat ping to keep connection alive",
                "payload": {"event": "ping", "data": {}},
                "response": {"event": "pong", "data": {"timestamp": "2024-01-01T00:00:00Z"}}
            }
        ],
        "server_events": [
            {
                "event": "connected",
                "description": "Sent on successful connection with user info",
                "payload": {"event": "connected", "data": {"user_id": "uuid", "email": "user@example.com", "role": "user", "status": "online", "connection_id": "conn_xxx"}}
            },
            {
                "event": "error",
                "description": "Error response for failed operations",
                "payload": {"event": "error", "data": {"code": "VALIDATION_ERROR", "message": "Invalid input", "details": {}}}
            },
            {
                "event": "user:status-changed",
                "description": "Broadcast when user status changes",
                "payload": {"event": "user:status-changed", "data": {"user_id": "uuid", "status": "away"}}
            }
        ]
    },
    {
        "id": "chat",
        "path": "/ws/chat",
        "name": "Chat WebSocket",
        "description": "WebSocket endpoint dedicated to real-time chat messaging and typing indicators.",
        "auth_required": True,
        "auth_method": "JWT Token",
        "auth_locations": [
            {
                "name": "Query Parameter",
                "example": "?token=YOUR_JWT_TOKEN",
                "description": "Pass token as query parameter"
            }
        ],
        "connection_params": [
            {
                "name": "token",
                "type": "string",
                "required": True,
                "description": "JWT authentication token"
            }
        ],
        "client_events": [
            {
                "event": "message:send",
                "description": "Send a chat message to another user",
                "payload": {"event": "message:send", "data": {"recipient_id": "uuid", "message": "Hello!", "message_type": "text"}},
                "response": {"event": "message:sent", "data": {"message_id": "uuid", "recipient_id": "uuid", "status": "sent"}}
            },
            {
                "event": "typing:start",
                "description": "Notify recipient that sender is typing",
                "payload": {"event": "typing:start", "data": {"recipient_id": "uuid", "conversation_id": "uuid"}},
                "response": None
            },
            {
                "event": "typing:stop",
                "description": "Notify recipient that sender stopped typing",
                "payload": {"event": "typing:stop", "data": {"recipient_id": "uuid", "conversation_id": "uuid"}},
                "response": None
            },
            {
                "event": "subscribe",
                "description": "Subscribe to chat channel for a conversation",
                "payload": {"event": "subscribe", "data": {"channel": "chat", "filters": {"conversation_id": "uuid"}}},
                "response": {"event": "subscribed", "data": {"channel": "chat", "filters": {"conversation_id": "uuid"}}}
            }
        ],
        "server_events": [
            {
                "event": "message:receive",
                "description": "Receive a chat message from another user",
                "payload": {"event": "message:receive", "data": {"message_id": "uuid", "sender_id": "uuid", "recipient_id": "uuid", "message": "Hello!", "message_type": "text", "timestamp": "2024-01-01T00:00:00Z"}}
            },
            {
                "event": "typing:started",
                "description": "Notification that someone started typing",
                "payload": {"event": "typing:started", "data": {"user_id": "uuid", "conversation_id": "uuid"}}
            },
            {
                "event": "typing:stopped",
                "description": "Notification that someone stopped typing",
                "payload": {"event": "typing:stopped", "data": {"user_id": "uuid", "conversation_id": "uuid"}}
            }
        ]
    },
    {
        "id": "notifications",
        "path": "/ws/notifications",
        "name": "Notifications WebSocket",
        "description": "WebSocket endpoint for receiving real-time notifications and managing notification status.",
        "auth_required": True,
        "auth_method": "JWT Token",
        "auth_locations": [
            {
                "name": "Query Parameter",
                "example": "?token=YOUR_JWT_TOKEN",
                "description": "Pass token as query parameter"
            }
        ],
        "connection_params": [
            {
                "name": "token",
                "type": "string",
                "required": True,
                "description": "JWT authentication token"
            }
        ],
        "client_events": [
            {
                "event": "notification:mark-read",
                "description": "Mark a specific notification as read",
                "payload": {"event": "notification:mark-read", "data": {"notification_id": "uuid"}},
                "response": {"event": "notification:marked-read", "data": {"notification_id": "uuid", "read": True}}
            },
            {
                "event": "notification:mark-all-read",
                "description": "Mark all notifications as read",
                "payload": {"event": "notification:mark-all-read", "data": {}},
                "response": {"event": "notification:all-marked-read", "data": {"count": 5, "message": "All notifications marked as read"}}
            }
        ],
        "server_events": [
            {
                "event": "notification:new",
                "description": "New notification received",
                "payload": {"event": "notification:new", "data": {"id": "uuid", "user_id": "uuid", "type": "message", "title": "New Message", "message": "You have a new message", "read": False, "created_at": "2024-01-01T00:00:00Z"}}
            }
        ]
    }
]

# Channel documentation
CHANNELS = [
    {"name": "users", "description": "User-related events and status updates"},
    {"name": "chat", "description": "Chat messaging and typing indicators"},
    {"name": "notifications", "description": "Real-time notifications"}
]

# User statuses
USER_STATUSES = ["online", "away", "busy", "offline"]

# Error codes
ERROR_CODES = [
    {"code": "VALIDATION_ERROR", "description": "Invalid input data"},
    {"code": "UNAUTHORIZED", "description": "Authentication required or invalid token"},
    {"code": "FORBIDDEN", "description": "Insufficient permissions"},
    {"code": "NOT_FOUND", "description": "Resource not found"},
    {"code": "RATE_LIMITED", "description": "Too many requests"},
    {"code": "INTERNAL_ERROR", "description": "Server error"},
    {"code": "INVALID_CHANNEL", "description": "Unknown channel name"},
    {"code": "INVALID_EVENT", "description": "Unknown event type"}
]


# =============================================================================
# Documentation Routes
# =============================================================================

@router.get("/", response_class=HTMLResponse)
async def websocket_docs(request: Request):
    """Render the WebSocket documentation interface."""
    return HTMLResponse(content=get_docs_html())


def get_docs_html() -> str:
    """Generate the complete HTML for WebSocket documentation."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Documentation - Enterprise FastAPI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
    <style>
        {get_css()}
    </style>
</head>
<body>
    <div class="layout">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="sidebar-header">
                <div class="logo">
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                        <path d="M16 2L2 9L16 16L30 9L16 2Z" fill="#059669"/>
                        <path d="M2 23L16 30L30 23V16L16 23L2 16V23Z" fill="#10b981"/>
                        <path d="M16 16V30" stroke="#fff" stroke-width="2"/>
                    </svg>
                    <span>WebSocket Docs</span>
                </div>
                <div class="version">Enterprise FastAPI</div>
            </div>
            
            <nav class="sidebar-nav">
                <div class="nav-section">
                    <div class="nav-section-title">Overview</div>
                    <a href="#introduction" class="nav-link active" data-section="introduction">Introduction</a>
                    <a href="#authentication" class="nav-link" data-section="authentication">Authentication</a>
                    <a href="#events" class="nav-link" data-section="events">Events Reference</a>
                    <a href="#errors" class="nav-link" data-section="errors">Error Codes</a>
                </div>
                
                <div class="nav-section">
                    <div class="nav-section-title">Endpoints</div>
                    {generate_sidebar_links()}
                </div>
                
                <div class="nav-section">
                    <div class="nav-section-title">Testing</div>
                    <a href="#testing" class="nav-link" data-section="testing">Interactive Testing</a>
                </div>
            </nav>
            
            <div class="sidebar-footer">
                <button id="theme-toggle" class="theme-toggle" title="Toggle dark mode">
                    <svg class="icon-sun" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="5"/>
                        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                    </svg>
                    <svg class="icon-moon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                </button>
            </div>
        </aside>
        
        <!-- Main Content -->
        <main class="main-content">
            <div class="content-container">
                <!-- Introduction Section -->
                <section id="introduction" class="doc-section">
                    <h1 class="section-title">WebSocket Documentation</h1>
                    <p class="section-description">
                        Real-time bidirectional communication using WebSocket protocol. 
                        This documentation provides comprehensive information about available endpoints,
                        message formats, and interactive testing capabilities.
                    </p>
                    
                    <div class="info-card">
                        <h3>Base URL</h3>
                        <code class="inline-code" id="base-url">ws://localhost:8000</code>
                        <button class="copy-btn" onclick="copyBaseUrl()">Copy</button>
                    </div>
                    
                    <div class="feature-grid">
                        <div class="feature-card">
                            <div class="feature-icon">🔒</div>
                            <h4>JWT Authentication</h4>
                            <p>Secure connections with JWT token authentication</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">📡</div>
                            <h4>Real-time Events</h4>
                            <p>Instant bidirectional communication</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">🏠</div>
                            <h4>Room Broadcasting</h4>
                            <p>Targeted message delivery to groups</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">⚡</div>
                            <h4>Rate Limiting</h4>
                            <p>100 events per minute per user</p>
                        </div>
                    </div>
                </section>
                
                <!-- Authentication Section -->
                <section id="authentication" class="doc-section">
                    <h2 class="section-title">Authentication</h2>
                    <p class="section-description">
                        All WebSocket endpoints require JWT authentication. Tokens can be provided in three ways:
                    </p>
                    
                    <div class="auth-methods">
                        <div class="auth-method">
                            <div class="auth-method-header">
                                <span class="method-badge get">Query Parameter</span>
                                <span class="auth-method-name">Token in URL</span>
                            </div>
                            <div class="code-block">
                                <pre><code class="language-json">ws://localhost:8000/ws/?token=YOUR_JWT_TOKEN</code></pre>
                            </div>
                        </div>
                        
                        <div class="auth-method">
                            <div class="auth-method-header">
                                <span class="method-badge post">Header</span>
                                <span class="auth-method-name">Authorization Bearer</span>
                            </div>
                            <div class="code-block">
                                <pre><code class="language-json">Authorization: Bearer YOUR_JWT_TOKEN</code></pre>
                            </div>
                        </div>
                        
                        <div class="auth-method">
                            <div class="auth-method-header">
                                <span class="method-badge ws">Protocol</span>
                                <span class="auth-method-name">Sec-WebSocket-Protocol</span>
                            </div>
                            <div class="code-block">
                                <pre><code class="language-json">Sec-WebSocket-Protocol: token.YOUR_JWT_TOKEN</code></pre>
                            </div>
                        </div>
                    </div>
                    
                    <div class="warning-card">
                        <strong>⚠️ Security Note:</strong> Query parameter authentication may expose tokens in server logs. 
                        Use Authorization header for production environments.
                    </div>
                </section>
                
                <!-- Events Reference Section -->
                <section id="events" class="doc-section">
                    <h2 class="section-title">Events Reference</h2>
                    <p class="section-description">
                        WebSocket communication uses event-based messaging. Each message contains an <code class="inline-code">event</code> 
                        field and a <code class="inline-code">data</code> object.
                    </p>
                    
                    <h3>Message Format</h3>
                    <div class="code-block">
                        <pre><code class="language-json">{{
  "event": "event:name",
  "data": {{
    // Event-specific data
  }}
}}</code></pre>
                    </div>
                    
                    <h3>Available Channels</h3>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Channel</th>
                                    <th>Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                {generate_channels_table()}
                            </tbody>
                        </table>
                    </div>
                    
                    <h3>User Statuses</h3>
                    <div class="status-badges">
                        {generate_status_badges()}
                    </div>
                </section>
                
                <!-- Error Codes Section -->
                <section id="errors" class="doc-section">
                    <h2 class="section-title">Error Codes</h2>
                    <p class="section-description">
                        Error responses include a code and descriptive message for debugging.
                    </p>
                    
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Code</th>
                                    <th>Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                {generate_error_codes_table()}
                            </tbody>
                        </table>
                    </div>
                    
                    <h3>Error Response Format</h3>
                    <div class="code-block">
                        <pre><code class="language-json">{{
  "event": "error",
  "data": {{
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {{
      "errors": [
        {{"field": "user_id", "message": "Invalid UUID format"}}
      ]
    }}
  }},
  "timestamp": "2024-01-01T00:00:00Z"
}}</code></pre>
                    </div>
                </section>
                
                <!-- Endpoint Sections -->
                {generate_endpoint_sections()}
                
                <!-- Testing Section -->
                <section id="testing" class="doc-section">
                    <h2 class="section-title">Interactive Testing</h2>
                    <p class="section-description">
                        Test WebSocket connections directly from the browser. Connect to any endpoint,
                        send messages, and view real-time responses.
                    </p>
                    
                    <div class="testing-panel">
                        <div class="testing-header">
                            <div class="connection-controls">
                                <div class="input-group">
                                    <label>Endpoint</label>
                                    <select id="ws-endpoint" class="select-input">
                                        {generate_endpoint_options()}
                                    </select>
                                </div>
                                
                                <div class="input-group">
                                    <label>JWT Token</label>
                                    <input type="text" id="ws-token" class="text-input" placeholder="Enter your JWT token">
                                </div>
                                
                                <div class="button-group">
                                    <button id="connect-btn" class="btn btn-primary" onclick="toggleConnection()">
                                        <span class="btn-icon">🔗</span>
                                        Connect
                                    </button>
                                    <button id="disconnect-btn" class="btn btn-danger" onclick="disconnect()" disabled>
                                        <span class="btn-icon">⛔</span>
                                        Disconnect
                                    </button>
                                </div>
                                
                                <div class="connection-status">
                                    <span class="status-indicator" id="status-indicator"></span>
                                    <span id="status-text">Disconnected</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="testing-body">
                            <div class="testing-left">
                                <div class="panel-header">
                                    <h4>Send Message</h4>
                                </div>
                                <div class="message-composer">
                                    <div class="input-group">
                                        <label>Event</label>
                                        <select id="event-select" class="select-input" onchange="updatePayloadTemplate()">
                                            <option value="">Select an event...</option>
                                        </select>
                                    </div>
                                    
                                    <div class="input-group">
                                        <label>JSON Payload</label>
                                        <textarea id="message-input" class="textarea-input" rows="8" placeholder='{{"event": "ping", "data": {{}}}}'></textarea>
                                    </div>
                                    
                                    <div class="button-group">
                                        <button class="btn btn-secondary" onclick="formatJson()">
                                            <span class="btn-icon">✨</span>
                                            Format JSON
                                        </button>
                                        <button class="btn btn-primary" onclick="sendMessage()" id="send-btn" disabled>
                                            <span class="btn-icon">📤</span>
                                            Send
                                        </button>
                                    </div>
                                </div>
                                
                                <div class="quick-actions">
                                    <h5>Quick Actions</h5>
                                    <div class="quick-buttons">
                                        <button class="btn btn-sm" onclick="sendPing()">Ping</button>
                                        <button class="btn btn-sm" onclick="sendSubscribe()">Subscribe</button>
                                        <button class="btn btn-sm" onclick="sendStatusUpdate()">Set Status</button>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="testing-right">
                                <div class="panel-header">
                                    <h4>Message Log</h4>
                                    <div class="log-controls">
                                        <button class="btn btn-sm btn-icon-only" onclick="clearLogs()" title="Clear logs">
                                            🗑️
                                        </button>
                                        <label class="checkbox-label">
                                            <input type="checkbox" id="auto-scroll" checked>
                                            Auto-scroll
                                        </label>
                                    </div>
                                </div>
                                <div class="message-log" id="message-log">
                                    <div class="log-empty">Connect to a WebSocket to see messages</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </main>
    </div>
    
    <script>
        {get_javascript()}
    </script>
</body>
</html>'''


def generate_sidebar_links() -> str:
    """Generate sidebar navigation links for endpoints."""
    links = []
    for endpoint in WEBSOCKET_ENDPOINTS:
        links.append(f'''<a href="#endpoint-{endpoint['id']}" class="nav-link" data-section="endpoint-{endpoint['id']}">
            <span class="endpoint-indicator"></span>
            {endpoint['name']}
        </a>''')
    return '\n'.join(links)


def generate_endpoint_sections() -> str:
    """Generate documentation sections for each endpoint."""
    sections = []
    for endpoint in WEBSOCKET_ENDPOINTS:
        sections.append(generate_endpoint_section(endpoint))
    return '\n'.join(sections)


def generate_endpoint_section(endpoint: Dict[str, Any]) -> str:
    """Generate a single endpoint documentation section."""
    client_events_html = generate_events_table(endpoint.get('client_events', []), 'client')
    server_events_html = generate_events_table(endpoint.get('server_events', []), 'server')
    
    return f'''
    <section id="endpoint-{endpoint['id']}" class="doc-section endpoint-section">
        <div class="endpoint-header">
            <h2 class="section-title">{endpoint['name']}</h2>
            <div class="endpoint-badges">
                <span class="badge badge-ws">WebSocket</span>
                {f'<span class="badge badge-auth">Auth Required</span>' if endpoint.get('auth_required') else ''}
            </div>
        </div>
        
        <p class="section-description">{endpoint['description']}</p>
        
        <div class="endpoint-url-box">
            <code class="endpoint-url">{endpoint['path']}</code>
            <button class="copy-btn" onclick="copyEndpointUrl('{endpoint['path']}')">Copy URL</button>
        </div>
        
        <h3>Connection Parameters</h3>
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Required</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {generate_params_table(endpoint.get('connection_params', []))}
                </tbody>
            </table>
        </div>
        
        <h3>Client Events <span class="direction-hint">(Client → Server)</span></h3>
        {client_events_html}
        
        <h3>Server Events <span class="direction-hint">(Server → Client)</span></h3>
        {server_events_html}
    </section>
'''


def generate_events_table(events: List[Dict[str, Any]], direction: str) -> str:
    """Generate events documentation table."""
    if not events:
        return '<p class="no-events">No events defined.</p>'
    
    rows = []
    for event in events:
        payload_json = json.dumps(event.get('payload', {}), indent=2)
        response_json = json.dumps(event.get('response', {}), indent=2) if event.get('response') else None
        
        response_html = ''
        if response_json:
            response_html = f'''
            <div class="event-response">
                <strong>Response:</strong>
                <pre><code class="language-json">{response_json}</code></pre>
            </div>'''
        
        rows.append(f'''
        <div class="event-card">
            <div class="event-header">
                <code class="event-name">{event['event']}</code>
                <span class="event-direction {direction}">{'↑' if direction == 'client' else '↓'}</span>
            </div>
            <p class="event-description">{event['description']}</p>
            <div class="event-payload">
                <strong>Example Payload:</strong>
                <pre><code class="language-json">{payload_json}</code></pre>
            </div>
            {response_html}
        </div>''')
    
    return '\n'.join(rows)


def generate_params_table(params: List[Dict[str, Any]]) -> str:
    """Generate connection parameters table rows."""
    rows = []
    for param in params:
        required = '<span class="required">Yes</span>' if param.get('required') else 'No'
        rows.append(f'''
        <tr>
            <td><code>{param['name']}</code></td>
            <td>{param['type']}</td>
            <td>{required}</td>
            <td>{param['description']}</td>
        </tr>''')
    return '\n'.join(rows)


def generate_channels_table() -> str:
    """Generate channels table rows."""
    rows = []
    for channel in CHANNELS:
        rows.append(f'''
        <tr>
            <td><code>{channel['name']}</code></td>
            <td>{channel['description']}</td>
        </tr>''')
    return '\n'.join(rows)


def generate_status_badges() -> str:
    """Generate user status badges."""
    badges = []
    for status in USER_STATUSES:
        badges.append(f'<span class="status-badge status-{status}">{status}</span>')
    return '\n'.join(badges)


def generate_error_codes_table() -> str:
    """Generate error codes table rows."""
    rows = []
    for error in ERROR_CODES:
        rows.append(f'''
        <tr>
            <td><code class="error-code">{error['code']}</code></td>
            <td>{error['description']}</td>
        </tr>''')
    return '\n'.join(rows)


def generate_endpoint_options() -> str:
    """Generate endpoint select options."""
    options = []
    for endpoint in WEBSOCKET_ENDPOINTS:
        options.append(f'<option value="{endpoint["path"]}">{endpoint["name"]} ({endpoint["path"]})</option>')
    return '\n'.join(options)


def get_css() -> str:
    """Return CSS styles for the documentation interface."""
    return '''
    /* CSS Variables */
    :root {
        --primary-color: #059669;
        --primary-hover: #047857;
        --primary-light: #d1fae5;
        --secondary-color: #6366f1;
        --danger-color: #ef4444;
        --danger-hover: #dc2626;
        --warning-color: #f59e0b;
        --warning-bg: #fef3c7;
        
        --bg-sidebar: #1f2937;
        --bg-sidebar-hover: #374151;
        --bg-main: #ffffff;
        --bg-main-dark: #111827;
        --bg-card: #f9fafb;
        --bg-card-dark: #1f2937;
        
        --text-primary: #111827;
        --text-primary-dark: #f9fafb;
        --text-secondary: #6b7280;
        --text-secondary-dark: #9ca3af;
        --text-sidebar: #e5e7eb;
        
        --border-color: #e5e7eb;
        --border-color-dark: #374151;
        
        --code-bg: #1e293b;
        --code-text: #e2e8f0;
        
        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 12px;
        
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        
        --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
    }
    
    /* Dark Mode */
    [data-theme="dark"] {
        --bg-main: var(--bg-main-dark);
        --bg-card: var(--bg-card-dark);
        --text-primary: var(--text-primary-dark);
        --text-secondary: var(--text-secondary-dark);
        --border-color: var(--border-color-dark);
    }
    
    /* Reset & Base */
    *, *::before, *::after {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }
    
    html {
        scroll-behavior: smooth;
    }
    
    body {
        font-family: var(--font-sans);
        background: var(--bg-main);
        color: var(--text-primary);
        line-height: 1.6;
        min-height: 100vh;
    }
    
    /* Layout */
    .layout {
        display: flex;
        min-height: 100vh;
    }
    
    /* Sidebar */
    .sidebar {
        width: 280px;
        background: var(--bg-sidebar);
        color: var(--text-sidebar);
        position: fixed;
        top: 0;
        left: 0;
        height: 100vh;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        z-index: 100;
    }
    
    .sidebar-header {
        padding: 20px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .logo {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 18px;
        font-weight: 600;
        color: #fff;
    }
    
    .version {
        font-size: 12px;
        color: var(--text-secondary-dark);
        margin-top: 4px;
    }
    
    .sidebar-nav {
        flex: 1;
        padding: 16px 0;
    }
    
    .nav-section {
        margin-bottom: 24px;
    }
    
    .nav-section-title {
        padding: 8px 20px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary-dark);
    }
    
    .nav-link {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 20px;
        color: var(--text-sidebar);
        text-decoration: none;
        font-size: 14px;
        transition: all 0.15s;
    }
    
    .nav-link:hover {
        background: var(--bg-sidebar-hover);
    }
    
    .nav-link.active {
        background: var(--primary-color);
        color: #fff;
    }
    
    .endpoint-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--primary-color);
    }
    
    .sidebar-footer {
        padding: 16px 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .theme-toggle {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        background: var(--bg-sidebar-hover);
        border: none;
        border-radius: var(--radius-md);
        color: var(--text-sidebar);
        cursor: pointer;
        transition: background 0.15s;
    }
    
    .theme-toggle:hover {
        background: var(--primary-color);
    }
    
    .icon-moon { display: none; }
    [data-theme="dark"] .icon-sun { display: none; }
    [data-theme="dark"] .icon-moon { display: block; }
    
    /* Main Content */
    .main-content {
        flex: 1;
        margin-left: 280px;
        background: var(--bg-main);
    }
    
    .content-container {
        max-width: 1000px;
        margin: 0 auto;
        padding: 40px;
    }
    
    /* Sections */
    .doc-section {
        margin-bottom: 60px;
        scroll-margin-top: 20px;
    }
    
    .section-title {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
    }
    
    .section-description {
        font-size: 16px;
        color: var(--text-secondary);
        margin-bottom: 24px;
    }
    
    /* Info Card */
    .info-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        padding: 20px;
        margin-bottom: 24px;
    }
    
    .info-card h3 {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 8px;
    }
    
    /* Feature Grid */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-top: 24px;
    }
    
    .feature-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        padding: 20px;
        text-align: center;
    }
    
    .feature-icon {
        font-size: 32px;
        margin-bottom: 12px;
    }
    
    .feature-card h4 {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .feature-card p {
        font-size: 14px;
        color: var(--text-secondary);
    }
    
    /* Auth Methods */
    .auth-methods {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 24px;
    }
    
    .auth-method {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        overflow: hidden;
    }
    
    .auth-method-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: var(--bg-main);
        border-bottom: 1px solid var(--border-color);
    }
    
    .method-badge {
        padding: 4px 10px;
        border-radius: var(--radius-sm);
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .method-badge.get { background: var(--primary-light); color: var(--primary-color); }
    .method-badge.post { background: #dbeafe; color: #2563eb; }
    .method-badge.ws { background: #fef3c7; color: #d97706; }
    
    .auth-method-name {
        font-weight: 500;
    }
    
    /* Code Blocks */
    .code-block {
        background: var(--code-bg);
        border-radius: var(--radius-md);
        overflow: hidden;
        margin: 16px 0;
    }
    
    .code-block pre {
        margin: 0;
        padding: 16px;
        overflow-x: auto;
    }
    
    .code-block code {
        font-family: var(--font-mono);
        font-size: 13px;
        color: var(--code-text);
    }
    
    .inline-code {
        font-family: var(--font-mono);
        font-size: 13px;
        background: var(--bg-card);
        padding: 2px 6px;
        border-radius: var(--radius-sm);
        border: 1px solid var(--border-color);
    }
    
    /* Warning Card */
    .warning-card {
        background: var(--warning-bg);
        border: 1px solid var(--warning-color);
        border-radius: var(--radius-md);
        padding: 16px;
        font-size: 14px;
    }
    
    .warning-card strong {
        color: #92400e;
    }
    
    /* Tables */
    .table-container {
        overflow-x: auto;
        margin: 16px 0;
    }
    
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    
    .data-table th,
    .data-table td {
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid var(--border-color);
    }
    
    .data-table th {
        background: var(--bg-card);
        font-weight: 600;
        color: var(--text-secondary);
    }
    
    .data-table code {
        font-family: var(--font-mono);
        font-size: 13px;
        background: var(--bg-card);
        padding: 2px 6px;
        border-radius: var(--radius-sm);
    }
    
    .required {
        color: var(--danger-color);
        font-weight: 600;
    }
    
    /* Status Badges */
    .status-badges {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin: 16px 0;
    }
    
    .status-badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
    }
    
    .status-online { background: #d1fae5; color: #059669; }
    .status-away { background: #fef3c7; color: #d97706; }
    .status-busy { background: #fee2e2; color: #dc2626; }
    .status-offline { background: #e5e7eb; color: #6b7280; }
    
    /* Error Code */
    .error-code {
        color: var(--danger-color);
    }
    
    /* Endpoint Section */
    .endpoint-section {
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        padding: 24px;
        background: var(--bg-main);
    }
    
    .endpoint-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
    }
    
    .endpoint-badges {
        display: flex;
        gap: 8px;
    }
    
    .badge {
        padding: 4px 10px;
        border-radius: var(--radius-sm);
        font-size: 12px;
        font-weight: 600;
    }
    
    .badge-ws { background: #dbeafe; color: #2563eb; }
    .badge-auth { background: #fee2e2; color: #dc2626; }
    
    .endpoint-url-box {
        display: flex;
        align-items: center;
        gap: 12px;
        background: var(--bg-card);
        padding: 12px 16px;
        border-radius: var(--radius-md);
        margin-bottom: 24px;
    }
    
    .endpoint-url {
        font-family: var(--font-mono);
        font-size: 16px;
        font-weight: 500;
        color: var(--primary-color);
    }
    
    .copy-btn {
        padding: 6px 12px;
        background: transparent;
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        font-size: 12px;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.15s;
    }
    
    .copy-btn:hover {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: #fff;
    }
    
    /* Event Cards */
    .event-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        padding: 16px;
        margin-bottom: 16px;
    }
    
    .event-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    
    .event-name {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-color);
    }
    
    .event-direction {
        font-size: 16px;
    }
    
    .event-direction.client { color: var(--secondary-color); }
    .event-direction.server { color: var(--primary-color); }
    
    .event-description {
        font-size: 14px;
        color: var(--text-secondary);
        margin-bottom: 12px;
    }
    
    .event-payload,
    .event-response {
        margin-top: 12px;
    }
    
    .event-payload strong,
    .event-response strong {
        display: block;
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 8px;
    }
    
    .event-card .code-block {
        margin: 0;
    }
    
    .direction-hint {
        font-size: 14px;
        font-weight: 400;
        color: var(--text-secondary);
    }
    
    .no-events {
        color: var(--text-secondary);
        font-style: italic;
    }
    
    /* Testing Panel */
    .testing-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        overflow: hidden;
    }
    
    .testing-header {
        background: var(--bg-main);
        border-bottom: 1px solid var(--border-color);
        padding: 20px;
    }
    
    .connection-controls {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        align-items: flex-end;
    }
    
    .input-group {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .input-group label {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-secondary);
    }
    
    .text-input,
    .select-input,
    .textarea-input {
        font-family: var(--font-sans);
        font-size: 14px;
        padding: 10px 12px;
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        background: var(--bg-main);
        color: var(--text-primary);
        transition: border-color 0.15s;
    }
    
    .text-input:focus,
    .select-input:focus,
    .textarea-input:focus {
        outline: none;
        border-color: var(--primary-color);
    }
    
    .text-input {
        min-width: 300px;
    }
    
    .textarea-input {
        font-family: var(--font-mono);
        font-size: 13px;
        resize: vertical;
    }
    
    .button-group {
        display: flex;
        gap: 8px;
    }
    
    .btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 10px 16px;
        font-family: var(--font-sans);
        font-size: 14px;
        font-weight: 500;
        border: none;
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all 0.15s;
    }
    
    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    
    .btn-primary {
        background: var(--primary-color);
        color: #fff;
    }
    
    .btn-primary:hover:not(:disabled) {
        background: var(--primary-hover);
    }
    
    .btn-secondary {
        background: var(--bg-main);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }
    
    .btn-secondary:hover:not(:disabled) {
        background: var(--bg-card);
    }
    
    .btn-danger {
        background: var(--danger-color);
        color: #fff;
    }
    
    .btn-danger:hover:not(:disabled) {
        background: var(--danger-hover);
    }
    
    .btn-sm {
        padding: 6px 12px;
        font-size: 13px;
    }
    
    .btn-icon-only {
        padding: 6px 10px;
    }
    
    .connection-status {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 16px;
        background: var(--bg-card);
        border-radius: var(--radius-md);
    }
    
    .status-indicator {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--danger-color);
    }
    
    .status-indicator.connected {
        background: var(--primary-color);
        animation: pulse 2s infinite;
    }
    
    .status-indicator.connecting {
        background: var(--warning-color);
        animation: pulse 0.5s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .testing-body {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1px;
        background: var(--border-color);
    }
    
    .testing-left,
    .testing-right {
        background: var(--bg-main);
        padding: 20px;
    }
    
    .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
    }
    
    .panel-header h4 {
        font-size: 16px;
        font-weight: 600;
    }
    
    .log-controls {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .checkbox-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--text-secondary);
        cursor: pointer;
    }
    
    .message-composer {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    
    .quick-actions {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid var(--border-color);
    }
    
    .quick-actions h5 {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 12px;
    }
    
    .quick-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .message-log {
        background: var(--code-bg);
        border-radius: var(--radius-md);
        height: 400px;
        overflow-y: auto;
        padding: 12px;
        font-family: var(--font-mono);
        font-size: 12px;
    }
    
    .log-empty {
        color: var(--text-secondary-dark);
        text-align: center;
        padding: 40px;
    }
    
    .log-entry {
        margin-bottom: 8px;
        padding: 8px 12px;
        border-radius: var(--radius-sm);
        border-left: 3px solid var(--border-color);
    }
    
    .log-entry.sent {
        background: rgba(99, 102, 241, 0.1);
        border-left-color: var(--secondary-color);
    }
    
    .log-entry.received {
        background: rgba(5, 150, 105, 0.1);
        border-left-color: var(--primary-color);
    }
    
    .log-entry.error {
        background: rgba(239, 68, 68, 0.1);
        border-left-color: var(--danger-color);
    }
    
    .log-entry.system {
        background: rgba(107, 114, 128, 0.1);
        border-left-color: var(--text-secondary);
    }
    
    .log-time {
        color: var(--text-secondary-dark);
        margin-right: 8px;
    }
    
    .log-direction {
        font-weight: 600;
        margin-right: 8px;
    }
    
    .log-entry.sent .log-direction { color: var(--secondary-color); }
    .log-entry.received .log-direction { color: var(--primary-color); }
    .log-entry.error .log-direction { color: var(--danger-color); }
    .log-entry.system .log-direction { color: var(--text-secondary); }
    
    .log-content {
        color: var(--code-text);
        white-space: pre-wrap;
        word-break: break-all;
    }
    
    /* Responsive */
    @media (max-width: 1024px) {
        .testing-body {
            grid-template-columns: 1fr;
        }
    }
    
    @media (max-width: 768px) {
        .sidebar {
            transform: translateX(-100%);
        }
        
        .main-content {
            margin-left: 0;
        }
        
        .content-container {
            padding: 20px;
        }
        
        .connection-controls {
            flex-direction: column;
        }
        
        .text-input {
            min-width: 100%;
        }
    }
    '''


def get_javascript() -> str:
    """Return JavaScript for WebSocket testing functionality."""
    endpoints_json = json.dumps(WEBSOCKET_ENDPOINTS)
    return f'''
    // WebSocket Documentation JavaScript
    
    // Global state
    let ws = null;
    let isConnected = false;
    const endpoints = {endpoints_json};
    
    // Initialize
    document.addEventListener('DOMContentLoaded', () => {{
        initializeTheme();
        initializeNavigation();
        initializeEventSelect();
        updateBaseUrl();
        hljs.highlightAll();
    }});
    
    // Theme Management
    function initializeTheme() {{
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        document.getElementById('theme-toggle').addEventListener('click', () => {{
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }});
    }}
    
    // Navigation
    function initializeNavigation() {{
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {{
            link.addEventListener('click', (e) => {{
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            }});
        }});
        
        // Update active link on scroll
        const sections = document.querySelectorAll('.doc-section');
        
        window.addEventListener('scroll', () => {{
            let current = '';
            
            sections.forEach(section => {{
                const sectionTop = section.offsetTop;
                if (scrollY >= sectionTop - 100) {{
                    current = section.getAttribute('id');
                }}
            }});
            
            navLinks.forEach(link => {{
                link.classList.remove('active');
                if (link.getAttribute('href') === '#' + current) {{
                    link.classList.add('active');
                }}
            }});
        }});
    }}
    
    // Event Select
    function initializeEventSelect() {{
        const select = document.getElementById('event-select');
        const endpointSelect = document.getElementById('ws-endpoint');
        
        function updateEvents() {{
            const endpointPath = endpointSelect.value;
            const endpoint = endpoints.find(e => e.path === endpointPath);
            
            select.innerHTML = '<option value="">Select an event...</option>';
            
            if (endpoint && endpoint.client_events) {{
                endpoint.client_events.forEach(event => {{
                    const option = document.createElement('option');
                    option.value = event.event;
                    option.textContent = `${{event.event}} - ${{event.description}}`;
                    option.dataset.payload = JSON.stringify(event.payload);
                    select.appendChild(option);
                }});
            }}
        }}
        
        endpointSelect.addEventListener('change', updateEvents);
        updateEvents();
    }}
    
    function updatePayloadTemplate() {{
        const select = document.getElementById('event-select');
        const textarea = document.getElementById('message-input');
        const selectedOption = select.options[select.selectedIndex];
        
        if (selectedOption && selectedOption.dataset.payload) {{
            const payload = JSON.parse(selectedOption.dataset.payload);
            textarea.value = JSON.stringify(payload, null, 2);
        }}
    }}
    
    // Base URL
    function updateBaseUrl() {{
        const baseUrl = `${{window.location.protocol === 'https:' ? 'wss:' : 'ws:'}}//${{window.location.host}}`;
        document.getElementById('base-url').textContent = baseUrl;
    }}
    
    // Copy Functions
    function copyBaseUrl() {{
        const url = document.getElementById('base-url').textContent;
        navigator.clipboard.writeText(url);
        showCopyFeedback(event.target);
    }}
    
    function copyEndpointUrl(path) {{
        const baseUrl = document.getElementById('base-url').textContent;
        navigator.clipboard.writeText(baseUrl + path);
        showCopyFeedback(event.target);
    }}
    
    function showCopyFeedback(btn) {{
        const original = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = original, 1500);
    }}
    
    // WebSocket Connection
    function toggleConnection() {{
        if (isConnected) {{
            disconnect();
        }} else {{
            connect();
        }}
    }}
    
    function connect() {{
        const endpoint = document.getElementById('ws-endpoint').value;
        const token = document.getElementById('ws-token').value;
        
        if (!endpoint) {{
            addLogEntry('system', 'Please select an endpoint');
            return;
        }}
        
        if (!token) {{
            addLogEntry('system', 'Please enter a JWT token');
            return;
        }}
        
        const baseUrl = document.getElementById('base-url').textContent;
        const wsUrl = `${{baseUrl}}${{endpoint}}?token=${{encodeURIComponent(token)}}`;
        
        updateStatus('connecting');
        addLogEntry('system', `Connecting to ${{wsUrl}}...`);
        
        try {{
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {{
                isConnected = true;
                updateStatus('connected');
                addLogEntry('system', 'Connected successfully');
                updateConnectionButtons(true);
            }};
            
            ws.onmessage = (event) => {{
                try {{
                    const data = JSON.parse(event.data);
                    addLogEntry('received', JSON.stringify(data, null, 2));
                }} catch (e) {{
                    addLogEntry('received', event.data);
                }}
            }};
            
            ws.onerror = (error) => {{
                addLogEntry('error', 'WebSocket error');
                updateStatus('disconnected');
            }};
            
            ws.onclose = (event) => {{
                isConnected = false;
                updateStatus('disconnected');
                addLogEntry('system', `Disconnected (code: ${{event.code}}, reason: ${{event.reason || 'N/A'}})`);
                updateConnectionButtons(false);
            }};
        }} catch (error) {{
            addLogEntry('error', `Connection failed: ${{error.message}}`);
            updateStatus('disconnected');
        }}
    }}
    
    function disconnect() {{
        if (ws) {{
            ws.close(1000, 'User disconnect');
            ws = null;
        }}
        isConnected = false;
        updateStatus('disconnected');
        updateConnectionButtons(false);
    }}
    
    function updateStatus(status) {{
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');
        
        indicator.className = 'status-indicator';
        
        switch (status) {{
            case 'connected':
                indicator.classList.add('connected');
                text.textContent = 'Connected';
                break;
            case 'connecting':
                indicator.classList.add('connecting');
                text.textContent = 'Connecting...';
                break;
            default:
                text.textContent = 'Disconnected';
        }}
    }}
    
    function updateConnectionButtons(connected) {{
        document.getElementById('connect-btn').disabled = connected;
        document.getElementById('disconnect-btn').disabled = !connected;
        document.getElementById('send-btn').disabled = !connected;
    }}
    
    // Messaging
    function sendMessage() {{
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message || !ws || !isConnected) {{
            return;
        }}
        
        try {{
            const parsed = JSON.parse(message);
            ws.send(JSON.stringify(parsed));
            addLogEntry('sent', JSON.stringify(parsed, null, 2));
        }} catch (e) {{
            addLogEntry('error', `Invalid JSON: ${{e.message}}`);
        }}
    }}
    
    function formatJson() {{
        const input = document.getElementById('message-input');
        try {{
            const parsed = JSON.parse(input.value);
            input.value = JSON.stringify(parsed, null, 2);
        }} catch (e) {{
            addLogEntry('error', `Invalid JSON: ${{e.message}}`);
        }}
    }}
    
    // Quick Actions
    function sendPing() {{
        if (!isConnected) return;
        const payload = {{"event": "ping", "data": {{}}}};
        ws.send(JSON.stringify(payload));
        addLogEntry('sent', JSON.stringify(payload, null, 2));
    }}
    
    function sendSubscribe() {{
        if (!isConnected) return;
        const payload = {{"event": "subscribe", "data": {{"channel": "users"}}}};
        ws.send(JSON.stringify(payload));
        addLogEntry('sent', JSON.stringify(payload, null, 2));
    }}
    
    function sendStatusUpdate() {{
        if (!isConnected) return;
        const payload = {{"event": "user:status", "data": {{"status": "online"}}}};
        ws.send(JSON.stringify(payload));
        addLogEntry('sent', JSON.stringify(payload, null, 2));
    }}
    
    // Logging
    function addLogEntry(type, content) {{
        const log = document.getElementById('message-log');
        const autoScroll = document.getElementById('auto-scroll').checked;
        
        // Remove empty message if present
        const empty = log.querySelector('.log-empty');
        if (empty) empty.remove();
        
        const entry = document.createElement('div');
        entry.className = `log-entry ${{type}}`;
        
        const time = new Date().toLocaleTimeString();
        const direction = {{
            'sent': '↑ SENT',
            'received': '↓ RECV',
            'error': '✕ ERROR',
            'system': 'ℹ SYS'
        }}[type];
        
        entry.innerHTML = `
            <span class="log-time">${{time}}</span>
            <span class="log-direction">${{direction}}</span>
            <div class="log-content">${{escapeHtml(content)}}</div>
        `;
        
        log.appendChild(entry);
        
        if (autoScroll) {{
            log.scrollTop = log.scrollHeight;
        }}
    }}
    
    function clearLogs() {{
        const log = document.getElementById('message-log');
        log.innerHTML = '<div class="log-empty">Connect to a WebSocket to see messages</div>';
    }}
    
    function escapeHtml(text) {{
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }}
    '''
