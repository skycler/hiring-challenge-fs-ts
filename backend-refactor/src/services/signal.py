"""Signal service — business logic for signal lookups."""

from models.signal import Signal
from providers.base import DataProvider


class SignalService:
    """Provides signal lookup operations.

    Args:
        provider: The data provider to load signals from.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider

    def get_all(self) -> list[Signal]:
        """Return all signals."""
        return self._provider.load_signals()

    def find_by_id(self, signal_id: int) -> Signal | None:
        """Return the signal with the given ID, or ``None`` if not found."""
        for s in self._provider.load_signals():
            if s.signal_id == signal_id:
                return s
        return None

    def find_unknown_ids(self, signal_ids: list[int]) -> list[int]:
        """Return any IDs from *signal_ids* that don't match a known signal."""
        known = {s.signal_id for s in self._provider.load_signals()}
        return [sid for sid in signal_ids if sid not in known]
