"""Signal service — business logic for signal lookups.

Lazily builds dictionary indexes on first access for O(1) lookups
by ``signal_id`` and ``asset_id``.
"""

from collections import defaultdict

from models.signal import Signal
from providers.base import DataProvider


class SignalService:
    """Provides signal lookup operations.

    Indexes are built lazily on first access and cached for subsequent
    calls, giving O(1) lookups instead of scanning the full signal list.

    Args:
        provider: The data provider to load signals from.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider
        self._by_id: dict[int, Signal] | None = None
        self._by_asset_id: dict[int, list[Signal]] | None = None
        self._known_ids: set[int] | None = None

    # ------------------------------------------------------------------
    # Lazy indexes
    # ------------------------------------------------------------------

    def _ensure_indexes(self) -> None:
        """Build all indexes from the provider data if not yet cached."""
        if self._by_id is not None:
            return
        by_id: dict[int, Signal] = {}
        by_asset: dict[int, list[Signal]] = defaultdict(list)
        for s in self._provider.load_signals():
            by_id[s.signal_id] = s
            by_asset[s.asset_id].append(s)
        self._by_id = by_id
        self._by_asset_id = dict(by_asset)
        self._known_ids = set(by_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all(self) -> list[Signal]:
        """Return all signals."""
        return self._provider.load_signals()

    def find_by_id(self, signal_id: int) -> Signal | None:
        """Return the signal with the given ID, or ``None`` if not found.  O(1)."""
        self._ensure_indexes()
        assert self._by_id is not None  # appeases type checker
        return self._by_id.get(signal_id)

    def find_by_asset_id(self, asset_id: int) -> list[Signal]:
        """Return all signals belonging to the given asset.  O(1)."""
        self._ensure_indexes()
        assert self._by_asset_id is not None
        return self._by_asset_id.get(asset_id, [])

    def find_unknown_ids(self, signal_ids: list[int]) -> list[int]:
        """Return any IDs from *signal_ids* that don't match a known signal.  O(k)."""
        self._ensure_indexes()
        assert self._known_ids is not None
        return [sid for sid in signal_ids if sid not in self._known_ids]
