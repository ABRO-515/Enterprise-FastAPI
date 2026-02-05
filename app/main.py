from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import auth, health
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.db.session import init_db
from app.middleware.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    configure_logging(settings)

    app = FastAPI(title=settings.app_name)
    app.add_middleware(RequestIdMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        allow_credentials=settings.cors_allow_credentials,
    )

    app.include_router(health.router, prefix=settings.api_prefix, tags=["health"])
    app.include_router(auth.router, prefix=settings.api_prefix)

    register_error_handlers(app)

    Instrumentator().instrument(app).expose(app, endpoint=settings.metrics_path)

    @app.on_event("startup")
    async def on_startup() -> None:
        
        if settings.create_tables_on_startup:
            await init_db()

    return app


app = create_app()
