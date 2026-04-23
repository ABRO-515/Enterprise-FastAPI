# 🚀 FastAPI Boilerplate + AI Chat System

  Production-ready FastAPI boilerplate extended with a real-time AI chat system (WebSocket + OpenAI streaming) using a clean layered architecture:

  Production-ready FastAPI boilerplate with a clean layered architecture:
  edge/api → mediators/usecases → services → repositories → models → infrastructure

# ✨ Features
# ⚙️ Core Backend

  FastAPI app factory with dependency injection
  Async SQLAlchemy 2.0 + asyncpg
  Pydantic v2 + pydantic-settings
  Structured JSON logging with request IDs
  Centralized config, error handling, metrics
  Alembic migrations
  Pytest + httpx tests
  Sliding window rate limiting (100 req / 60s)

# 🤖 AI Chat System (Contribution 🚀)

  Real-time chat using WebSockets
  AI integration using OpenAI API (streaming responses)
  Token-based WebSocket authentication
  Event-driven messaging system:
  message:send
  message:receive
  message:stream
  Special recipient_id="ai" for AI assistant
  Streaming responses chunk-by-chunk (ChatGPT-like UX)
  Redis pub/sub support (optional for scaling)

# 🎨 Frontend (NEW 🎯)

  ChatGPT-style dark UI
  Left sidebar (chat panel)
  Right-aligned user messages
  Left-aligned AI responses
  Smooth streaming text rendering
  Clean, modern prompt input section


# 📂 Project structure
```
    app/
      main.py
      api/
        v1/
          routers/
            health.py
            users.py
            chat_ws.py       
      core/
        config.py
        logging.py
        errors.py
      db/
       session.py
        base.py
      models/
        user.py
      schemas/
        user.py
      repositories/
        user_repository.py
      services/
        user_service.py
        ai_service.py       
      mediators/
        user_mediator.py
        chat_handler.py    
      middleware/
        request_id.py
        websocket_auth.py  
      frontend/
        index.html            
      tests/
        test_health.py
        test_users.py
      alembic/
        .env.example
        docker-compose.yml
        dockerfile
```
# ⚡ Rate Limiting

The application enforces sliding window rate limiting to prevent abuse.

- **Algorithm**: Sliding window per client IP address.
- **Limits**: Configurable via environment variables:
  - `RATE_LIMIT_MAX`: Maximum requests per window (default: 100)
  - `RATE_LIMIT_WINDOW_SECONDS`: Window duration in seconds (default: 60)
- **Exemptions**: Health checks (`/api/v1/health`) and metrics (`/metrics`) are exempt.
- **Behavior**: Returns HTTP 429 with `Retry-After` header and JSON error on limit exceeded.
- **Storage**: In-memory for simplicity; extensible to Redis for distributed setups.

# 🧠 AI Flow (How it works)

  Client → WebSocket → FastAPI → Chat Handler
        → If recipient_id == "ai"
            → AI Service (OpenAI)
            → Stream response
        → Send chunks back to client

## Setup
1. Create a virtual environment and install dependencies:
```
uv sync
```

2. Configure environment:
```
copy .env.example .env
```

3. Run the API:
```
uv run uvicorn app.main:app --reload
```

4. Run tests:
```
uv run pytest
```


5. Start infrastructure services:
```
docker-compose up -d
```


6. 🔌 WebSocket Usage:

  Endpoint:

    ws://localhost:8000/ws/chat?token=YOUR_TOKEN


## Migrations
```
uv run alembic revision --autogenerate -m "alter auth_user table"

uv run alembic upgrade head

```

## Endpoints

REST APIs

Health → /api/v1/health
Users → /api/v1/users
Auth → /api/v1/auth/*
Metrics → /metrics

WebSocket

Chat → /ws/chat

# 🧑‍💻 My Contribution

     I extended this boilerplate into a full AI-powered real-time chat system:

# 🔥 Backend Work

    Implemented WebSocket chat system
    Designed event-based messaging architecture
    Integrated OpenAI API with async streaming
    Built AI service layer (ai_service.py)
    Added WebSocket authentication system
    Implemented AI routing via recipient_id="ai"
    Handled real-time streaming responses
# 🎨 Frontend Work

    Built ChatGPT-like UI from scratch
    Implemented:
    Left/right message alignment
    Streaming message rendering
    Sidebar layout
    Prompt UX improvements
    Improved user interaction and responsiveness

# 🧠 What I Learned

    WebSockets in FastAPI (real-time systems)
    Async programming (Python)
    Streaming APIs (OpenAI)
    Clean architecture (layered design)
    Event-driven backend design
    Authentication in WebSockets
    Frontend + backend integration
    Debugging production-level issues (tokens, auth, rate limits)

# Contribution in RabbitMQ Concept

  Integrated RabbitMQ Topic Exchange into the project for event-driven communication
  Designed and implemented event publishing layer using clean architecture principles

  Added structured event routing with patterns like:

  chat.message.created
  chat.ai.response.generated
  chat.error.occurred
  Built producer and consumer setup to validate real-time message flow
  Established foundation for scalable microservices and AI event pipelines