"""Tests for models.asset.Asset."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from models.asset import Asset

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
def single_record() -> dict:
    return deepcopy(ASSET_RECORDS[0])


# ---------------------------------------------------------------------------
# Construction from alias (PascalCase) keys
# ---------------------------------------------------------------------------


class TestFromAliasKeys:
    def test_construct_from_alias_keys(self, single_record):
        a = Asset(**single_record)
        assert a.asset_id == "1"
        assert a.description == "UW Beznau"

    def test_latitude_longitude_are_floats(self, single_record):
        """Source JSON has these as strings — Pydantic should coerce to float."""
        a = Asset(**single_record)
        assert isinstance(a.latitude, float)
        assert isinstance(a.longitude, float)
        assert a.latitude == pytest.approx(47.5568277613)
        assert a.longitude == pytest.approx(8.2338560914)

    def test_all_three_records_parse(self, asset_records):
        assets = [Asset(**r) for r in asset_records]
        assert len(assets) == 3
        assert {a.asset_id for a in assets} == {"1", "2", "3"}

    def test_model_validate_from_alias_keys(self, single_record):
        a = Asset.model_validate(single_record)
        assert a.asset_id == single_record["AssetID"]


# ---------------------------------------------------------------------------
# Construction from snake_case keys (populate_by_name=True)
# ---------------------------------------------------------------------------


class TestFromSnakeCaseKeys:
    def test_construct_from_snake_case(self):
        a = Asset(
            asset_id="99",
            latitude=47.0,
            longitude=8.0,
            description="Test Station",
        )
        assert a.asset_id == "99"
        assert a.description == "Test Station"

    def test_model_validate_from_snake_case(self):
        a = Asset.model_validate(
            {
                "asset_id": "99",
                "latitude": 47.0,
                "longitude": 8.0,
                "description": "Test Station",
            }
        )
        assert a.latitude == 47.0


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_dump_uses_snake_case_by_default(self, single_record):
        a = Asset(**single_record)
        d = a.model_dump()
        assert "asset_id" in d
        assert "AssetID" not in d
        assert "description" in d
        assert "descri" not in d

    def test_dump_by_alias(self, single_record):
        a = Asset(**single_record)
        d = a.model_dump(by_alias=True)
        assert "AssetID" in d
        assert "asset_id" not in d
        assert "descri" in d
        assert "description" not in d

    def test_json_round_trip_by_alias(self, single_record):
        a = Asset(**single_record)
        json_str = a.model_dump_json(by_alias=True)
        a2 = Asset.model_validate_json(json_str)
        assert a == a2

    def test_json_round_trip_by_field_name(self, single_record):
        a = Asset(**single_record)
        json_str = a.model_dump_json()
        a2 = Asset.model_validate_json(json_str)
        assert a == a2


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestValidation:
    def test_missing_field_raises(self, single_record):
        bad = deepcopy(single_record)
        del bad["AssetID"]
        with pytest.raises(ValidationError):
            Asset(**bad)

    @pytest.mark.parametrize("field", ["AssetID", "Latitude", "Longitude", "descri"])
    def test_each_required_field(self, single_record, field):
        bad = deepcopy(single_record)
        del bad[field]
        with pytest.raises(ValidationError):
            Asset(**bad)

    def test_latitude_non_numeric_raises(self, single_record):
        bad = {**single_record, "Latitude": "not-a-number"}
        with pytest.raises(ValidationError):
            Asset(**bad)

    def test_longitude_non_numeric_raises(self, single_record):
        bad = {**single_record, "Longitude": "not-a-number"}
        with pytest.raises(ValidationError):
            Asset(**bad)


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


class TestEquality:
    def test_equal_instances(self, single_record):
        a = Asset(**single_record)
        b = Asset(**single_record)
        assert a == b

    def test_different_instances(self, asset_records):
        a = Asset(**asset_records[0])
        b = Asset(**asset_records[1])
        assert a != b
