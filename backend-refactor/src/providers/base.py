"""Abstract data provider interface.

Defines the contract for loading domain data.  Concrete implementations
handle the *where* (filesystem, database, API …) while the rest of the
application works against this interface.
"""

from abc import ABC, abstractmethod

from models.asset import Asset
from models.measurement import Measurement
from models.signal import Signal


class DataProvider(ABC):
    """Abstract base class for data providers.

    Every provider must implement three pure loader methods.  They return
    *complete* datasets — filtering is the service layer's responsibility.
    """

    @abstractmethod
    def load_signals(self) -> list[Signal]:
        """Return all signals."""

    @abstractmethod
    def load_assets(self) -> list[Asset]:
        """Return all assets."""

    @abstractmethod
    def load_measurements(self) -> list[Measurement]:
        """Return all measurements."""
