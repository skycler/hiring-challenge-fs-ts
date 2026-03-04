"""Filesystem-backed data provider.

Reads signals from JSON, assets from JSON, and measurements from a
pipe-delimited CSV with European comma decimals.  Each dataset is cached
on first load so subsequent calls return the same list without re-reading
the file.
"""

import csv
import json
import logging
from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel

from models.asset import Asset
from models.measurement import MeasurementTuple
from models.signal import Signal
from providers.base import DataProvider
from settings import Settings

logger = logging.getLogger(__name__)

_M = TypeVar("_M", bound=BaseModel)


class FileSystemProvider(DataProvider):
    """Load domain data from local JSON/CSV files.

    JSON datasets share a common load-validate-cache pipeline
    (:meth:`_load_json`).  The CSV pipeline is specialised because of the
    pipe-delimited format and European comma decimals.

    Args:
        settings: Application settings providing file paths.  Defaults to
            the global :meth:`Settings.get` singleton when omitted.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings.get()
        self._signals_cache: list[Signal] | None = None
        self._assets_cache: list[Asset] | None = None
        self._measurements_cache: list[MeasurementTuple] | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(path: str, model: type[_M]) -> list[_M]:
        """Read a JSON array from *path* and validate each element as *model*.

        Raises:
            FileNotFoundError: If *path* does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValueError: If a record fails Pydantic validation.
        """
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            return [model.model_validate(record) for record in raw]
        except FileNotFoundError:
            logger.error("File not found: %s", path)
            raise
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error("Failed to parse %s: %s", path, exc)
            raise

    # ------------------------------------------------------------------
    # DataProvider interface
    # ------------------------------------------------------------------

    def load_signals(self) -> list[Signal]:
        """Load all signals from ``signal.json``, caching on first read."""
        if self._signals_cache is None:
            self._signals_cache = self._load_json(self._settings.signals_path, Signal)
            logger.info(
                "Loaded %d signals from %s",
                len(self._signals_cache),
                self._settings.signals_path,
            )
        return self._signals_cache

    def load_assets(self) -> list[Asset]:
        """Load all assets from ``assets.json``, caching on first read."""
        if self._assets_cache is None:
            self._assets_cache = self._load_json(self._settings.assets_path, Asset)
            logger.info(
                "Loaded %d assets from %s",
                len(self._assets_cache),
                self._settings.assets_path,
            )
        return self._assets_cache

    def load_measurements(self) -> list[MeasurementTuple]:
        """Load all measurements from ``measurements.csv``, caching on first read.

        The CSV is pipe-delimited with European comma decimals
        (e.g. ``116,129`` -> ``116.129``).  Data is stored as lightweight
        :class:`MeasurementTuple` instances to minimise memory usage.
        """
        if self._measurements_cache is None:
            measurements: list[MeasurementTuple] = []
            try:
                with open(self._settings.measurements_path, encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f, delimiter="|")
                    for row in reader:
                        measurements.append(
                            MeasurementTuple(
                                timestamp=datetime.fromisoformat(row["Ts"]),
                                signal_id=int(row["SignalId"]),
                                value=float(row["MeasurementValue"].replace(",", ".")),
                            )
                        )
            except FileNotFoundError:
                logger.error("Measurements file not found: %s", self._settings.measurements_path)
                raise
            except (KeyError, ValueError) as exc:
                logger.error(
                    "Failed to parse measurements file %s: %s",
                    self._settings.measurements_path,
                    exc,
                )
                raise
            self._measurements_cache = measurements
            logger.info(
                "Loaded %d measurements from %s",
                len(self._measurements_cache),
                self._settings.measurements_path,
            )
        return self._measurements_cache
