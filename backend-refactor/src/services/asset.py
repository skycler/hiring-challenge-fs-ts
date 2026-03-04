"""Asset service — business logic for asset lookups."""

from models.asset import Asset
from providers.base import DataProvider


class AssetService:
    """Provides asset lookup operations.

    Args:
        provider: The data provider to load assets from.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider

    def get_all(self) -> list[Asset]:
        """Return all assets."""
        return self._provider.load_assets()

    def find_by_id(self, asset_id: int) -> Asset | None:
        """Return the asset with the given ID, or ``None`` if not found."""
        for a in self._provider.load_assets():
            if a.asset_id == asset_id:
                return a
        return None
