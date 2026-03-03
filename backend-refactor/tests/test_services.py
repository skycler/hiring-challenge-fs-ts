"""Tests for the measurement service layer.

The service now owns filtering logic and receives a DataProvider via
constructor injection.  Tests use a stub provider with inlined data.
"""

from datetime import datetime

from conftest import StubProvider
from models.measurement import Measurement, MeasurementList
from models.signal import SignalStats
from services import get_measurement_service
from services.measurement import MeasurementService

# ---------------------------------------------------------------------------
# Inline fixtures
# ---------------------------------------------------------------------------

_MEASUREMENTS = [
    Measurement(timestamp=datetime(2021, 11, 7, 10, 0), signal_id=100, value=100.0),
    Measurement(timestamp=datetime(2021, 11, 7, 11, 0), signal_id=100, value=200.0),
    Measurement(timestamp=datetime(2021, 11, 7, 12, 0), signal_id=100, value=300.0),
    Measurement(timestamp=datetime(2021, 11, 8, 10, 0), signal_id=200, value=230.5),
]


def _make_svc(measurements: list[Measurement] | None = None) -> MeasurementService:
    return MeasurementService(StubProvider(measurements=measurements or _MEASUREMENTS))


def _make_empty_svc() -> MeasurementService:
    return MeasurementService(StubProvider(measurements=[]))


# ---------------------------------------------------------------------------
# get_measurements — filtering tests
# ---------------------------------------------------------------------------


class TestFilterBySignalId:
    def test_single_signal(self):
        svc = _make_svc()
        result = svc.get_measurements([100])
        assert result.count == 3
        assert all(m.signal_id == 100 for m in result.measurements)

    def test_multiple_signals(self):
        svc = _make_svc()
        result = svc.get_measurements([100, 200])
        assert result.count == 4

    def test_unknown_signal(self):
        svc = _make_svc()
        result = svc.get_measurements([999])
        assert result.count == 0
        assert result.measurements == []


class TestFilterByDateRange:
    def test_from_and_to(self):
        svc = _make_svc()
        result = svc.get_measurements(
            [100, 200],
            from_date=datetime(2021, 11, 8, 0, 0, 0),
            to_date=datetime(2021, 11, 9, 0, 0, 0),
        )
        assert result.count == 1
        assert result.measurements[0].signal_id == 200

    def test_from_only(self):
        svc = _make_svc()
        result = svc.get_measurements(
            [100],
            from_date=datetime(2021, 11, 7, 10, 30),
        )
        # 11:00 and 12:00 pass
        assert result.count == 2

    def test_to_only(self):
        svc = _make_svc()
        result = svc.get_measurements(
            [100],
            to_date=datetime(2021, 11, 7, 10, 30),
        )
        # Only 10:00 passes
        assert result.count == 1

    def test_no_date_filter(self):
        svc = _make_svc()
        result = svc.get_measurements([100])
        assert result.count == 3


# ---------------------------------------------------------------------------
# get_measurements — wrapper tests
# ---------------------------------------------------------------------------


class TestGetMeasurements:
    def test_returns_measurement_list(self):
        svc = _make_svc()
        result = svc.get_measurements([100])
        assert isinstance(result, MeasurementList)
        assert result.count == 3
        assert len(result.measurements) == 3

    def test_passes_date_filters(self):
        svc = _make_svc()
        result = svc.get_measurements(
            [100],
            from_date=datetime(2021, 11, 7, 10, 30),
            to_date=datetime(2021, 11, 7, 12, 30),
        )
        assert result.count == 2

    def test_empty_result(self):
        svc = _make_empty_svc()
        result = svc.get_measurements([999])
        assert result.count == 0
        assert result.measurements == []


# ---------------------------------------------------------------------------
# calculate_signal_stats
# ---------------------------------------------------------------------------


class TestCalculateSignalStats:
    def test_returns_signal_stats(self):
        svc = _make_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert isinstance(result, SignalStats)

    def test_count(self):
        svc = _make_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.count == 3

    def test_mean(self):
        svc = _make_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.mean == 200.0

    def test_min_max(self):
        svc = _make_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.min == 100.0
        assert result.max == 300.0

    def test_median(self):
        svc = _make_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.median == 200.0

    def test_std_dev(self):
        svc = _make_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.std_dev == 100.0

    def test_empty_range(self):
        svc = _make_empty_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.count == 0
        assert result.mean is None
        assert result.min is None
        assert result.max is None
        assert result.median is None
        assert result.std_dev is None

    def test_single_measurement_std_dev_zero(self):
        svc = _make_svc([_MEASUREMENTS[0]])
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.std_dev == 0.0

    def test_dates_in_result(self):
        svc = _make_svc()
        from_dt = datetime(2021, 1, 1)
        to_dt = datetime(2021, 12, 31)
        result = svc.calculate_signal_stats(100, from_dt, to_dt)
        assert result.from_date == from_dt
        assert result.to_date == to_dt

    def test_signal_id_in_result(self):
        svc = _make_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.signal_id == 100


# ---------------------------------------------------------------------------
# get_measurement_service dependency factory
# ---------------------------------------------------------------------------


class TestGetMeasurementServiceFactory:
    def test_returns_measurement_service(self):
        provider = StubProvider(measurements=_MEASUREMENTS)
        svc = get_measurement_service(provider)
        assert isinstance(svc, MeasurementService)

    def test_service_uses_provided_provider(self):
        provider = StubProvider(measurements=_MEASUREMENTS)
        svc = get_measurement_service(provider)
        result = svc.get_measurements([100])
        assert result.count == 3
