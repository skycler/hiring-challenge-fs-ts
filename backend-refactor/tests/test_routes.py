"""Tests for route handlers.

All tests use FastAPI's TestClient with dependency overrides so that
no actual data files are needed (test fixture data is inlined).
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import create_app
from models.asset import Asset
from models.measurement import Measurement
from models.signal import Signal
from providers import get_provider
from providers.base import DataProvider
from services import get_measurement_service
from services.measurement_svc import MeasurementService

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


class _StubProvider(DataProvider):
    """In-memory provider for route tests."""

    def load_signals(self) -> list[Signal]:
        return _SIGNALS

    def load_assets(self) -> list[Asset]:
        return _ASSETS

    def load_measurements(self) -> list[Measurement]:
        return _MEASUREMENTS


_stub_provider = _StubProvider()


@pytest.fixture()
def client():
    """TestClient with dependency overrides for the provider and service."""
    app = create_app()
    app.dependency_overrides[get_provider] = lambda: _stub_provider
    app.dependency_overrides[get_measurement_service] = lambda: MeasurementService(_stub_provider)
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


class TestGetAssets:
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
    def test_status(self, client):
        r = client.get("/signals")
        assert r.status_code == 200

    def test_returns_all_signals(self, client):
        r = client.get("/signals")
        assert len(r.json()) == 3


class TestGetSignal:
    def test_found(self, client):
        r = client.get("/signals/100")
        assert r.status_code == 200
        assert r.json()["signal_id"] == 100

    def test_not_found(self, client):
        r = client.get("/signals/999")
        assert r.status_code == 404


class TestGetSignalStats:
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
    def test_success(self, client):
        r = client.get("/signals/100/measurements")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2

    def test_unknown_signal_404(self, client):
        r = client.get("/signals/999/measurements")
        assert r.status_code == 404

    def test_bad_date_range_400(self, client):
        r = client.get("/signals/100/measurements?from=2021-12-31T00:00:00&to=2021-01-01T00:00:00")
        assert r.status_code == 400

    def test_optional_date_params(self, client):
        r = client.get("/signals/100/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Measurements (multi-signal)
# ---------------------------------------------------------------------------


class TestGetMeasurements:
    def test_success(self, client):
        r = client.get("/measurements?signal_ids=100,200")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2

    def test_missing_signal_ids_422(self, client):
        r = client.get("/measurements")
        assert r.status_code == 422

    def test_bad_date_range_400(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-12-31T00:00:00&to=2021-01-01T00:00:00"
        )
        assert r.status_code == 400

    def test_empty_signal_ids_400(self, client):
        r = client.get("/measurements?signal_ids=")
        assert r.status_code == 400

    def test_non_integer_signal_ids_400(self, client):
        r = client.get("/measurements?signal_ids=abc")
        assert r.status_code == 400
        assert "integers" in r.json()["detail"]
