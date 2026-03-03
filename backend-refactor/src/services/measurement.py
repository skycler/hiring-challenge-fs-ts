"""Measurement service — business logic for measurements and statistics.

Filtering by signal IDs and date range is business logic and lives here,
not in the data provider.  The provider is injected so the service is
decoupled from any specific storage backend.
"""

import statistics
from datetime import datetime

from models.measurement import Measurement, MeasurementList
from models.signal import SignalStats
from providers.base import DataProvider


class MeasurementService:
    """Business logic for measurements: filtering, stats calculation.

    Args:
        provider: The data provider to load raw measurements from.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _filter_measurements(
        self,
        signal_ids: list[int],
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[Measurement]:
        """Return measurements filtered by signal IDs and optional date range.

        Both ``from_date`` and ``to_date`` bounds are inclusive (``>=`` and
        ``<=`` respectively).
        """
        all_measurements = self._provider.load_measurements()
        signal_id_set = set(signal_ids)

        result = [m for m in all_measurements if m.signal_id in signal_id_set]

        if from_date is not None:
            result = [m for m in result if m.timestamp >= from_date]
        if to_date is not None:
            result = [m for m in result if m.timestamp <= to_date]

        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_measurements(
        self,
        signal_ids: list[int],
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> MeasurementList:
        """Get measurements for signals in an optional date range."""
        measurements = self._filter_measurements(signal_ids, from_date, to_date)
        return MeasurementList(count=len(measurements), measurements=measurements)

    def calculate_signal_stats(
        self,
        signal_id: int,
        from_date: datetime,
        to_date: datetime,
    ) -> SignalStats:
        """Calculate aggregate statistics for a signal over a date range.

        Returns a :class:`SignalStats` with numeric fields set to ``None``
        when the date range contains no measurements.
        """
        measurements = self._filter_measurements([signal_id], from_date, to_date)

        if not measurements:
            return SignalStats(
                signal_id=signal_id,
                from_date=from_date,
                to_date=to_date,
                count=0,
            )

        values = [m.value for m in measurements]

        return SignalStats(
            signal_id=signal_id,
            from_date=from_date,
            to_date=to_date,
            count=len(values),
            mean=round(statistics.mean(values), 2),
            min=round(min(values), 2),
            max=round(max(values), 2),
            median=round(statistics.median(values), 2),
            std_dev=round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        )
