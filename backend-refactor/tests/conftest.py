"""Shared test fixtures.

Provides :class:`StubProvider`, an in-memory implementation of
:class:`~providers.base.DataProvider` used across all test modules.
"""

from models.asset import Asset
from models.measurement import Measurement
from models.signal import Signal
from providers.base import DataProvider


class StubProvider(DataProvider):
    """In-memory data provider for testing.

    Accepts optional lists for each data type; defaults to empty lists
    so tests only need to supply the data they care about.

    Args:
        signals: Pre-built signal objects to return from :meth:`load_signals`.
        assets: Pre-built asset objects to return from :meth:`load_assets`.
        measurements: Pre-built measurement objects to return from
            :meth:`load_measurements`.
    """

    def __init__(
        self,
        signals: list[Signal] | None = None,
        assets: list[Asset] | None = None,
        measurements: list[Measurement] | None = None,
    ) -> None:
        self._signals = signals or []
        self._assets = assets or []
        self._measurements = measurements or []

    def load_signals(self) -> list[Signal]:
        """Return the pre-configured signal list."""
        return self._signals

    def load_assets(self) -> list[Asset]:
        """Return the pre-configured asset list."""
        return self._assets

    def load_measurements(self) -> list[Measurement]:
        """Return the pre-configured measurement list."""
        return self._measurements
