"""Tests for route handlers.

All tests use FastAPI's TestClient with dependency overrides so that
no actual data files are needed (test fixture data is inlined).
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import create_app
from conftest import StubProvider
from models.asset import Asset
from models.measurement import Measurement
from models.signal import Signal
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
    Signal(
        signal_g_id="aaa-111",
        signal_id=100,
        signal_name="SIG_A",
        asset_id=1,
        unit="kV",
    ),
    Signal(
        signal_g_id="bbb-222",
        signal_id=200,
        signal_name="SIG_B",
        asset_id=1,
        unit="kW",
    ),
    Signal(
        signal_g_id="ccc-333",
        signal_id=300,
        signal_name="SIG_C",
        asset_id=2,
        unit="kV",
    ),
]

_MEASUREMENTS = [
    Measurement(timestamp=datetime(2021, 11, 7, 10, 0), signal_id=100, value=100.0),
    Measurement(timestamp=datetime(2021, 11, 7, 11, 0), signal_id=100, value=200.0),
]

_stub_provider = StubProvider(
    signals=_SIGNALS,
    assets=_ASSETS,
    measurements=_MEASUREMENTS,
)


@pytest.fixture()
def client():
    """TestClient with dependency overrides for the services."""
    app = create_app()
    app.dependency_overrides[get_asset_service] = lambda: AssetService(_stub_provider)
    app.dependency_overrides[get_signal_service] = lambda: SignalService(_stub_provider)
    app.dependency_overrides[get_measurement_service] = lambda: MeasurementService(_stub_provider)
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    """GET /health returns 200 with status ok."""

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


class TestGetAssets:
    """GET /assets returns all assets with correct fields."""

    def test_status(self, client):
        r = client.get("/assets")
        assert r.status_code == 200

    def test_returns_list(self, client):
        r = client.get("/assets")
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_asset_fields(self, client):
        r = client.get("/assets")
        a = r.json()[0]
        assert a["asset_id"] == 1
        assert a["latitude"] == 47.5
        assert a["longitude"] == 8.2
        assert a["description"] == "UW Alpha"


class TestGetAssetSignals:
    """GET /assets/{id}/signals returns signals for a given asset, or 404."""

    def test_signals_for_asset_1(self, client):
        r = client.get("/assets/1/signals")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert all(s["asset_id"] == 1 for s in data)

    def test_signals_for_asset_2(self, client):
        r = client.get("/assets/2/signals")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["signal_id"] == 300

    def test_unknown_asset_404(self, client):
        r = client.get("/assets/999/signals")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class TestGetSignals:
    """GET /signals returns all signals."""

    def test_status(self, client):
        r = client.get("/signals")
        assert r.status_code == 200

    def test_returns_all_signals(self, client):
        r = client.get("/signals")
        assert len(r.json()) == 3


class TestGetSignal:
    """GET /signals/{id} returns a single signal or 404."""

    def test_found(self, client):
        r = client.get("/signals/100")
        assert r.status_code == 200
        assert r.json()["signal_id"] == 100

    def test_not_found(self, client):
        r = client.get("/signals/999")
        assert r.status_code == 404


class TestGetSignalStats:
    """GET /signals/{id}/stats with required date params, or 400/404/422."""

    def test_success(self, client):
        r = client.get("/signals/100/stats?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2
        assert data["mean"] == 150.0

    def test_unknown_signal_404(self, client):
        r = client.get("/signals/999/stats?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 404

    def test_bad_date_range_400(self, client):
        r = client.get("/signals/100/stats?from=2021-12-31T00:00:00&to=2021-01-01T00:00:00")
        assert r.status_code == 400

    def test_missing_from_422(self, client):
        r = client.get("/signals/100/stats?to=2021-12-31T00:00:00")
        assert r.status_code == 422

    def test_missing_to_422(self, client):
        r = client.get("/signals/100/stats?from=2021-01-01T00:00:00")
        assert r.status_code == 422


class TestGetSignalMeasurements:
    """GET /signals/{id}/measurements with required dates and pagination."""

    def test_success(self, client):
        r = client.get("/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2
        assert data["total"] == 2
        assert data["limit"] == 1000
        assert data["offset"] == 0

    def test_unknown_signal_404(self, client):
        r = client.get("/signals/999/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 404

    def test_bad_date_range_400(self, client):
        r = client.get("/signals/100/measurements?from=2021-12-31T00:00:00&to=2021-01-01T00:00:00")
        assert r.status_code == 400

    def test_missing_from_422(self, client):
        r = client.get("/signals/100/measurements?to=2021-12-31T00:00:00")
        assert r.status_code == 422

    def test_missing_to_422(self, client):
        r = client.get("/signals/100/measurements?from=2021-01-01T00:00:00")
        assert r.status_code == 422

    def test_missing_both_dates_422(self, client):
        r = client.get("/signals/100/measurements")
        assert r.status_code == 422

    def test_pagination_params(self, client):
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&limit=1&offset=0"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["count"] == 1
        assert data["limit"] == 1
        assert data["offset"] == 0

    def test_limit_validation(self, client):
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&limit=0"
        )
        assert r.status_code == 422
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&limit=10001"
        )
        assert r.status_code == 422

    def test_offset_validation(self, client):
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&offset=-1"
        )
        assert r.status_code == 422


class TestGetSignalMeasurementsFlat:
    """GET /signals/{id}/measurements?format=flat returns parallel arrays."""

    def test_flat_format(self, client):
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=flat"
        )
        assert r.status_code == 200
        data = r.json()
        assert "timestamps" in data
        assert "signal_ids" in data
        assert "values" in data
        assert "measurements" not in data
        assert data["count"] == 2
        assert len(data["timestamps"]) == 2
        assert len(data["signal_ids"]) == 2
        assert len(data["values"]) == 2

    def test_flat_pagination_metadata(self, client):
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=flat"
        )
        data = r.json()
        assert data["total"] == 2
        assert data["limit"] == 1000
        assert data["offset"] == 0

    def test_objects_format_explicit(self, client):
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=objects"
        )
        assert r.status_code == 200
        data = r.json()
        assert "measurements" in data
        assert "timestamps" not in data

    def test_default_format_is_objects(self, client):
        r = client.get("/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        data = r.json()
        assert "measurements" in data
        assert "timestamps" not in data

    def test_invalid_format_422(self, client):
        r = client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=invalid"
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Measurements (multi-signal)
# ---------------------------------------------------------------------------


class TestGetMeasurements:
    """GET /measurements with signal_ids, required dates, and pagination."""

    def test_success(self, client):
        r = client.get(
            "/measurements?signal_ids=100,200&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2
        assert data["total"] == 2
        assert data["limit"] == 1000
        assert data["offset"] == 0

    def test_missing_signal_ids_422(self, client):
        r = client.get("/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 422

    def test_bad_date_range_400(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-12-31T00:00:00&to=2021-01-01T00:00:00"
        )
        assert r.status_code == 400

    def test_missing_from_422(self, client):
        r = client.get("/measurements?signal_ids=100&to=2021-12-31T00:00:00")
        assert r.status_code == 422

    def test_missing_to_422(self, client):
        r = client.get("/measurements?signal_ids=100&from=2021-01-01T00:00:00")
        assert r.status_code == 422

    def test_missing_both_dates_422(self, client):
        r = client.get("/measurements?signal_ids=100")
        assert r.status_code == 422

    def test_empty_signal_ids_400(self, client):
        r = client.get("/measurements?signal_ids=&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 400

    def test_non_integer_signal_ids_400(self, client):
        r = client.get(
            "/measurements?signal_ids=abc&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 400
        assert "integers" in r.json()["detail"]

    def test_unknown_signal_ids_404(self, client):
        r = client.get(
            "/measurements?signal_ids=999&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 404
        assert "999" in r.json()["detail"]

    def test_mix_known_and_unknown_signal_ids_404(self, client):
        r = client.get(
            "/measurements?signal_ids=100,999&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 404
        assert "999" in r.json()["detail"]

    def test_pagination_params(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&limit=1&offset=1"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["count"] == 1
        assert data["limit"] == 1
        assert data["offset"] == 1

    def test_limit_validation(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&limit=0"
        )
        assert r.status_code == 422
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&limit=10001"
        )
        assert r.status_code == 422

    def test_offset_validation(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&offset=-1"
        )
        assert r.status_code == 422


class TestGetMeasurementsFlat:
    """GET /measurements?format=flat returns parallel arrays."""

    def test_flat_format(self, client):
        r = client.get(
            "/measurements?signal_ids=100,200&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=flat"
        )
        assert r.status_code == 200
        data = r.json()
        assert "timestamps" in data
        assert "signal_ids" in data
        assert "values" in data
        assert "measurements" not in data
        assert data["count"] == 2
        assert len(data["timestamps"]) == 2

    def test_flat_pagination_metadata(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=flat"
        )
        data = r.json()
        assert data["total"] == 2
        assert data["limit"] == 1000
        assert data["offset"] == 0

    def test_objects_format_explicit(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=objects"
        )
        assert r.status_code == 200
        data = r.json()
        assert "measurements" in data
        assert "timestamps" not in data

    def test_default_format_is_objects(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        data = r.json()
        assert "measurements" in data
        assert "timestamps" not in data

    def test_invalid_format_422(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00&format=invalid"
        )
        assert r.status_code == 422
