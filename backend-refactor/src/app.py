"""Application factory and configuration.

Uses a FastAPI **lifespan** context manager to eagerly warm all
service caches at startup (CSV parsing, index building) so the first
request is not penalised by cold-start latency.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routes import assets_router, health_router, measurements_router, signals_router
from services import get_asset_service, get_measurement_service, get_signal_service
from settings import Settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Warm service caches eagerly so the first request is fast.

    Triggers index construction in each service by calling a cheap
    read-only method.  The ``yield`` separates startup from shutdown.
    """
    logger.info("Warming service caches …")
    get_asset_service().get_all()
    get_signal_service().get_all()
    get_measurement_service().get_measurements([])
    logger.info("Service caches warm.")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings.get()

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        lifespan=lifespan,
    )

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
