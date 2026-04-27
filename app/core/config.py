from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    # =========================
    # APP CORE
    # =========================
    app_name: str = "FastAPI Boilerplate"
    environment: str = "local"
    api_prefix: str = "/api/v1"

    # =========================
    # LOGGING
    # =========================
    log_level: str = "INFO"
    log_json: bool = False
    log_color: bool = True

    # =========================
    # SECURITY (JWT)
    # =========================
    jwt_secret: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 30

    # =========================
    # CORS
    # =========================
    cors_allow_origins: List[str] = ["*"]
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    cors_allow_credentials: bool = True

    # =========================
    # DATABASE
    # =========================
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5437/app"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    create_tables_on_startup: bool = False
    auto_migrate: bool = False

    # =========================
    # REDIS
    # =========================
    redis_url: str = "redis://redis:6379/0"
    redis_cluster_nodes: Optional[str] = None
    redis_password: Optional[str] = None

    # =========================
    # RABBITMQ
    # =========================
    rabbitmq_url: str = "amqp://admin:admin@rabbitmq:5672/"

    # =========================
    # RATE LIMITING
    # =========================
    rate_limit_max: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_exempt_routes: List[str] = ["/api/v1/health", "/metrics"]

    # =========================
    # METRICS
    # =========================
    metrics_path: str = "/metrics"

    # =========================
    # Pydantic config
    # =========================
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()