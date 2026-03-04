"""Measurement service — business logic for measurements and statistics.

Filtering by signal IDs and date range is business logic and lives here,
not in the data provider.  The provider is injected so the service is
decoupled from any specific storage backend.

Internally, measurements are stored as lightweight
:class:`~models.measurement.MeasurementTuple` instances and indexed by
``signal_id`` with each signal's list **sorted by timestamp**.  Date-range
queries use :func:`bisect.bisect_left` / :func:`bisect.bisect_right` for
O(log n) lookup instead of scanning every row.
"""

import statistics
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime

from models.measurement import (
    FlatMeasurementList,
    Measurement,
    MeasurementList,
    MeasurementTuple,
    ResponseFormat,
)
from models.signal import SignalStats
from providers.base import DataProvider


class MeasurementService:
    """Business logic for measurements: filtering, stats calculation.

    Measurements are indexed by ``signal_id`` on first access.  Each
    signal's list is sorted by ``timestamp`` so date-range queries can
    use binary search (O(log n)) rather than a linear scan.

    Args:
        provider: The data provider to load raw measurements from.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider
        self._index: dict[int, list[MeasurementTuple]] | None = None

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def _get_index(self) -> dict[int, list[MeasurementTuple]]:
        """Return (and lazily build) the signal_id -> sorted measurements index.

        Each signal's measurement list is sorted by ``timestamp`` ascending
        to enable bisect-based date-range queries.
        """
        if self._index is None:
            idx: dict[int, list[MeasurementTuple]] = defaultdict(list)
            for m in self._provider.load_measurements():
                idx[m.signal_id].append(m)
            for measurements in idx.values():
                measurements.sort(key=lambda m: m.timestamp)
            self._index = dict(idx)
        return self._index

    # ------------------------------------------------------------------
    # Bisect helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bisect_range(
        measurements: list[MeasurementTuple],
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> tuple[int, int]:
        """Return ``(lo, hi)`` indices for measurements within the date range.

        Uses binary search on the sorted timestamp list.  Both bounds are
        **inclusive** (``>= from_date`` and ``<= to_date``).  When a bound
        is ``None`` the corresponding end is unbounded.
        """
        if from_date is not None:
            lo = bisect_left(measurements, from_date, key=lambda m: m.timestamp)
        else:
            lo = 0

        if to_date is not None:
            hi = bisect_right(measurements, to_date, key=lambda m: m.timestamp)
        else:
            hi = len(measurements)

        return lo, hi

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

        Results are paginated via ``limit`` / ``offset``.  Date-range
        filtering uses bisect for O(log n) per signal rather than a
        linear scan.

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
        index = self._get_index()

        # Collect (lo, hi) ranges per signal — O(log n) each via bisect.
        ranges: list[tuple[list[MeasurementTuple], int, int]] = []
        total = 0
        for sid in signal_ids:
            signal_measurements = index.get(sid, [])
            if not signal_measurements:
                continue
            lo, hi = self._bisect_range(signal_measurements, from_date, to_date)
            count = hi - lo
            if count > 0:
                ranges.append((signal_measurements, lo, hi))
                total += count

        # Build only the page we need — skip offset items, take limit items.
        page: list[MeasurementTuple] = []
        remaining_offset = offset
        remaining_limit = limit
        for signal_measurements, lo, hi in ranges:
            span = hi - lo
            if remaining_offset >= span:
                remaining_offset -= span
                continue
            start = lo + remaining_offset
            end = min(hi, start + remaining_limit)
            page.extend(signal_measurements[start:end])
            remaining_limit -= end - start
            remaining_offset = 0
            if remaining_limit <= 0:
                break

        if fmt is ResponseFormat.FLAT:
            timestamps: list[datetime] = []
            signal_ids_out: list[int] = []
            values: list[float] = []
            for m in page:
                timestamps.append(m.timestamp)
                signal_ids_out.append(m.signal_id)
                values.append(m.value)
            return FlatMeasurementList(
                total=total,
                count=len(page),
                limit=limit,
                offset=offset,
                timestamps=timestamps,
                signal_ids=signal_ids_out,
                values=values,
            )

        return MeasurementList(
            total=total,
            count=len(page),
            limit=limit,
            offset=offset,
            measurements=[
                Measurement(timestamp=m.timestamp, signal_id=m.signal_id, value=m.value)
                for m in page
            ],
        )

    def calculate_signal_stats(
        self,
        signal_id: int,
        from_date: datetime,
        to_date: datetime,
    ) -> SignalStats:
        """Calculate aggregate statistics for a signal over a date range.

        Uses bisect to select only the matching measurements, then
        computes statistics in a single pass where possible.

        Returns a :class:`SignalStats` with numeric fields set to ``None``
        when the date range contains no measurements.
        """
        index = self._get_index()
        signal_measurements = index.get(signal_id, [])
        lo, hi = self._bisect_range(signal_measurements, from_date, to_date)

        if lo >= hi:
            return SignalStats(
                signal_id=signal_id,
                from_date=from_date,
                to_date=to_date,
                count=0,
            )

        values = [m.value for m in signal_measurements[lo:hi]]
        count = len(values)

        # Single-pass min/max/sum.
        min_val = values[0]
        max_val = values[0]
        total = 0.0
        for v in values:
            if v < min_val:
                min_val = v
            if v > max_val:
                max_val = v
            total += v
        mean = total / count

        return SignalStats(
            signal_id=signal_id,
            from_date=from_date,
            to_date=to_date,
            count=count,
            mean=round(mean, 2),
            min=round(min_val, 2),
            max=round(max_val, 2),
            median=round(statistics.median(values), 2),
            std_dev=round(statistics.stdev(values), 2) if count > 1 else 0.0,
        )
