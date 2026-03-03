"""Application factory and configuration."""

from fastapi import FastAPI

from routes import assets_router, health_router, measurements_router, signals_router
from settings import Settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings.get()
    app = FastAPI(title=settings.app_name, version=settings.api_version)

    app.include_router(health_router)
    app.include_router(assets_router)
    app.include_router(signals_router)
    app.include_router(measurements_router)

    return app
