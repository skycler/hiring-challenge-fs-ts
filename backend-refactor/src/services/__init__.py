"""Services package — business logic layer.

Provides FastAPI dependency functions that wire services to the
application-wide :class:`~providers.base.DataProvider`.  Each service
is cached per provider instance so that expensive internal state (e.g.
the measurement signal-id index) is built only once rather than on
every request.
"""

from functools import lru_cache

from fastapi import Depends

from providers import get_provider
from providers.base import DataProvider
from services.asset import AssetService
from services.measurement import MeasurementService
from services.signal import SignalService


@lru_cache(maxsize=1)
def _cached_asset_service(provider: DataProvider) -> AssetService:
    """Return a cached :class:`AssetService` for *provider*."""
    return AssetService(provider)


@lru_cache(maxsize=1)
def _cached_signal_service(provider: DataProvider) -> SignalService:
    """Return a cached :class:`SignalService` for *provider*."""
    return SignalService(provider)


@lru_cache(maxsize=1)
def _cached_measurement_service(provider: DataProvider) -> MeasurementService:
    """Return a cached :class:`MeasurementService` for *provider*."""
    return MeasurementService(provider)


def get_asset_service(
    provider: DataProvider = Depends(get_provider),
) -> AssetService:
    """FastAPI dependency that returns a (cached) :class:`AssetService`.

    The provider is injected by FastAPI's dependency system via
    :func:`providers.get_provider`.
    """
    return _cached_asset_service(provider)


def get_signal_service(
    provider: DataProvider = Depends(get_provider),
) -> SignalService:
    """FastAPI dependency that returns a (cached) :class:`SignalService`.

    The provider is injected by FastAPI's dependency system via
    :func:`providers.get_provider`.
    """
    return _cached_signal_service(provider)


def get_measurement_service(
    provider: DataProvider = Depends(get_provider),
) -> MeasurementService:
    """FastAPI dependency that returns a (cached) :class:`MeasurementService`.

    The provider is injected by FastAPI's dependency system via
    :func:`providers.get_provider`.  Caching ensures the measurement
    signal-id index is built only once.
    """
    return _cached_measurement_service(provider)
