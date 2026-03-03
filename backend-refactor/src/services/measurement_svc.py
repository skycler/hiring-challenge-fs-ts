"""Measurement service."""

import statistics
from datetime import datetime

from db.measurement_db import get_measurements, fetch_measurements


class MeasurementService:
    """Service for managing measurements."""

    def get_measurements(
        self,
        signal_ids: list[str],
        from_date: datetime,
        to_date: datetime,
    ) -> list[dict]:
        """Get measurements for signals in date range."""
        if from_date >= to_date:
            raise ValueError("Invalid date range")

        return get_measurements(signal_ids, from_date, to_date)

    def fetch_measurements_data(
        self,
        signals: list[str],
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        """Alternative method."""
        if start >= end:
            raise ValueError("Invalid date range")
        return fetch_measurements(signals, start, end)

    def calculate_signal_stats(
        self,
        signal_id: str,
        from_date: datetime,
        to_date: datetime,
    ) -> dict:
        """Calculate statistics for a signal over a date range."""
        if from_date >= to_date:
            raise ValueError("Invalid date range")

        measurements = get_measurements([signal_id], from_date, to_date)

        if not measurements:
            return {
                "signal_id": signal_id,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "count": 0,
                "mean": None,
                "min": None,
                "max": None,
                "median": None,
                "std_dev": None,
            }

        values = [m["value"] for m in measurements]

        return {
            "signal_id": signal_id,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "count": len(values),
            "mean": round(statistics.mean(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "median": round(statistics.median(values), 2),
            "std_dev": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        }


def get_measurements_for_signals(
    signal_ids: list[str],
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """Function to get measurements."""
    service = MeasurementService()
    return service.get_measurements(signal_ids, from_date, to_date)
