"""Tests for the providers package.

Covers:
- DataProvider ABC contract (cannot be instantiated directly)
- FileSystemProvider: signal/asset/measurement loading, caching
- get_provider singleton behaviour
"""

import json
import textwrap
from datetime import datetime
from unittest.mock import mock_open, patch

import pytest

from models.asset import Asset
from models.measurement import MeasurementTuple
from models.signal import Signal
from providers import get_provider
from providers.base import DataProvider
from providers.filesystem import FileSystemProvider
from settings import Settings

# ---------------------------------------------------------------------------
# Inline fixtures
# ---------------------------------------------------------------------------

SIGNAL_JSON = json.dumps(
    [
        {
            "SignalGId": "aaa-111",
            "SignalId": "100",
            "SignalName": "SIG_A",
            "AssetId": "1",
            "Unit": "kV",
        },
        {
            "SignalGId": "bbb-222",
            "SignalId": "200",
            "SignalName": "SIG_B",
            "AssetId": "1",
            "Unit": "kW",
        },
        {
            "SignalGId": "ccc-333",
            "SignalId": "300",
            "SignalName": "SIG_C",
            "AssetId": "2",
            "Unit": "kV",
        },
    ]
)

ASSET_JSON = json.dumps(
    [
        {
            "AssetID": "1",
            "Latitude": "47.5",
            "Longitude": "8.2",
            "descri": "UW Alpha",
        },
        {
            "AssetID": "2",
            "Latitude": "47.2",
            "Longitude": "8.9",
            "descri": "UW Beta",
        },
    ]
)

MEASUREMENT_CSV = textwrap.dedent("""\
    Ts|SignalId|MeasurementValue
    2021-11-07 23:59:03.762|100|116,129
    2021-11-07 23:57:48.259|100|115,958
    2021-11-08 10:00:00.000|200|230,5
""")


# ---------------------------------------------------------------------------
# DataProvider ABC
# ---------------------------------------------------------------------------


class TestDataProviderABC:
    """DataProvider cannot be instantiated; subclasses must implement all methods."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            DataProvider()  # type: ignore[abstract]

    def test_subclass_must_implement_load_signals(self):
        class Incomplete(DataProvider):
            def load_assets(self):
                return []

            def load_measurements(self):
                return []

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_must_implement_load_assets(self):
        class Incomplete(DataProvider):
            def load_signals(self):
                return []

            def load_measurements(self):
                return []

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_must_implement_load_measurements(self):
        class Incomplete(DataProvider):
            def load_signals(self):
                return []

            def load_assets(self):
                return []

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_complete_subclass_instantiates(self):
        class Complete(DataProvider):
            def load_signals(self):
                return []

            def load_assets(self):
                return []

            def load_measurements(self):
                return []

        provider = Complete()
        assert isinstance(provider, DataProvider)


# ---------------------------------------------------------------------------
# FileSystemProvider — signals
# ---------------------------------------------------------------------------


class TestFileSystemProviderSignals:
    """FileSystemProvider.load_signals: parsing, caching, and error handling."""

    def test_returns_list_of_signal(self):
        m = mock_open(read_data=SIGNAL_JSON)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_signals()
        assert len(result) == 3
        assert all(isinstance(s, Signal) for s in result)

    def test_first_signal_fields(self):
        m = mock_open(read_data=SIGNAL_JSON)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_signals()
        s = result[0]
        assert s.signal_id == 100
        assert s.signal_name == "SIG_A"
        assert s.asset_id == 1
        assert s.unit == "kV"

    def test_empty_file(self):
        m = mock_open(read_data="[]")
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_signals()
        assert result == []

    def test_caching(self):
        m = mock_open(read_data=SIGNAL_JSON)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            r1 = provider.load_signals()
            r2 = provider.load_signals()
        assert r1 is r2
        m.assert_called_once()

    def test_file_not_found(self):
        provider = FileSystemProvider()
        with (
            patch("providers.filesystem.open", side_effect=FileNotFoundError),
            pytest.raises(FileNotFoundError),
        ):
            provider.load_signals()

    def test_invalid_json(self):
        m = mock_open(read_data="NOT VALID JSON")
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m), pytest.raises(json.JSONDecodeError):
            provider.load_signals()


# ---------------------------------------------------------------------------
# FileSystemProvider — assets
# ---------------------------------------------------------------------------


class TestFileSystemProviderAssets:
    """FileSystemProvider.load_assets: parsing, caching, and error handling."""

    def test_returns_list_of_asset(self):
        m = mock_open(read_data=ASSET_JSON)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_assets()
        assert len(result) == 2
        assert all(isinstance(a, Asset) for a in result)

    def test_first_asset_fields(self):
        m = mock_open(read_data=ASSET_JSON)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_assets()
        a = result[0]
        assert a.asset_id == 1
        assert a.latitude == 47.5
        assert a.longitude == 8.2
        assert a.description == "UW Alpha"

    def test_empty_file(self):
        m = mock_open(read_data="[]")
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_assets()
        assert result == []

    def test_caching(self):
        m = mock_open(read_data=ASSET_JSON)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            r1 = provider.load_assets()
            r2 = provider.load_assets()
        assert r1 is r2
        m.assert_called_once()

    def test_file_not_found(self):
        provider = FileSystemProvider()
        with (
            patch("providers.filesystem.open", side_effect=FileNotFoundError),
            pytest.raises(FileNotFoundError),
        ):
            provider.load_assets()

    def test_invalid_json(self):
        m = mock_open(read_data="{bad json}")
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m), pytest.raises(json.JSONDecodeError):
            provider.load_assets()


# ---------------------------------------------------------------------------
# FileSystemProvider — measurements
# ---------------------------------------------------------------------------


class TestFileSystemProviderMeasurements:
    """FileSystemProvider.load_measurements: CSV parsing, caching, and error handling."""

    def test_returns_list_of_measurement(self):
        m = mock_open(read_data=MEASUREMENT_CSV)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_measurements()
        assert len(result) == 3
        assert all(isinstance(r, MeasurementTuple) for r in result)

    def test_european_comma_parsed(self):
        m = mock_open(read_data=MEASUREMENT_CSV)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_measurements()
        assert result[0].value == 116.129
        assert result[1].value == 115.958

    def test_timestamp_parsed(self):
        m = mock_open(read_data=MEASUREMENT_CSV)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_measurements()
        assert result[0].timestamp == datetime(2021, 11, 7, 23, 59, 3, 762000)

    def test_signal_id_parsed(self):
        m = mock_open(read_data=MEASUREMENT_CSV)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            result = provider.load_measurements()
        assert result[0].signal_id == 100
        assert result[2].signal_id == 200

    def test_caching(self):
        m = mock_open(read_data=MEASUREMENT_CSV)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m):
            r1 = provider.load_measurements()
            r2 = provider.load_measurements()
        assert r1 is r2
        m.assert_called_once()

    def test_file_not_found(self):
        provider = FileSystemProvider()
        with (
            patch("providers.filesystem.open", side_effect=FileNotFoundError),
            pytest.raises(FileNotFoundError),
        ):
            provider.load_measurements()

    def test_malformed_csv_missing_column(self):
        bad_csv = "Ts|WrongColumn\n2021-11-07 23:59:03.762|100\n"
        m = mock_open(read_data=bad_csv)
        provider = FileSystemProvider()
        with patch("providers.filesystem.open", m), pytest.raises(KeyError):
            provider.load_measurements()

    def test_csv_row_limit_exceeded(self, tmp_path, monkeypatch):
        """Loading more than MAX_MEASUREMENT_ROWS raises ValueError."""
        from providers.filesystem import MAX_MEASUREMENT_ROWS

        monkeypatch.setattr(Settings, "_PROJECT_ROOT", tmp_path)
        # Create a tiny settings where data_dir covers tmp_path
        csv_file = tmp_path / "measurements.csv"
        header = "Ts|SignalId|MeasurementValue\n"
        row = "2021-11-07 23:59:03.762|100|116,129\n"
        csv_file.write_text(header + row * (MAX_MEASUREMENT_ROWS + 1))

        settings = Settings(
            data_dir=str(tmp_path),
            measurements_path=str(csv_file),
        )
        provider = FileSystemProvider(settings=settings)
        with pytest.raises(ValueError, match="CSV exceeds maximum"):
            provider.load_measurements()

    def test_path_traversal_blocked_json(self, tmp_path, monkeypatch):
        """_load_json rejects paths outside the data directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setattr(Settings, "_PROJECT_ROOT", tmp_path)
        evil_path = str(tmp_path / "data" / ".." / "etc" / "passwd")
        settings = Settings(data_dir=str(data_dir), signals_path=evil_path)
        provider = FileSystemProvider(settings=settings)
        with pytest.raises(ValueError, match="resolves outside"):
            provider.load_signals()

    def test_path_traversal_blocked_csv(self, tmp_path, monkeypatch):
        """load_measurements rejects paths outside the data directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setattr(Settings, "_PROJECT_ROOT", tmp_path)
        evil_path = str(tmp_path / "data" / ".." / "etc" / "passwd")
        settings = Settings(data_dir=str(data_dir), measurements_path=evil_path)
        provider = FileSystemProvider(settings=settings)
        with pytest.raises(ValueError, match="resolves outside"):
            provider.load_measurements()

    def test_path_traversal_blocked_assets(self, tmp_path, monkeypatch):
        """load_assets rejects paths outside the data directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setattr(Settings, "_PROJECT_ROOT", tmp_path)
        evil_path = str(tmp_path / "data" / ".." / "etc" / "passwd")
        settings = Settings(data_dir=str(data_dir), assets_path=evil_path)
        provider = FileSystemProvider(settings=settings)
        with pytest.raises(ValueError, match="resolves outside"):
            provider.load_assets()

    def test_csv_formula_injection_rejected(self, tmp_path, monkeypatch):
        """CSV cells containing spreadsheet formula payloads fail float conversion."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setattr(Settings, "_PROJECT_ROOT", tmp_path)
        csv_file = data_dir / "measurements.csv"
        csv_file.write_text(
            'Ts|SignalId|MeasurementValue\n2021-11-07 23:59:03.762|100|=CMD("calc")\n'
        )
        settings = Settings(
            data_dir=str(data_dir),
            measurements_path=str(csv_file),
        )
        provider = FileSystemProvider(settings=settings)
        with pytest.raises(ValueError):
            provider.load_measurements()


# ---------------------------------------------------------------------------
# get_provider singleton
# ---------------------------------------------------------------------------


class TestGetProvider:
    """get_provider returns a singleton FileSystemProvider instance."""

    def setup_method(self):
        # Reset the module-level singleton before each test
        import providers

        providers._provider = None

    def test_returns_filesystem_provider(self):
        with patch("providers.filesystem.open", mock_open(read_data="[]")):
            provider = get_provider()
        assert isinstance(provider, FileSystemProvider)

    def test_singleton(self):
        with patch("providers.filesystem.open", mock_open(read_data="[]")):
            p1 = get_provider()
            p2 = get_provider()
        assert p1 is p2

    def test_reset_creates_new_instance(self):
        import providers

        with patch("providers.filesystem.open", mock_open(read_data="[]")):
            p1 = get_provider()
            providers._provider = None
            p2 = get_provider()
        assert p1 is not p2
