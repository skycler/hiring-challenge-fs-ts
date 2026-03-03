"""Tests for settings module."""

import os
from unittest.mock import patch

from settings import Settings


class TestDefaults:
    """Verify default setting values."""

    def test_app_name(self):
        s = Settings()
        assert s.app_name == "AssetAPI"

    def test_api_version(self):
        s = Settings()
        assert s.api_version == "v1"

    def test_debug_off_by_default(self):
        s = Settings()
        assert s.debug is False

    def test_signals_path(self):
        s = Settings()
        assert s.signals_path == "data/signal.json"

    def test_assets_path(self):
        s = Settings()
        assert s.assets_path == "data/assets.json"

    def test_measurements_path(self):
        s = Settings()
        assert s.measurements_path == "data/measurements.csv"


class TestEnvironmentOverride:
    """Settings can be overridden via environment variables."""

    def test_override_app_name(self):
        with patch.dict(os.environ, {"APP_NAME": "TestApp"}):
            s = Settings()
        assert s.app_name == "TestApp"

    def test_override_debug(self):
        with patch.dict(os.environ, {"DEBUG": "true"}):
            s = Settings()
        assert s.debug is True

    def test_override_signals_path(self):
        with patch.dict(os.environ, {"SIGNALS_PATH": "/tmp/signals.json"}):
            s = Settings()
        assert s.signals_path == "/tmp/signals.json"

    def test_override_assets_path(self):
        with patch.dict(os.environ, {"ASSETS_PATH": "/tmp/assets.json"}):
            s = Settings()
        assert s.assets_path == "/tmp/assets.json"

    def test_override_measurements_path(self):
        with patch.dict(os.environ, {"MEASUREMENTS_PATH": "/tmp/m.csv"}):
            s = Settings()
        assert s.measurements_path == "/tmp/m.csv"


class TestGetCaching:
    """Settings.get() returns a cached singleton."""

    def test_get_returns_settings(self):
        Settings.get.cache_clear()
        s = Settings.get()
        assert isinstance(s, Settings)

    def test_get_is_cached(self):
        Settings.get.cache_clear()
        s1 = Settings.get()
        s2 = Settings.get()
        assert s1 is s2
