"""Asset service — business logic for asset lookups.

Lazily builds a dictionary index on first access for O(1) lookups
by ``asset_id``.
"""

from models.asset import Asset
from providers.base import DataProvider


class AssetService:
    """Provides asset lookup operations.

    An ``asset_id -> Asset`` index is built lazily on first :meth:`find_by_id`
    call and cached for subsequent lookups.

    Args:
        provider: The data provider to load assets from.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider
        self._by_id: dict[int, Asset] | None = None

    def _ensure_index(self) -> None:
        """Build the asset-id index if not yet cached."""
        if self._by_id is not None:
            return
        self._by_id = {a.asset_id: a for a in self._provider.load_assets()}

    def get_all(self) -> list[Asset]:
        """Return all assets."""
        return self._provider.load_assets()

    def find_by_id(self, asset_id: int) -> Asset | None:
        """Return the asset with the given ID, or ``None`` if not found.  O(1)."""
        self._ensure_index()
        assert self._by_id is not None
        return self._by_id.get(asset_id)
