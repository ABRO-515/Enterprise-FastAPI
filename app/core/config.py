from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Boilerplate"
    environment: str = "local"
    log_level: str = "INFO"
    log_json: bool = True
    api_prefix: str = "/api/v1"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 30

    # CORS
    cors_allow_origins: list[str] = ["*"]  # comma-separated in env
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    cors_allow_credentials: bool = True

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5437/app"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    create_tables_on_startup: bool = False
    # Development convenience: autogenerate & apply Alembic migrations on startup
    auto_migrate: bool = False

    redis_url: str = "redis://localhost:6379/0"
    redis_cluster_nodes: str | None = None  # comma-separated host:port
    redis_password: str | None = None
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rate_limit_max: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_exempt_routes: list[str] = ["/api/v1/health", "/metrics"]
    metrics_path: str = "/metrics"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
