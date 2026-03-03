"""Shared test fixtures."""

from models.asset import Asset
from models.measurement import Measurement
from models.signal import Signal
from providers.base import DataProvider


class StubProvider(DataProvider):
    """In-memory provider for testing.

    Accepts optional lists for each data type; defaults to empty lists.
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
        return self._signals

    def load_assets(self) -> list[Asset]:
        return self._assets

    def load_measurements(self) -> list[Measurement]:
        return self._measurements
