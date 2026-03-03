"""Asset service layer."""

from db.asset_db import get_assets, fetch_assets


class AssetService:
    """Service for managing assets."""

    def get_all_assets(self) -> list[dict]:
        """Get all assets with their signals."""
        return get_assets()

    def fetch_asset(self) -> list[dict]:
        return fetch_assets()
