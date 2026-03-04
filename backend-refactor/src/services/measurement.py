"""Measurement service — business logic for measurements and statistics.

Filtering by signal IDs and date range is business logic and lives here,
not in the data provider.  The provider is injected so the service is
decoupled from any specific storage backend.
"""

import statistics
from collections import defaultdict
from datetime import datetime

from models.measurement import (
    FlatMeasurementList,
    Measurement,
    MeasurementList,
    ResponseFormat,
)
from models.signal import SignalStats
from providers.base import DataProvider


class MeasurementService:
    """Business logic for measurements: filtering, stats calculation.

    Measurements are indexed by ``signal_id`` on first access for O(1)
    lookups instead of scanning the entire dataset on every request.

    Args:
        provider: The data provider to load raw measurements from.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider
        self._index: dict[int, list[Measurement]] | None = None

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def _get_index(self) -> dict[int, list[Measurement]]:
        """Return (and lazily build) the signal_id → measurements index."""
        if self._index is None:
            idx: dict[int, list[Measurement]] = defaultdict(list)
            for m in self._provider.load_measurements():
                idx[m.signal_id].append(m)
            self._index = dict(idx)
        return self._index

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

        Uses a signal_id index for fast lookup.  Both ``from_date`` and
        ``to_date`` bounds are inclusive (``>=`` and ``<=`` respectively).
        """
        index = self._get_index()

        candidates: list[Measurement] = []
        for sid in signal_ids:
            candidates.extend(index.get(sid, []))

        if from_date is None and to_date is None:
            return candidates

        return [
            m
            for m in candidates
            if (from_date is None or m.timestamp >= from_date)
            and (to_date is None or m.timestamp <= to_date)
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_date_range(from_date: datetime, to_date: datetime) -> None:
        """Raise :class:`ValueError` if ``from_date >= to_date``."""
        if from_date >= to_date:
            raise ValueError("Invalid date range: 'from' must be before 'to'")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_measurements(
        self,
        signal_ids: list[int],
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        *,
        limit: int = 1000,
        offset: int = 0,
        fmt: ResponseFormat = ResponseFormat.OBJECTS,
    ) -> MeasurementList | FlatMeasurementList:
        """Get measurements for signals in an optional date range.

        Results are paginated via ``limit`` / ``offset``.

        Args:
            signal_ids: Signal IDs to include.
            from_date: Inclusive lower bound on timestamp (optional).
            to_date: Inclusive upper bound on timestamp (optional).
            limit: Maximum number of measurements per page.
            offset: Zero-based offset into the full result set.
            fmt: Response layout — ``objects`` (default) returns a
                :class:`MeasurementList`; ``flat`` returns a
                :class:`FlatMeasurementList` with parallel arrays.

        Returns:
            A paginated measurement response in the requested format.
        """
        filtered = self._filter_measurements(signal_ids, from_date, to_date)
        page = filtered[offset : offset + limit]

        if fmt is ResponseFormat.FLAT:
            return FlatMeasurementList(
                total=len(filtered),
                count=len(page),
                limit=limit,
                offset=offset,
                timestamps=[m.timestamp for m in page],
                signal_ids=[m.signal_id for m in page],
                values=[m.value for m in page],
            )

        return MeasurementList(
            total=len(filtered),
            count=len(page),
            limit=limit,
            offset=offset,
            measurements=page,
        )

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
