"""Tests for route handlers.

All tests use FastAPI's TestClient with dependency overrides so that
no actual data files are needed (test fixture data is inlined).
"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import create_app
from conftest import StubProvider
from models.asset import Asset
from models.measurement import MeasurementTuple
from models.signal import Signal
from services import get_asset_service, get_measurement_service, get_signal_service
from services.asset import AssetService
from services.measurement import MeasurementService
from services.signal import SignalService
from settings import Settings

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
    MeasurementTuple(timestamp=datetime(2021, 11, 7, 10, 0), signal_id=100, value=100.0),
    MeasurementTuple(timestamp=datetime(2021, 11, 7, 11, 0), signal_id=100, value=200.0),
]

_stub_provider = StubProvider(
    signals=_SIGNALS,
    assets=_ASSETS,
    measurements=_MEASUREMENTS,
)


@pytest.fixture()
def client(monkeypatch):
    """TestClient with dependency overrides for the services.

    The lifespan warmup calls the ``get_*_service()`` factories directly
    (outside FastAPI DI), so we monkeypatch the underlying provider to
    use stub data and clear the lru_caches first.  The context manager
    form ensures lifespan startup/shutdown events fire.
    """
    monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
    get_asset_service.cache_clear()
    get_signal_service.cache_clear()
    get_measurement_service.cache_clear()

    app = create_app()
    app.dependency_overrides[get_asset_service] = lambda: AssetService(_stub_provider)
    app.dependency_overrides[get_signal_service] = lambda: SignalService(_stub_provider)
    app.dependency_overrides[get_measurement_service] = lambda: MeasurementService(_stub_provider)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_asset_service.cache_clear()
    get_signal_service.cache_clear()
    get_measurement_service.cache_clear()


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


# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------


class TestSignalIdsCap:
    """GET /measurements rejects more than 100 signal_ids."""

    def test_too_many_signal_ids_400(self, client):
        ids = ",".join(str(i) for i in range(101))
        r = client.get(
            f"/measurements?signal_ids={ids}&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 400
        assert "Too many signal_ids" in r.json()["detail"]

    def test_exactly_100_signal_ids_accepted(self, client):
        """100 IDs is within the cap (will 404 because most are unknown, but not 400)."""
        ids = ",".join(str(i) for i in range(100))
        r = client.get(
            f"/measurements?signal_ids={ids}&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        # Should not be 400 for "Too many"; will be 404 because most IDs are unknown
        assert r.status_code != 400 or "Too many" not in r.json().get("detail", "")


class TestErrorMessageSanitization:
    """Error messages must not use repr() to avoid leaking internal details."""

    def test_signal_404_message_no_repr(self, client):
        r = client.get("/signals/999")
        assert r.status_code == 404
        detail = r.json()["detail"]
        assert detail == "Signal 999 not found"

    def test_asset_404_message_no_repr(self, client):
        r = client.get("/assets/999/signals")
        assert r.status_code == 404
        detail = r.json()["detail"]
        assert detail == "Asset 999 not found"

    def test_measurement_unknown_ids_message_format(self, client):
        r = client.get(
            "/measurements?signal_ids=888,999&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 404
        detail = r.json()["detail"]
        assert detail == "Signal(s) 888, 999 not found"

    def test_signal_stats_404_message(self, client):
        r = client.get("/signals/999/stats?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 404
        assert r.json()["detail"] == "Signal 999 not found"

    def test_signal_measurements_404_message(self, client):
        r = client.get("/signals/999/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 404
        assert r.json()["detail"] == "Signal 999 not found"


class TestFileNotFoundHandler:
    """FileNotFoundError at runtime returns 503 with a generic message."""

    def test_503_on_file_not_found(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_asset_service.cache_clear()
        get_signal_service.cache_clear()
        get_measurement_service.cache_clear()

        app = create_app()

        def _exploding_get_all():
            raise FileNotFoundError("data/signal.json")

        bad_signal_svc = SignalService(_stub_provider)
        bad_signal_svc.get_all = _exploding_get_all  # type: ignore[assignment]

        app.dependency_overrides[get_asset_service] = lambda: AssetService(_stub_provider)
        app.dependency_overrides[get_signal_service] = lambda: bad_signal_svc
        app.dependency_overrides[get_measurement_service] = lambda: MeasurementService(
            _stub_provider
        )
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/signals")
        assert r.status_code == 503
        assert r.json()["detail"] == "Service temporarily unavailable"
        app.dependency_overrides.clear()
        get_asset_service.cache_clear()
        get_signal_service.cache_clear()
        get_measurement_service.cache_clear()


class TestDocsDisabledInProduction:
    """When debug=False, /docs, /redoc, and /openapi.json are disabled."""

    def test_docs_disabled(self, client):
        """Default debug=False should disable docs endpoints."""
        r = client.get("/docs")
        assert r.status_code == 404

    def test_redoc_disabled(self, client):
        r = client.get("/redoc")
        assert r.status_code == 404

    def test_openapi_disabled(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 404


class TestDocsEnabledInDebug:
    """When debug=True, /docs, /redoc, and /openapi.json are available."""

    def test_docs_available_in_debug(self, monkeypatch):
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_asset_service.cache_clear()
        get_signal_service.cache_clear()
        get_measurement_service.cache_clear()
        Settings.get.cache_clear()
        with patch.dict(os.environ, {"DEBUG": "true"}):
            Settings.get.cache_clear()
            app = create_app()
            app.dependency_overrides[get_asset_service] = lambda: AssetService(_stub_provider)
            app.dependency_overrides[get_signal_service] = lambda: SignalService(_stub_provider)
            app.dependency_overrides[get_measurement_service] = lambda: MeasurementService(
                _stub_provider
            )
            with TestClient(app) as c:
                r = c.get("/docs")
                assert r.status_code == 200
                r = c.get("/openapi.json")
                assert r.status_code == 200
            app.dependency_overrides.clear()
        Settings.get.cache_clear()
        get_asset_service.cache_clear()
        get_signal_service.cache_clear()
        get_measurement_service.cache_clear()


# ---------------------------------------------------------------------------
# Security attack simulation tests
# ---------------------------------------------------------------------------


class TestNegativeAndZeroIds:
    """Negative and zero IDs are syntactically valid ints but semantically invalid."""

    def test_signal_negative_id_404(self, client):
        r = client.get("/signals/-1")
        assert r.status_code == 404

    def test_signal_zero_id_404(self, client):
        r = client.get("/signals/0")
        assert r.status_code == 404

    def test_asset_negative_id_404(self, client):
        r = client.get("/assets/-1/signals")
        assert r.status_code == 404

    def test_asset_zero_id_404(self, client):
        r = client.get("/assets/0/signals")
        assert r.status_code == 404

    def test_measurement_negative_signal_id_404(self, client):
        r = client.get(
            "/measurements?signal_ids=-1&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 404

    def test_measurement_zero_signal_id_404(self, client):
        r = client.get(
            "/measurements?signal_ids=0&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 404

    def test_signal_stats_negative_id_404(self, client):
        r = client.get("/signals/-1/stats?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 404

    def test_signal_measurements_negative_id_404(self, client):
        r = client.get("/signals/-1/measurements?from=2021-01-01T00:00:00&to=2021-12-31T00:00:00")
        assert r.status_code == 404


class TestDuplicateSignalIds:
    """Duplicate signal_ids should not cause server errors."""

    def test_duplicate_ids_no_error(self, client):
        r = client.get(
            "/measurements?signal_ids=100,100,100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 200

    def test_duplicate_ids_cause_repeated_results(self, client):
        """Duplicates are processed per-occurrence — total is a multiple of the single count.

        This documents current behaviour: the service iterates over signal_ids
        as given, so duplicates produce repeated measurements.  A future
        deduplication step could change this.
        """
        r_single = client.get(
            "/measurements?signal_ids=100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        r_dup = client.get(
            "/measurements?signal_ids=100,100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        single_total = r_single.json()["total"]
        dup_total = r_dup.json()["total"]
        assert dup_total == single_total * 2


class TestTrailingLeadingCommas:
    """Edge cases in signal_ids comma parsing."""

    def test_leading_comma(self, client):
        r = client.get(
            "/measurements?signal_ids=,100&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 200

    def test_trailing_comma(self, client):
        r = client.get(
            "/measurements?signal_ids=100,&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 200

    def test_multiple_commas_only_400(self, client):
        """Only commas and no actual IDs should return 400."""
        r = client.get(
            "/measurements?signal_ids=,,,&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 400
        assert "At least one signal_id" in r.json()["detail"]

    def test_spaces_between_ids(self, client):
        r = client.get(
            "/measurements?signal_ids=%20100%20,%20200%20&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 200


class TestVeryLargeIntegerIds:
    """Extremely large integers should not crash the server."""

    def test_huge_signal_id_in_path_404(self, client):
        r = client.get("/signals/99999999999999999999999999")
        assert r.status_code == 404

    def test_huge_asset_id_in_path_404(self, client):
        r = client.get("/assets/99999999999999999999999999/signals")
        assert r.status_code == 404

    def test_huge_signal_id_in_query_404(self, client):
        r = client.get(
            "/measurements?signal_ids=99999999999999999999999999"
            "&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 404

    def test_huge_offset_returns_empty(self, client):
        r = client.get(
            "/measurements?signal_ids=100"
            "&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
            "&offset=999999999"
        )
        assert r.status_code == 200
        assert r.json()["count"] == 0


class TestHttpMethodRestriction:
    """Only GET is allowed — POST/PUT/DELETE/PATCH must return 405."""

    _ENDPOINTS = [
        "/health",
        "/assets",
        "/assets/1/signals",
        "/signals",
        "/signals/100",
        "/signals/100/stats",
        "/signals/100/measurements",
        "/measurements",
    ]

    @pytest.mark.parametrize("endpoint", _ENDPOINTS)
    def test_post_returns_405(self, client, endpoint):
        r = client.post(endpoint)
        assert r.status_code == 405

    @pytest.mark.parametrize("endpoint", _ENDPOINTS)
    def test_put_returns_405(self, client, endpoint):
        r = client.put(endpoint)
        assert r.status_code == 405

    @pytest.mark.parametrize("endpoint", _ENDPOINTS)
    def test_delete_returns_405(self, client, endpoint):
        r = client.delete(endpoint)
        assert r.status_code == 405

    @pytest.mark.parametrize("endpoint", _ENDPOINTS)
    def test_patch_returns_405(self, client, endpoint):
        r = client.patch(endpoint)
        assert r.status_code == 405


class TestFromEqualsToAtRouteLevel:
    """from == to should return 400 at the route level, not 200 with empty results."""

    def test_signal_stats_equal_dates_400(self, client):
        r = client.get("/signals/100/stats?from=2021-06-15T00:00:00&to=2021-06-15T00:00:00")
        assert r.status_code == 400

    def test_signal_measurements_equal_dates_400(self, client):
        r = client.get("/signals/100/measurements?from=2021-06-15T00:00:00&to=2021-06-15T00:00:00")
        assert r.status_code == 400

    def test_measurements_equal_dates_400(self, client):
        r = client.get(
            "/measurements?signal_ids=100&from=2021-06-15T00:00:00&to=2021-06-15T00:00:00"
        )
        assert r.status_code == 400


class TestNonIntegerPathParams:
    """Non-integer path parameters should return 422 (framework-enforced)."""

    def test_signal_string_id_422(self, client):
        r = client.get("/signals/abc")
        assert r.status_code == 422

    def test_asset_string_id_422(self, client):
        r = client.get("/assets/abc/signals")
        assert r.status_code == 422

    def test_signal_float_id_422(self, client):
        r = client.get("/signals/1.5")
        assert r.status_code == 422

    def test_asset_float_id_422(self, client):
        r = client.get("/assets/1.5/signals")
        assert r.status_code == 422


class TestTimezoneAwareDatetimes:
    """Timezone-aware datetime inputs vs. naive stored data.

    The stored measurements use naive (timezone-unaware) datetimes.
    Mixing offset-aware query parameters with naive data causes a
    ``TypeError`` in Python's comparison operators.  These tests document
    the current behaviour: the server returns **500** because the
    exception is unhandled.

    A separate ``TestClient(raise_server_exceptions=False)`` is used so
    the 500 is returned as an HTTP response rather than a Python exception.

    TODO: Consider stripping timezone info from query datetimes or storing
    data as UTC-aware to handle this gracefully.
    """

    @pytest.fixture()
    def lenient_client(self, monkeypatch):
        """TestClient that returns 500 responses instead of raising."""
        monkeypatch.setattr("services.get_provider", lambda: _stub_provider)
        get_asset_service.cache_clear()
        get_signal_service.cache_clear()
        get_measurement_service.cache_clear()

        app = create_app()
        app.dependency_overrides[get_asset_service] = lambda: AssetService(_stub_provider)
        app.dependency_overrides[get_signal_service] = lambda: SignalService(_stub_provider)
        app.dependency_overrides[get_measurement_service] = lambda: MeasurementService(
            _stub_provider
        )
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        app.dependency_overrides.clear()
        get_asset_service.cache_clear()
        get_signal_service.cache_clear()
        get_measurement_service.cache_clear()

    def test_utc_z_suffix_not_200(self, lenient_client):
        r = lenient_client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00Z&to=2021-12-31T00:00:00Z"
        )
        # Expect an error status — not silently wrong results.
        assert r.status_code >= 400

    def test_positive_offset_not_200(self, lenient_client):
        r = lenient_client.get(
            "/signals/100/measurements"
            "?from=2021-01-01T00:00:00%2B05:00&to=2021-12-31T00:00:00%2B05:00"
        )
        assert r.status_code >= 400

    def test_negative_offset_not_200(self, lenient_client):
        r = lenient_client.get(
            "/signals/100/measurements?from=2021-01-01T00:00:00-05:00&to=2021-12-31T00:00:00-05:00"
        )
        assert r.status_code >= 400


class TestSqlInjectionStrings:
    """SQL-injection payloads in signal_ids should be rejected as non-integers."""

    def test_or_injection_400(self, client):
        r = client.get(
            "/measurements?signal_ids=1 OR 1=1&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 400
        assert "integers" in r.json()["detail"]

    def test_drop_table_400(self, client):
        r = client.get(
            "/measurements?signal_ids=1;DROP TABLE signals&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 400

    def test_union_select_400(self, client):
        r = client.get(
            "/measurements?signal_ids=1 UNION SELECT * FROM users"
            "&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
        )
        assert r.status_code == 400


class TestUnknownQueryParamsIgnored:
    """Extra/unknown query parameters must be silently ignored."""

    def test_extra_params_on_assets(self, client):
        r = client.get("/assets?admin=true&debug=1")
        assert r.status_code == 200

    def test_extra_params_on_signals(self, client):
        r = client.get("/signals?role=superuser&token=abc")
        assert r.status_code == 200

    def test_extra_params_on_measurements(self, client):
        r = client.get(
            "/measurements?signal_ids=100"
            "&from=2021-01-01T00:00:00&to=2021-12-31T00:00:00"
            "&admin=true&__proto__=polluted"
        )
        assert r.status_code == 200

    def test_extra_params_on_health(self, client):
        r = client.get("/health?verbose=true&debug=1")
        assert r.status_code == 200
