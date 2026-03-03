"""Application factory and configuration."""

from fastapi import FastAPI

from api.v1.endpoints import assets as assets_v1
from api.v2.routes import measurements_router
from services import measurement_legacy
from settings import Settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings.get()
    app = FastAPI(title=settings.app_name, version=settings.api_version)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    # Register v1 routes
    app.include_router(assets_v1.router, prefix="/api/v1")
    app.include_router(measurements_router.router, prefix="/api/v1")
    app.include_router(assets_v1.router, tags=["assets"])
    app.include_router(measurements_router.router, tags=["measurement"])
    app.include_router(measurement_legacy.router, tags=["measurements"])

    return app
