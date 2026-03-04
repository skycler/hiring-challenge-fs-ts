"""Services package — business logic layer."""

from fastapi import Depends

from providers import get_provider
from providers.base import DataProvider
from services.asset import AssetService
from services.measurement import MeasurementService
from services.signal import SignalService


def get_asset_service(
    provider: DataProvider = Depends(get_provider),
) -> AssetService:
    """FastAPI dependency that builds an :class:`AssetService`."""
    return AssetService(provider)


def get_signal_service(
    provider: DataProvider = Depends(get_provider),
) -> SignalService:
    """FastAPI dependency that builds a :class:`SignalService`."""
    return SignalService(provider)


def get_measurement_service(
    provider: DataProvider = Depends(get_provider),
) -> MeasurementService:
    """FastAPI dependency that builds a :class:`MeasurementService`.

    Chains onto :func:`providers.get_provider` so the provider is
    automatically injected by FastAPI's dependency system.
    """
    return MeasurementService(provider)
