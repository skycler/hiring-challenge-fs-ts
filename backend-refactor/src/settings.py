"""Application settings loaded from environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AssetAPI"
    api_version: str = "v1"
    debug: bool = False
    data_path: str = "data/signal.json"

    model_config = {"env_file": ".env"}

    @staticmethod
    @lru_cache
    def get() -> "Settings":
        return Settings()
