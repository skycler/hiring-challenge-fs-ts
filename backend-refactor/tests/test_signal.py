"""Tests for models.signal.Signal and SignalStats."""

from copy import deepcopy
from datetime import datetime

import pytest
from pydantic import ValidationError

from models.signal import Signal, SignalStats

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
def single_record() -> dict:
    return deepcopy(SIGNAL_RECORDS[0])


# ---------------------------------------------------------------------------
# Construction from alias (PascalCase) keys — the primary path
# ---------------------------------------------------------------------------


class TestFromAliasKeys:
    def test_construct_from_alias_keys(self, single_record):
        s = Signal(**single_record)
        assert s.signal_g_id == single_record["SignalGId"]
        assert s.signal_id == single_record["SignalId"]
        assert s.signal_name == single_record["SignalName"]
        assert s.asset_id == single_record["AssetId"]
        assert s.unit == single_record["Unit"]

    def test_all_four_records_parse(self, signal_records):
        signals = [Signal(**r) for r in signal_records]
        assert len(signals) == 4
        assert {s.signal_id for s in signals} == {"427038", "427659", "427712", "430247"}

    def test_model_validate_from_alias_keys(self, single_record):
        s = Signal.model_validate(single_record)
        assert s.signal_id == single_record["SignalId"]


# ---------------------------------------------------------------------------
# Construction from snake_case keys (populate_by_name=True)
# ---------------------------------------------------------------------------


class TestFromSnakeCaseKeys:
    def test_construct_from_snake_case(self):
        s = Signal(
            signal_g_id="abc",
            signal_id="123",
            signal_name="TEST",
            asset_id="1",
            unit="kV",
        )
        assert s.signal_id == "123"
        assert s.unit == "kV"

    def test_model_validate_from_snake_case(self):
        s = Signal.model_validate(
            {
                "signal_g_id": "abc",
                "signal_id": "123",
                "signal_name": "TEST",
                "asset_id": "1",
                "unit": "kV",
            }
        )
        assert s.signal_name == "TEST"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_dict_uses_snake_case_by_default(self, single_record):
        s = Signal(**single_record)
        d = s.model_dump()
        assert "signal_id" in d
        assert "SignalId" not in d

    def test_dict_by_alias(self, single_record):
        s = Signal(**single_record)
        d = s.model_dump(by_alias=True)
        assert "SignalId" in d
        assert "signal_id" not in d

    def test_json_round_trip_by_alias(self, single_record):
        s = Signal(**single_record)
        json_str = s.model_dump_json(by_alias=True)
        s2 = Signal.model_validate_json(json_str)
        assert s == s2

    def test_json_round_trip_by_field_name(self, single_record):
        s = Signal(**single_record)
        json_str = s.model_dump_json()
        s2 = Signal.model_validate_json(json_str)
        assert s == s2


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestValidation:
    def test_missing_field_raises(self, single_record):
        bad = deepcopy(single_record)
        del bad["SignalId"]
        with pytest.raises(ValidationError):
            Signal(**bad)

    def test_extra_field_is_ignored_by_default(self, single_record):
        record = {**single_record, "Bogus": "value"}
        s = Signal(**record)
        assert s.signal_id == single_record["SignalId"]

    @pytest.mark.parametrize("field", ["SignalGId", "SignalId", "SignalName", "AssetId", "Unit"])
    def test_each_required_field(self, single_record, field):
        bad = deepcopy(single_record)
        del bad[field]
        with pytest.raises(ValidationError):
            Signal(**bad)


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------


class TestEquality:
    def test_equal_instances(self, single_record):
        a = Signal(**single_record)
        b = Signal(**single_record)
        assert a == b

    def test_different_instances(self, signal_records):
        a = Signal(**signal_records[0])
        b = Signal(**signal_records[1])
        assert a != b


# ===========================================================================
# SignalStats
# ===========================================================================

STATS_WITH_DATA = {
    "signal_id": "100001",
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
    "signal_id": "100001",
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
    def test_construct_with_data(self):
        s = SignalStats(**STATS_WITH_DATA)
        assert s.signal_id == "100001"
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
        assert s.signal_id == "100001"

    def test_numeric_fields_default_to_none(self):
        s = SignalStats(
            signal_id="100001",
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
    def test_dump(self):
        s = SignalStats(**STATS_WITH_DATA)
        d = s.model_dump()
        assert d["signal_id"] == "100001"
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
