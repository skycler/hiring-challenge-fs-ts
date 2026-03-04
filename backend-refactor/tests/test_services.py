"""Tests for the service layer.

Services own business logic and receive a DataProvider via
constructor injection.  Tests use a stub provider with inlined data.
"""

from datetime import datetime

import pytest
from conftest import StubProvider
from models.asset import Asset
from models.measurement import (
    FlatMeasurementList,
    MeasurementList,
    MeasurementTuple,
    ResponseFormat,
)
from models.signal import Signal, SignalStats
from services import get_asset_service, get_measurement_service, get_signal_service
from services.asset import AssetService
from services.measurement import MeasurementService
from services.signal import SignalService

# ---------------------------------------------------------------------------
# Inline fixtures
# ---------------------------------------------------------------------------

_ASSETS = [
    Asset(asset_id=1, latitude=47.5, longitude=8.2, description="UW Alpha"),
    Asset(asset_id=2, latitude=47.2, longitude=8.9, description="UW Beta"),
]

_SIGNALS = [
    Signal(signal_g_id="aaa-111", signal_id=100, signal_name="SIG_A", asset_id=1, unit="kV"),
    Signal(signal_g_id="bbb-222", signal_id=200, signal_name="SIG_B", asset_id=1, unit="kW"),
    Signal(signal_g_id="ccc-333", signal_id=300, signal_name="SIG_C", asset_id=2, unit="kV"),
]

_MEASUREMENTS = [
    MeasurementTuple(timestamp=datetime(2021, 11, 7, 10, 0), signal_id=100, value=100.0),
    MeasurementTuple(timestamp=datetime(2021, 11, 7, 11, 0), signal_id=100, value=200.0),
    MeasurementTuple(timestamp=datetime(2021, 11, 7, 12, 0), signal_id=100, value=300.0),
    MeasurementTuple(timestamp=datetime(2021, 11, 8, 10, 0), signal_id=200, value=230.5),
]

_stub_provider = StubProvider(
    signals=_SIGNALS,
    assets=_ASSETS,
    measurements=_MEASUREMENTS,
)


def _make_measurement_svc(
    measurements: list[MeasurementTuple] | None = None,
) -> MeasurementService:
    return MeasurementService(StubProvider(measurements=measurements or _MEASUREMENTS))


def _make_empty_measurement_svc() -> MeasurementService:
    return MeasurementService(StubProvider(measurements=[]))


# ===========================================================================
# AssetService
# ===========================================================================


class TestAssetServiceGetAll:
    """AssetService.get_all returns every asset from the provider."""

    def test_returns_all_assets(self):
        svc = AssetService(_stub_provider)
        result = svc.get_all()
        assert len(result) == 2
        assert all(isinstance(a, Asset) for a in result)

    def test_empty(self):
        svc = AssetService(StubProvider())
        assert svc.get_all() == []


class TestAssetServiceFindById:
    """AssetService.find_by_id returns matching asset or None."""

    def test_found(self):
        svc = AssetService(_stub_provider)
        asset = svc.find_by_id(1)
        assert asset is not None
        assert asset.asset_id == 1

    def test_not_found(self):
        svc = AssetService(_stub_provider)
        assert svc.find_by_id(999) is None

    def test_index_reused_across_calls(self):
        """Second find_by_id reuses the cached index (early-return path)."""
        svc = AssetService(_stub_provider)
        svc.find_by_id(1)
        assert svc._by_id is not None
        # Second call hits the early-return in _ensure_index
        asset = svc.find_by_id(2)
        assert asset is not None
        assert asset.asset_id == 2


# ===========================================================================
# SignalService
# ===========================================================================


class TestSignalServiceFindByAssetId:
    """SignalService.find_by_asset_id returns signals for a given asset."""

    def test_returns_matching_signals(self):
        svc = SignalService(_stub_provider)
        result = svc.find_by_asset_id(1)
        assert len(result) == 2
        assert all(s.asset_id == 1 for s in result)

    def test_single_match(self):
        svc = SignalService(_stub_provider)
        result = svc.find_by_asset_id(2)
        assert len(result) == 1
        assert result[0].signal_id == 300

    def test_no_match(self):
        svc = SignalService(_stub_provider)
        result = svc.find_by_asset_id(999)
        assert result == []

    def test_empty_provider(self):
        svc = SignalService(StubProvider())
        result = svc.find_by_asset_id(1)
        assert result == []


class TestSignalServiceGetAll:
    """SignalService.get_all returns every signal from the provider."""

    def test_returns_all_signals(self):
        svc = SignalService(_stub_provider)
        result = svc.get_all()
        assert len(result) == 3
        assert all(isinstance(s, Signal) for s in result)

    def test_empty(self):
        svc = SignalService(StubProvider())
        assert svc.get_all() == []


class TestSignalServiceFindById:
    """SignalService.find_by_id returns matching signal or None."""

    def test_found(self):
        svc = SignalService(_stub_provider)
        signal = svc.find_by_id(100)
        assert signal is not None
        assert signal.signal_id == 100

    def test_not_found(self):
        svc = SignalService(_stub_provider)
        assert svc.find_by_id(999) is None

    def test_index_reused_across_calls(self):
        """Second find_by_id reuses the cached indexes (early-return path)."""
        svc = SignalService(_stub_provider)
        svc.find_by_id(100)
        assert svc._by_id is not None
        # Second call hits the early-return in _ensure_indexes
        signal = svc.find_by_id(200)
        assert signal is not None
        assert signal.signal_id == 200


class TestSignalServiceFindUnknownIds:
    """SignalService.find_unknown_ids returns IDs not present in the dataset."""

    def test_all_known(self):
        svc = SignalService(_stub_provider)
        assert svc.find_unknown_ids([100, 200]) == []

    def test_some_unknown(self):
        svc = SignalService(_stub_provider)
        assert svc.find_unknown_ids([100, 999]) == [999]

    def test_all_unknown(self):
        svc = SignalService(_stub_provider)
        assert svc.find_unknown_ids([888, 999]) == [888, 999]

    def test_empty_list(self):
        svc = SignalService(_stub_provider)
        assert svc.find_unknown_ids([]) == []


# ===========================================================================
# MeasurementService — validate_date_range
# ===========================================================================


class TestValidateDateRange:
    """MeasurementService.validate_date_range raises ValueError when from >= to."""

    def test_valid_range(self):
        # Should not raise
        MeasurementService.validate_date_range(datetime(2021, 1, 1), datetime(2021, 12, 31))

    def test_from_after_to(self):
        with pytest.raises(ValueError, match="'from' must be before 'to'"):
            MeasurementService.validate_date_range(datetime(2021, 12, 31), datetime(2021, 1, 1))

    def test_from_equals_to(self):
        with pytest.raises(ValueError, match="'from' must be before 'to'"):
            MeasurementService.validate_date_range(datetime(2021, 6, 15), datetime(2021, 6, 15))


# ===========================================================================
# MeasurementService — filtering
# ===========================================================================


class TestFilterBySignalId:
    """get_measurements filters results to the requested signal_ids."""

    def test_single_signal(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100])
        assert result.count == 3
        assert all(m.signal_id == 100 for m in result.measurements)

    def test_multiple_signals(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100, 200])
        assert result.count == 4

    def test_unknown_signal(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([999])
        assert result.count == 0
        assert result.measurements == []


class TestFilterByDateRange:
    """get_measurements applies from_date/to_date filters correctly."""

    def test_from_and_to(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements(
            [100, 200],
            from_date=datetime(2021, 11, 8, 0, 0, 0),
            to_date=datetime(2021, 11, 9, 0, 0, 0),
        )
        assert result.count == 1
        assert result.measurements[0].signal_id == 200

    def test_from_only(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements(
            [100],
            from_date=datetime(2021, 11, 7, 10, 30),
        )
        # 11:00 and 12:00 pass
        assert result.count == 2

    def test_to_only(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements(
            [100],
            to_date=datetime(2021, 11, 7, 10, 30),
        )
        # Only 10:00 passes
        assert result.count == 1

    def test_no_date_filter(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100])
        assert result.count == 3


# ===========================================================================
# MeasurementService — get_measurements
# ===========================================================================


class TestGetMeasurements:
    """get_measurements returns a paginated MeasurementList with total/count."""

    def test_returns_measurement_list(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100])
        assert isinstance(result, MeasurementList)
        assert result.total == 3
        assert result.count == 3
        assert len(result.measurements) == 3

    def test_passes_date_filters(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements(
            [100],
            from_date=datetime(2021, 11, 7, 10, 30),
            to_date=datetime(2021, 11, 7, 12, 30),
        )
        assert result.total == 2
        assert result.count == 2

    def test_empty_result(self):
        svc = _make_empty_measurement_svc()
        result = svc.get_measurements([999])
        assert result.total == 0
        assert result.count == 0
        assert result.measurements == []

    def test_default_pagination(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100])
        assert result.limit == 1000
        assert result.offset == 0

    def test_custom_limit(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], limit=2)
        assert result.total == 3
        assert result.count == 2
        assert result.limit == 2
        assert len(result.measurements) == 2

    def test_custom_offset(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], offset=1)
        assert result.total == 3
        assert result.count == 2
        assert result.offset == 1

    def test_limit_and_offset(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], limit=1, offset=1)
        assert result.total == 3
        assert result.count == 1
        assert result.measurements[0].value == 200.0

    def test_offset_beyond_results(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], offset=100)
        assert result.total == 3
        assert result.count == 0
        assert result.measurements == []


# ===========================================================================
# MeasurementService — get_measurements (flat format)
# ===========================================================================


class TestGetMeasurementsFlat:
    """get_measurements with fmt=FLAT returns a FlatMeasurementList."""

    def test_returns_flat_measurement_list(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], fmt=ResponseFormat.FLAT)
        assert isinstance(result, FlatMeasurementList)

    def test_parallel_arrays_length(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], fmt=ResponseFormat.FLAT)
        assert len(result.timestamps) == 3
        assert len(result.signal_ids) == 3
        assert len(result.values) == 3

    def test_values_match_objects_format(self):
        svc = _make_measurement_svc()
        obj_result = svc.get_measurements([100], fmt=ResponseFormat.OBJECTS)
        flat_result = svc.get_measurements([100], fmt=ResponseFormat.FLAT)
        assert flat_result.timestamps == [m.timestamp for m in obj_result.measurements]
        assert flat_result.signal_ids == [m.signal_id for m in obj_result.measurements]
        assert flat_result.values == [m.value for m in obj_result.measurements]

    def test_pagination_metadata(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], fmt=ResponseFormat.FLAT)
        assert result.total == 3
        assert result.count == 3
        assert result.limit == 1000
        assert result.offset == 0

    def test_custom_limit(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], limit=2, fmt=ResponseFormat.FLAT)
        assert result.total == 3
        assert result.count == 2
        assert len(result.values) == 2

    def test_custom_offset(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100], offset=1, fmt=ResponseFormat.FLAT)
        assert result.total == 3
        assert result.count == 2
        assert len(result.values) == 2

    def test_empty_result(self):
        svc = _make_empty_measurement_svc()
        result = svc.get_measurements([999], fmt=ResponseFormat.FLAT)
        assert result.total == 0
        assert result.count == 0
        assert result.timestamps == []
        assert result.signal_ids == []
        assert result.values == []

    def test_date_filters_applied(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements(
            [100],
            from_date=datetime(2021, 11, 7, 10, 30),
            to_date=datetime(2021, 11, 7, 12, 30),
            fmt=ResponseFormat.FLAT,
        )
        assert result.total == 2
        assert result.count == 2

    def test_default_format_is_objects(self):
        svc = _make_measurement_svc()
        result = svc.get_measurements([100])
        assert isinstance(result, MeasurementList)


# ===========================================================================
# MeasurementService — calculate_signal_stats
# ===========================================================================


class TestCalculateSignalStats:
    """calculate_signal_stats computes count/mean/min/max/median/std_dev."""

    def test_returns_signal_stats(self):
        svc = _make_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert isinstance(result, SignalStats)

    def test_count(self):
        svc = _make_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.count == 3

    def test_mean(self):
        svc = _make_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.mean == 200.0

    def test_min_max(self):
        svc = _make_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.min == 100.0
        assert result.max == 300.0

    def test_median(self):
        svc = _make_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.median == 200.0

    def test_std_dev(self):
        svc = _make_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.std_dev == 100.0

    def test_empty_range(self):
        svc = _make_empty_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.count == 0
        assert result.mean is None
        assert result.min is None
        assert result.max is None
        assert result.median is None
        assert result.std_dev is None

    def test_single_measurement_std_dev_zero(self):
        svc = _make_measurement_svc([_MEASUREMENTS[0]])
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.std_dev == 0.0

    def test_min_not_first_element(self):
        """Covers the ``min_val = v`` branch when min appears after the first row."""
        measurements = [
            MeasurementTuple(timestamp=datetime(2021, 11, 7, 10, 0), signal_id=100, value=300.0),
            MeasurementTuple(timestamp=datetime(2021, 11, 7, 11, 0), signal_id=100, value=50.0),
            MeasurementTuple(timestamp=datetime(2021, 11, 7, 12, 0), signal_id=100, value=200.0),
        ]
        svc = _make_measurement_svc(measurements)
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.min == 50.0
        assert result.max == 300.0

    def test_dates_in_result(self):
        svc = _make_measurement_svc()
        from_dt = datetime(2021, 1, 1)
        to_dt = datetime(2021, 12, 31)
        result = svc.calculate_signal_stats(100, from_dt, to_dt)
        assert result.from_date == from_dt
        assert result.to_date == to_dt

    def test_signal_id_in_result(self):
        svc = _make_measurement_svc()
        result = svc.calculate_signal_stats(100, datetime(2021, 1, 1), datetime(2021, 12, 31))
        assert result.signal_id == 100


# ===========================================================================
# Index caching
# ===========================================================================


class TestServiceIndexCaching:
    """MeasurementService builds a signal_id index lazily and reuses it."""

    def test_index_is_built_lazily(self):
        """The index is None until the first query."""
        svc = _make_measurement_svc()
        assert svc._index is None
        svc.get_measurements([100])
        assert svc._index is not None

    def test_index_is_reused_across_calls(self):
        """Multiple queries reuse the same index (provider called once)."""
        svc = _make_measurement_svc()
        svc.get_measurements([100])
        first_index = svc._index
        svc.get_measurements([200])
        assert svc._index is first_index


# ===========================================================================
# Dependency factory functions
# ===========================================================================


class TestGetAssetServiceFactory:
    """get_asset_service dependency factory returns an AssetService."""

    def test_returns_asset_service(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_asset_service.cache_clear()
        svc = get_asset_service()
        assert isinstance(svc, AssetService)

    def test_service_uses_provided_provider(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_asset_service.cache_clear()
        svc = get_asset_service()
        assert len(svc.get_all()) == 2


class TestGetSignalServiceFactory:
    """get_signal_service dependency factory returns a SignalService."""

    def test_returns_signal_service(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_signal_service.cache_clear()
        svc = get_signal_service()
        assert isinstance(svc, SignalService)

    def test_service_uses_provided_provider(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_signal_service.cache_clear()
        svc = get_signal_service()
        assert len(svc.get_all()) == 3


class TestGetMeasurementServiceFactory:
    """get_measurement_service dependency factory returns a MeasurementService."""

    def test_returns_measurement_service(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_measurement_service.cache_clear()
        svc = get_measurement_service()
        assert isinstance(svc, MeasurementService)

    def test_service_uses_provided_provider(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_measurement_service.cache_clear()
        svc = get_measurement_service()
        result = svc.get_measurements([100])
        assert result.count == 3
