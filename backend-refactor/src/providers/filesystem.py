"""Filesystem-backed data provider.

Reads signals from JSON, assets from JSON, and measurements from a
pipe-delimited CSV with European comma decimals.  Each dataset is cached
on first load so subsequent calls return the same list without re-reading
the file.
"""

import csv
import json
from datetime import datetime

from models.asset import Asset
from models.measurement import Measurement
from models.signal import Signal
from providers.base import DataProvider
from settings import Settings


class FileSystemProvider(DataProvider):
    """Load domain data from local JSON/CSV files.

    Args:
        settings: Application settings providing file paths.  Defaults to
            the global :meth:`Settings.get` singleton when omitted.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings.get()
        self._signals_cache: list[Signal] | None = None
        self._assets_cache: list[Asset] | None = None
        self._measurements_cache: list[Measurement] | None = None

    # ------------------------------------------------------------------
    # DataProvider interface
    # ------------------------------------------------------------------

    def load_signals(self) -> list[Signal]:
        """Load all signals from ``signal.json``, caching on first read."""
        if self._signals_cache is None:
            with open(self._settings.signals_path) as f:
                raw = json.load(f)
            self._signals_cache = [Signal.model_validate(record) for record in raw]
        return self._signals_cache

    def load_assets(self) -> list[Asset]:
        """Load all assets from ``assets.json``, caching on first read."""
        if self._assets_cache is None:
            with open(self._settings.assets_path) as f:
                raw = json.load(f)
            self._assets_cache = [Asset.model_validate(record) for record in raw]
        return self._assets_cache

    def load_measurements(self) -> list[Measurement]:
        """Load all measurements from ``measurements.csv``, caching on first read.

        The CSV is pipe-delimited with European comma decimals
        (e.g. ``116,129`` → ``116.129``).
        """
        if self._measurements_cache is None:
            measurements: list[Measurement] = []
            with open(self._settings.measurements_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter="|")
                for row in reader:
                    measurements.append(
                        Measurement(
                            timestamp=datetime.fromisoformat(row["Ts"]),
                            signal_id=row["SignalId"],
                            value=float(row["MeasurementValue"].replace(",", ".")),
                        )
                    )
            self._measurements_cache = measurements
        return self._measurements_cache
