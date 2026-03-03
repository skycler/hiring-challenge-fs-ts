"""Application settings loaded from environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AssetAPI"
    api_version: str = "v1"
    debug: bool = False
    signals_path: str = "data/signal.json"
    assets_path: str = "data/assets.json"
    measurements_path: str = "data/measurements.csv"

    model_config = {"env_file": ".env"}

    @staticmethod
    @lru_cache
    def get() -> "Settings":
        return Settings()
