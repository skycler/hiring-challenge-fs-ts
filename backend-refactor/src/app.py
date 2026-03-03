"""Application factory and configuration."""

import logging

from fastapi import FastAPI

from routes import assets_router, health_router, measurements_router, signals_router
from settings import Settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings.get()

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    )

    app = FastAPI(title=settings.app_name, version=settings.api_version)

    app.include_router(health_router)
    app.include_router(assets_router)
    app.include_router(signals_router)
    app.include_router(measurements_router)

    logger.info(
        "%s %s started — debug=%s",
        settings.app_name,
        settings.api_version,
        settings.debug,
    )

    return app
