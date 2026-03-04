"""Tests for all Pydantic models (Asset, Signal, SignalStats, Measurement, MeasurementList)."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from models.asset import Asset
from models.measurement import Measurement, MeasurementList
from models.signal import Signal, SignalStats

# ===========================================================================
# Asset
# ===========================================================================

# ---------------------------------------------------------------------------
# Fixtures — inline data matching the structure of data/assets.json
# ---------------------------------------------------------------------------

ASSET_RECORDS = [
    {
        "AssetID": "1",
        "Latitude": "47.5568277613",
        "Longitude": "8.2338560914",
        "descri": "UW Beznau",
    },
    {
        "AssetID": "2",
        "Latitude": "47.219215463",
        "Longitude": "8.9728980141",
        "descri": "UW Grynau",
    },
    {
        "AssetID": "3",
        "Latitude": "47.397979458",
        "Longitude": "9.3026581653",
        "descri": "UW Winkeln",
    },
]


@pytest.fixture()
def asset_records() -> list[dict]:
    return [deepcopy(r) for r in ASSET_RECORDS]


@pytest.fixture()
def single_asset_record() -> dict:
    return deepcopy(ASSET_RECORDS[0])


# ---------------------------------------------------------------------------
# Construction from alias (PascalCase) keys
# ---------------------------------------------------------------------------


class TestAssetFromAliasKeys:
    """Construct Asset from PascalCase (alias) keys as found in the source JSON."""

    def test_construct_from_alias_keys(self, single_asset_record):
        a = Asset(**single_asset_record)
        assert a.asset_id == 1
        assert a.description == "UW Beznau"

    def test_latitude_longitude_are_floats(self, single_asset_record):
        """Source JSON has these as strings — Pydantic should coerce to float."""
        a = Asset(**single_asset_record)
        assert isinstance(a.latitude, float)
        assert isinstance(a.longitude, float)
        assert a.latitude == pytest.approx(47.5568277613)
        assert a.longitude == pytest.approx(8.2338560914)

    def test_all_three_records_parse(self, asset_records):
        assets = [Asset(**r) for r in asset_records]
        assert len(assets) == 3
        assert {a.asset_id for a in assets} == {1, 2, 3}

    def test_model_validate_from_alias_keys(self, single_asset_record):
        a = Asset.model_validate(single_asset_record)
        assert a.asset_id == 1


# ---------------------------------------------------------------------------
# Construction from snake_case keys (populate_by_name=True)
# ---------------------------------------------------------------------------


class TestAssetFromSnakeCaseKeys:
    """Construct Asset from snake_case keys (``populate_by_name=True``)."""

    def test_construct_from_snake_case(self):
        a = Asset(
            asset_id=99,
            latitude=47.0,
            longitude=8.0,
            description="Test Station",
        )
        assert a.asset_id == 99
        assert a.description == "Test Station"

    def test_model_validate_from_snake_case(self):
        a = Asset.model_validate(
            {
                "asset_id": 99,
                "latitude": 47.0,
                "longitude": 8.0,
                "description": "Test Station",
            }
        )
        assert a.latitude == 47.0


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestAssetSerialization:
    """Verify Asset serialization via model_dump and JSON round-trips."""

    def test_dump_uses_snake_case_by_default(self, single_asset_record):
        a = Asset(**single_asset_record)
        d = a.model_dump()
        assert "asset_id" in d
        assert "AssetID" not in d
        assert "description" in d
        assert "descri" not in d

    def test_dump_by_alias(self, single_asset_record):
        a = Asset(**single_asset_record)
        d = a.model_dump(by_alias=True)
        assert "AssetID" in d
        assert "asset_id" not in d
        assert "descri" in d
        assert "description" not in d

    def test_json_round_trip_by_alias(self, single_asset_record):
        a = Asset(**single_asset_record)
        json_str = a.model_dump_json(by_alias=True)
        a2 = Asset.model_validate_json(json_str)
        assert a == a2

    def test_json_round_trip_by_field_name(self, single_asset_record):
        a = Asset(**single_asset_record)
        json_str = a.model_dump_json()
        a2 = Asset.model_validate_json(json_str)
        assert a == a2


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestAssetValidation:
    """Ensure missing or invalid fields raise ``ValidationError``."""

    def test_missing_field_raises(self, single_asset_record):
        bad = deepcopy(single_asset_record)
        del bad["AssetID"]
        with pytest.raises(ValidationError):
            Asset(**bad)

    @pytest.mark.parametrize("field", ["AssetID", "Latitude", "Longitude", "descri"])
    def test_each_required_field(self, single_asset_record, field):
        bad = deepcopy(single_asset_record)
        del bad[field]
        with pytest.raises(ValidationError):
            Asset(**bad)

    def test_latitude_non_numeric_raises(self, single_asset_record):
        bad = {**single_asset_record, "Latitude": "not-a-number"}
        with pytest.raises(ValidationError):
            Asset(**bad)

    def test_longitude_non_numeric_raises(self, single_asset_record):
        bad = {**single_asset_record, "Longitude": "not-a-number"}
        with pytest.raises(ValidationError):
            Asset(**bad)


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


class TestAssetEquality:
    """Pydantic model equality based on field values."""

    def test_equal_instances(self, single_asset_record):
        a = Asset(**single_asset_record)
        b = Asset(**single_asset_record)
        assert a == b

    def test_different_instances(self, asset_records):
        a = Asset(**asset_records[0])
        b = Asset(**asset_records[1])
        assert a != b


# ===========================================================================
# Signal
# ===========================================================================

# ---------------------------------------------------------------------------
# Fixtures — inline data matching the structure of data/signal.json
# ---------------------------------------------------------------------------

SIGNAL_RECORDS = [
    {
        "SignalGId": "045ad75f-d8c7-4c92-b252-05f515e4006f",
        "SignalId": "427038",
        "SignalName": "BEZOBF110BIRMENU_L12",
        "AssetId": "1",
        "Unit": "kV",
    },
    {
        "SignalGId": "beb78c41-96a9-48f8-b77f-62f21366814a",
        "SignalId": "427659",
        "SignalName": "GRYAAT110JONA++U_L12",
        "AssetId": "2",
        "Unit": "kV",
    },
    {
        "SignalGId": "566a7ca6-d9d0-463d-829c-cd9a2d9e4f2f",
        "SignalId": "427712",
        "SignalName": "GRYAAT110TR_1++P",
        "AssetId": "2",
        "Unit": "kW",
    },
    {
        "SignalGId": "29291fed-663e-432b-8305-4f5b8d661115",
        "SignalId": "430247",
        "SignalName": "WINMON110WIDNAUU_L12",
        "AssetId": "3",
        "Unit": "kV",
    },
]


@pytest.fixture()
def signal_records() -> list[dict]:
    return [deepcopy(r) for r in SIGNAL_RECORDS]


@pytest.fixture()
def single_signal_record() -> dict:
    return deepcopy(SIGNAL_RECORDS[0])


# ---------------------------------------------------------------------------
# Construction from alias (PascalCase) keys — the primary path
# ---------------------------------------------------------------------------


class TestSignalFromAliasKeys:
    """Construct Signal from PascalCase (alias) keys."""

    def test_construct_from_alias_keys(self, single_signal_record):
        s = Signal(**single_signal_record)
        assert s.signal_g_id == single_signal_record["SignalGId"]
        assert s.signal_id == 427038
        assert s.signal_name == single_signal_record["SignalName"]
        assert s.asset_id == 1
        assert s.unit == single_signal_record["Unit"]

    def test_all_four_records_parse(self, signal_records):
        signals = [Signal(**r) for r in signal_records]
        assert len(signals) == 4
        assert {s.signal_id for s in signals} == {427038, 427659, 427712, 430247}

    def test_model_validate_from_alias_keys(self, single_signal_record):
        s = Signal.model_validate(single_signal_record)
        assert s.signal_id == 427038


# ---------------------------------------------------------------------------
# Construction from snake_case keys (populate_by_name=True)
# ---------------------------------------------------------------------------


class TestSignalFromSnakeCaseKeys:
    """Construct Signal from snake_case keys (``populate_by_name=True``)."""

    def test_construct_from_snake_case(self):
        s = Signal(
            signal_g_id="abc",
            signal_id=123,
            signal_name="TEST",
            asset_id=1,
            unit="kV",
        )
        assert s.signal_id == 123
        assert s.unit == "kV"

    def test_model_validate_from_snake_case(self):
        s = Signal.model_validate(
            {
                "signal_g_id": "abc",
                "signal_id": 123,
                "signal_name": "TEST",
                "asset_id": 1,
                "unit": "kV",
            }
        )
        assert s.signal_name == "TEST"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSignalSerialization:
    """Verify Signal serialization via model_dump and JSON round-trips."""

    def test_dict_uses_snake_case_by_default(self, single_signal_record):
        s = Signal(**single_signal_record)
        d = s.model_dump()
        assert "signal_id" in d
        assert "SignalId" not in d

    def test_dict_by_alias(self, single_signal_record):
        s = Signal(**single_signal_record)
        d = s.model_dump(by_alias=True)
        assert "SignalId" in d
        assert "signal_id" not in d

    def test_json_round_trip_by_alias(self, single_signal_record):
        s = Signal(**single_signal_record)
        json_str = s.model_dump_json(by_alias=True)
        s2 = Signal.model_validate_json(json_str)
        assert s == s2

    def test_json_round_trip_by_field_name(self, single_signal_record):
        s = Signal(**single_signal_record)
        json_str = s.model_dump_json()
        s2 = Signal.model_validate_json(json_str)
        assert s == s2


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestSignalValidation:
    """Ensure missing or invalid fields raise ``ValidationError``."""

    def test_missing_field_raises(self, single_signal_record):
        bad = deepcopy(single_signal_record)
        del bad["SignalId"]
        with pytest.raises(ValidationError):
            Signal(**bad)

    def test_extra_field_is_ignored_by_default(self, single_signal_record):
        record = {**single_signal_record, "Bogus": "value"}
        s = Signal(**record)
        assert s.signal_id == 427038

    @pytest.mark.parametrize("field", ["SignalGId", "SignalId", "SignalName", "AssetId", "Unit"])
    def test_each_required_field(self, single_signal_record, field):
        bad = deepcopy(single_signal_record)
        del bad[field]
        with pytest.raises(ValidationError):
            Signal(**bad)


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------


class TestSignalEquality:
    """Pydantic model equality based on field values."""

    def test_equal_instances(self, single_signal_record):
        a = Signal(**single_signal_record)
        b = Signal(**single_signal_record)
        assert a == b

    def test_different_instances(self, signal_records):
        a = Signal(**signal_records[0])
        b = Signal(**signal_records[1])
        assert a != b


# ===========================================================================
# SignalStats
# ===========================================================================

STATS_WITH_DATA = {
    "signal_id": 100001,
    "from_date": "2023-01-01T00:00:00",
    "to_date": "2023-01-31T23:59:59",
    "count": 150,
    "mean": 225.75,
    "min": 110.0,
    "max": 340.5,
    "median": 228.0,
    "std_dev": 42.3,
}

STATS_EMPTY = {
    "signal_id": 100001,
    "from_date": "2023-06-01T00:00:00",
    "to_date": "2023-06-30T23:59:59",
    "count": 0,
    "mean": None,
    "min": None,
    "max": None,
    "median": None,
    "std_dev": None,
}


class TestSignalStatsConstruction:
    """Construct SignalStats with data and without (empty range)."""

    def test_construct_with_data(self):
        s = SignalStats(**STATS_WITH_DATA)
        assert s.signal_id == 100001
        assert s.count == 150
        assert s.mean == pytest.approx(225.75)
        assert s.min == pytest.approx(110.0)
        assert s.max == pytest.approx(340.5)
        assert s.median == pytest.approx(228.0)
        assert s.std_dev == pytest.approx(42.3)

    def test_construct_empty_range(self):
        s = SignalStats(**STATS_EMPTY)
        assert s.count == 0
        assert s.mean is None
        assert s.min is None
        assert s.max is None
        assert s.median is None
        assert s.std_dev is None

    def test_dates_parsed(self):
        s = SignalStats(**STATS_WITH_DATA)
        assert isinstance(s.from_date, datetime)
        assert isinstance(s.to_date, datetime)
        assert s.from_date.year == 2023
        assert s.to_date.month == 1

    def test_model_validate(self):
        s = SignalStats.model_validate(STATS_WITH_DATA)
        assert s.signal_id == 100001

    def test_numeric_fields_default_to_none(self):
        s = SignalStats(
            signal_id=100001,
            from_date="2023-01-01T00:00:00",
            to_date="2023-01-31T23:59:59",
            count=0,
        )
        assert s.mean is None
        assert s.min is None
        assert s.max is None
        assert s.median is None
        assert s.std_dev is None


class TestSignalStatsSerialization:
    """Verify SignalStats dump and JSON round-trip behaviour."""

    def test_dump(self):
        s = SignalStats(**STATS_WITH_DATA)
        d = s.model_dump()
        assert d["signal_id"] == 100001
        assert d["count"] == 150
        assert d["mean"] == pytest.approx(225.75)

    def test_dump_empty_range_has_nones(self):
        s = SignalStats(**STATS_EMPTY)
        d = s.model_dump()
        assert d["mean"] is None
        assert d["min"] is None

    def test_json_round_trip(self):
        s = SignalStats(**STATS_WITH_DATA)
        json_str = s.model_dump_json()
        s2 = SignalStats.model_validate_json(json_str)
        assert s == s2

    def test_json_round_trip_empty(self):
        s = SignalStats(**STATS_EMPTY)
        json_str = s.model_dump_json()
        s2 = SignalStats.model_validate_json(json_str)
        assert s == s2


class TestSignalStatsValidation:
    """Ensure missing or invalid fields raise ``ValidationError``."""

    def test_missing_signal_id_raises(self):
        bad = deepcopy(STATS_WITH_DATA)
        del bad["signal_id"]
        with pytest.raises(ValidationError):
            SignalStats(**bad)

    def test_missing_count_raises(self):
        bad = deepcopy(STATS_WITH_DATA)
        del bad["count"]
        with pytest.raises(ValidationError):
            SignalStats(**bad)

    def test_missing_from_date_raises(self):
        bad = deepcopy(STATS_WITH_DATA)
        del bad["from_date"]
        with pytest.raises(ValidationError):
            SignalStats(**bad)

    def test_missing_to_date_raises(self):
        bad = deepcopy(STATS_WITH_DATA)
        del bad["to_date"]
        with pytest.raises(ValidationError):
            SignalStats(**bad)

    def test_invalid_date_raises(self):
        bad = {**STATS_WITH_DATA, "from_date": "not-a-date"}
        with pytest.raises(ValidationError):
            SignalStats(**bad)

    def test_non_numeric_mean_raises(self):
        bad = {**STATS_WITH_DATA, "mean": "not-a-number"}
        with pytest.raises(ValidationError):
            SignalStats(**bad)


# ===========================================================================
# Measurement
# ===========================================================================

# ---------------------------------------------------------------------------
# Fixtures — representative data matching measurements.csv structure
# ---------------------------------------------------------------------------

SAMPLE_ALIAS = {
    "Ts": "2021-11-07T23:59:03.762000",
    "SignalId": "427038",
    "MeasurementValue": 116.129,
}

SAMPLE_SNAKE = {
    "timestamp": "2021-11-07T23:59:03.762000",
    "signal_id": 427038,
    "value": 116.129,
}


@pytest.fixture()
def alias_record() -> dict:
    return deepcopy(SAMPLE_ALIAS)


@pytest.fixture()
def snake_record() -> dict:
    return deepcopy(SAMPLE_SNAKE)


# ---------------------------------------------------------------------------
# Construction from alias keys
# ---------------------------------------------------------------------------


class TestMeasurementFromAliasKeys:
    """Construct Measurement from PascalCase (alias) keys."""

    def test_construct_from_alias_keys(self, alias_record):
        m = Measurement(**alias_record)
        assert m.signal_id == 427038
        assert m.value == pytest.approx(116.129)
        assert isinstance(m.timestamp, datetime)

    def test_model_validate_from_alias_keys(self, alias_record):
        m = Measurement.model_validate(alias_record)
        assert m.signal_id == 427038

    def test_timestamp_parsed_correctly(self, alias_record):
        m = Measurement(**alias_record)
        assert m.timestamp.year == 2021
        assert m.timestamp.month == 11
        assert m.timestamp.day == 7
        assert m.timestamp.hour == 23
        assert m.timestamp.minute == 59
        assert m.timestamp.second == 3


# ---------------------------------------------------------------------------
# Construction from snake_case keys
# ---------------------------------------------------------------------------


class TestMeasurementFromSnakeCaseKeys:
    """Construct Measurement from snake_case keys."""

    def test_construct_from_snake_case(self, snake_record):
        m = Measurement(**snake_record)
        assert m.signal_id == 427038
        assert m.value == pytest.approx(116.129)

    def test_model_validate_from_snake_case(self, snake_record):
        m = Measurement.model_validate(snake_record)
        assert m.signal_id == 427038


# ---------------------------------------------------------------------------
# Type coercion
# ---------------------------------------------------------------------------


class TestMeasurementTypeCoercion:
    """Pydantic should coerce compatible types (str/int to float, etc.)."""

    def test_string_value_coerced_to_float(self, alias_record):
        alias_record["MeasurementValue"] = "99.5"
        m = Measurement(**alias_record)
        assert m.value == 99.5

    def test_int_value_coerced_to_float(self, alias_record):
        alias_record["MeasurementValue"] = 100
        m = Measurement(**alias_record)
        assert m.value == 100.0
        assert isinstance(m.value, float)

    def test_datetime_object_accepted(self):
        m = Measurement(
            timestamp=datetime(2021, 11, 7, 23, 59, 3),
            signal_id=427038,
            value=116.129,
        )
        assert m.timestamp == datetime(2021, 11, 7, 23, 59, 3)

    def test_aware_datetime_accepted(self):
        ts = datetime(2021, 11, 7, 23, 59, 3, tzinfo=UTC)
        m = Measurement(timestamp=ts, signal_id=427038, value=0.0)
        assert m.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestMeasurementSerialization:
    """Verify Measurement dump and JSON round-trip behaviour."""

    def test_dump_uses_snake_case_by_default(self, alias_record):
        m = Measurement(**alias_record)
        d = m.model_dump()
        assert "signal_id" in d
        assert "SignalId" not in d
        assert "timestamp" in d
        assert "Ts" not in d
        assert "value" in d
        assert "MeasurementValue" not in d

    def test_dump_by_alias(self, alias_record):
        m = Measurement(**alias_record)
        d = m.model_dump(by_alias=True)
        assert "SignalId" in d
        assert "Ts" in d
        assert "MeasurementValue" in d

    def test_json_round_trip_by_alias(self, alias_record):
        m = Measurement(**alias_record)
        json_str = m.model_dump_json(by_alias=True)
        m2 = Measurement.model_validate_json(json_str)
        assert m == m2

    def test_json_round_trip_by_field_name(self, alias_record):
        m = Measurement(**alias_record)
        json_str = m.model_dump_json()
        m2 = Measurement.model_validate_json(json_str)
        assert m == m2


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestMeasurementValidation:
    """Ensure missing or invalid fields raise ``ValidationError``."""

    def test_missing_signal_id_raises(self, alias_record):
        del alias_record["SignalId"]
        with pytest.raises(ValidationError):
            Measurement(**alias_record)

    def test_missing_timestamp_raises(self, alias_record):
        del alias_record["Ts"]
        with pytest.raises(ValidationError):
            Measurement(**alias_record)

    def test_missing_value_raises(self, alias_record):
        del alias_record["MeasurementValue"]
        with pytest.raises(ValidationError):
            Measurement(**alias_record)

    def test_non_numeric_value_raises(self, alias_record):
        alias_record["MeasurementValue"] = "not-a-number"
        with pytest.raises(ValidationError):
            Measurement(**alias_record)

    def test_invalid_timestamp_raises(self, alias_record):
        alias_record["Ts"] = "not-a-date"
        with pytest.raises(ValidationError):
            Measurement(**alias_record)

    @pytest.mark.parametrize("field", ["Ts", "SignalId", "MeasurementValue"])
    def test_each_required_field(self, alias_record, field):
        bad = deepcopy(alias_record)
        del bad[field]
        with pytest.raises(ValidationError):
            Measurement(**bad)


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


class TestMeasurementEquality:
    """Pydantic model equality based on field values."""

    def test_equal_instances(self, alias_record):
        a = Measurement(**alias_record)
        b = Measurement(**alias_record)
        assert a == b

    def test_different_value(self, alias_record):
        a = Measurement(**alias_record)
        other = {**alias_record, "MeasurementValue": 0.0}
        b = Measurement(**other)
        assert a != b


# ===========================================================================
# MeasurementList
# ===========================================================================

SAMPLE_MEASUREMENTS = [
    {"Ts": "2023-01-15T10:30:00", "SignalId": 100001, "MeasurementValue": 230.5},
    {"Ts": "2023-01-15T10:31:00", "SignalId": 100001, "MeasurementValue": 231.0},
    {"Ts": "2023-01-15T10:32:00", "SignalId": 100001, "MeasurementValue": 229.8},
]


class TestMeasurementListConstruction:
    """Construct MeasurementList with items and empty."""

    def test_construct_with_measurements(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(total=3, count=3, limit=1000, offset=0, measurements=items)
        assert ml.count == 3
        assert len(ml.measurements) == 3

    def test_construct_empty(self):
        ml = MeasurementList(total=0, count=0, limit=1000, offset=0, measurements=[])
        assert ml.count == 0
        assert ml.measurements == []

    def test_model_validate(self):
        data = {
            "total": 2,
            "count": 2,
            "limit": 1000,
            "offset": 0,
            "measurements": SAMPLE_MEASUREMENTS[:2],
        }
        ml = MeasurementList.model_validate(data)
        assert ml.count == 2
        assert ml.measurements[0].value == pytest.approx(230.5)

    def test_pagination_fields(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(total=50, count=3, limit=10, offset=20, measurements=items)
        assert ml.total == 50
        assert ml.limit == 10
        assert ml.offset == 20


class TestMeasurementListSerialization:
    """Verify MeasurementList dump and JSON round-trip behaviour."""

    def test_dump_contains_nested_measurements(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(total=3, count=3, limit=1000, offset=0, measurements=items)
        d = ml.model_dump()
        assert d["count"] == 3
        assert len(d["measurements"]) == 3
        assert "value" in d["measurements"][0]

    def test_json_round_trip(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(total=3, count=3, limit=1000, offset=0, measurements=items)
        json_str = ml.model_dump_json()
        ml2 = MeasurementList.model_validate_json(json_str)
        assert ml == ml2

    def test_dump_contains_pagination_fields(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(total=100, count=3, limit=10, offset=5, measurements=items)
        d = ml.model_dump()
        assert d["total"] == 100
        assert d["limit"] == 10
        assert d["offset"] == 5


class TestMeasurementListValidation:
    """Ensure all pagination fields and measurements are required."""

    def test_missing_count_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(total=0, limit=1000, offset=0, measurements=[])

    def test_missing_measurements_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(total=0, count=0, limit=1000, offset=0)

    def test_invalid_measurement_in_list_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(
                total=1,
                count=1,
                limit=1000,
                offset=0,
                measurements=[{"bad": "data"}],
            )

    def test_missing_total_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(count=0, limit=1000, offset=0, measurements=[])

    def test_missing_limit_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(total=0, count=0, offset=0, measurements=[])

    def test_missing_offset_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(total=0, count=0, limit=1000, measurements=[])
