"""Application settings loaded from environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables and ``.env``."""

    app_name: str = "AssetAPI"
    api_version: str = "v1"
    debug: bool = False
    data_dir: str = "data"
    signals_path: str = "data/signal.json"
    assets_path: str = "data/assets.json"
    measurements_path: str = "data/measurements.csv"

    model_config = {"env_file": ".env"}

    #: Immutable project root – the directory that contains ``pyproject.toml``
    #: (two levels up from this file: ``src/settings.py`` → project root).
    _PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

    def validate_path(self, path: str) -> Path:
        """Resolve *path* and ensure it lives inside :attr:`data_dir`.

        The data directory itself must first be verified to live inside the
        project root.  This prevents an attacker from setting
        ``DATA_DIR=/`` to widen the sandbox to the entire filesystem.

        Returns the resolved :class:`~pathlib.Path` on success.

        Raises:
            ValueError: If *data_dir* escapes the project root **or** the
                resolved *path* escapes *data_dir*.
        """
        project_root = self._PROJECT_ROOT
        base = Path(self.data_dir).resolve()
        if not base.is_relative_to(project_root):
            raise ValueError(f"data_dir {self.data_dir!r} resolves outside the project root")
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(base):
            raise ValueError(f"Path {path!r} resolves outside the data directory")
        return resolved

    @staticmethod
    @lru_cache
    def get() -> "Settings":
        """Return the application-wide settings singleton.

        Backed by :func:`functools.lru_cache` so the instance is created
        only once.  Call ``Settings.get.cache_clear()`` in tests to reset.
        """
        return Settings()
