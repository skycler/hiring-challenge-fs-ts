"""Routes package."""

from routes.assets import router as assets_router
from routes.health import router as health_router
from routes.measurements import router as measurements_router
from routes.signals import router as signals_router

__all__ = ["assets_router", "health_router", "measurements_router", "signals_router"]
