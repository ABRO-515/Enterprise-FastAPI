# FastAPI Boilerplate

Production-ready FastAPI boilerplate with a clean layered architecture:
edge/api -> mediators/usecases -> services -> repositories -> models -> infrastructure.

## Features
- FastAPI app factory with dependency injection
- Async SQLAlchemy 2.0 + asyncpg
- Pydantic v2 + pydantic-settings
- Structured JSON logging with request IDs
- Centralized config, error handling, metrics
- Alembic migrations
- Pytest + httpx tests

## Project structure
```
app/
  main.py
  api/
    v1/
      routers/
        health.py
        users.py
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
  mediators/
    user_mediator.py
  middleware/
    request_id.py
tests/
  test_health.py
  test_users.py
alembic/
  env.py
  script.py.mako
  versions/
    0001_create_users.py
alembic.ini
pyproject.toml
.env.example
docker-compose.yml
Dockerfile
.dockerignore
```

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

## Migrations
```
uv run alembic revision --autogenerate -m "alter auth_user table"

uv run alembic upgrade head

```

## Endpoints
- Health: GET /api/v1/health
- Users: POST /api/v1/users, GET /api/v1/users, GET /api/v1/users/{user_id}
- Auth: POST /api/v1/auth/register, POST /api/v1/auth/login, GET /api/v1/auth/me
- Metrics: GET /metrics
