"""Services package — business logic layer.

Provides FastAPI dependency functions that wire services to the
application-wide :class:`~providers.base.DataProvider`.  Each factory
is decorated with :func:`functools.lru_cache` so that expensive
internal state (e.g. the measurement signal-id index built by
:class:`MeasurementService`) is constructed only once.

The caching is safe because :func:`providers.get_provider` always
returns the same singleton instance, making these effectively
parameterless calls.
"""

from functools import lru_cache

from providers import get_provider
from services.asset import AssetService
from services.measurement import MeasurementService
from services.signal import SignalService


@lru_cache(maxsize=1)
def get_asset_service() -> AssetService:
    """FastAPI dependency that returns a cached :class:`AssetService`."""
    return AssetService(get_provider())


@lru_cache(maxsize=1)
def get_signal_service() -> SignalService:
    """FastAPI dependency that returns a cached :class:`SignalService`."""
    return SignalService(get_provider())


@lru_cache(maxsize=1)
def get_measurement_service() -> MeasurementService:
    """FastAPI dependency that returns a cached :class:`MeasurementService`.

    Caching ensures the measurement signal-id index is built only once.
    """
    return MeasurementService(get_provider())
