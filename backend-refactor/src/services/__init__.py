"""Services package — business logic layer."""

from fastapi import Depends

from providers import get_provider
from providers.base import DataProvider
from services.measurement import MeasurementService


def get_measurement_service(
    provider: DataProvider = Depends(get_provider),
) -> MeasurementService:
    """FastAPI dependency that builds a :class:`MeasurementService`.

    Chains onto :func:`providers.get_provider` so the provider is
    automatically injected by FastAPI's dependency system.
    """
    return MeasurementService(provider)
