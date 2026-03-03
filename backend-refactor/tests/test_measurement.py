"""Tests for models.measurement.Measurement and MeasurementList."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from models.measurement import Measurement, MeasurementList

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
    "signal_id": "427038",
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


class TestFromAliasKeys:
    def test_construct_from_alias_keys(self, alias_record):
        m = Measurement(**alias_record)
        assert m.signal_id == "427038"
        assert m.value == pytest.approx(116.129)
        assert isinstance(m.timestamp, datetime)

    def test_model_validate_from_alias_keys(self, alias_record):
        m = Measurement.model_validate(alias_record)
        assert m.signal_id == "427038"

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


class TestFromSnakeCaseKeys:
    def test_construct_from_snake_case(self, snake_record):
        m = Measurement(**snake_record)
        assert m.signal_id == "427038"
        assert m.value == pytest.approx(116.129)

    def test_model_validate_from_snake_case(self, snake_record):
        m = Measurement.model_validate(snake_record)
        assert m.signal_id == "427038"


# ---------------------------------------------------------------------------
# Type coercion
# ---------------------------------------------------------------------------


class TestTypeCoercion:
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
            signal_id="427038",
            value=116.129,
        )
        assert m.timestamp == datetime(2021, 11, 7, 23, 59, 3)

    def test_aware_datetime_accepted(self):
        ts = datetime(2021, 11, 7, 23, 59, 3, tzinfo=UTC)
        m = Measurement(timestamp=ts, signal_id="427038", value=0.0)
        assert m.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
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


class TestValidation:
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


class TestEquality:
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
    {"Ts": "2023-01-15T10:30:00", "SignalId": "100001", "MeasurementValue": 230.5},
    {"Ts": "2023-01-15T10:31:00", "SignalId": "100001", "MeasurementValue": 231.0},
    {"Ts": "2023-01-15T10:32:00", "SignalId": "100001", "MeasurementValue": 229.8},
]


class TestMeasurementListConstruction:
    def test_construct_with_measurements(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(count=3, measurements=items)
        assert ml.count == 3
        assert len(ml.measurements) == 3

    def test_construct_empty(self):
        ml = MeasurementList(count=0, measurements=[])
        assert ml.count == 0
        assert ml.measurements == []

    def test_model_validate(self):
        data = {
            "count": 2,
            "measurements": SAMPLE_MEASUREMENTS[:2],
        }
        ml = MeasurementList.model_validate(data)
        assert ml.count == 2
        assert ml.measurements[0].value == pytest.approx(230.5)


class TestMeasurementListSerialization:
    def test_dump_contains_nested_measurements(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(count=3, measurements=items)
        d = ml.model_dump()
        assert d["count"] == 3
        assert len(d["measurements"]) == 3
        assert "value" in d["measurements"][0]

    def test_json_round_trip(self):
        items = [Measurement(**m) for m in SAMPLE_MEASUREMENTS]
        ml = MeasurementList(count=3, measurements=items)
        json_str = ml.model_dump_json()
        ml2 = MeasurementList.model_validate_json(json_str)
        assert ml == ml2


class TestMeasurementListValidation:
    def test_missing_count_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(measurements=[])

    def test_missing_measurements_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(count=0)

    def test_invalid_measurement_in_list_raises(self):
        with pytest.raises(ValidationError):
            MeasurementList(
                count=1,
                measurements=[{"bad": "data"}],
            )
