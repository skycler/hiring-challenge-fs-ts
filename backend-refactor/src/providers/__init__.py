"""Providers package -- data access abstraction.

Re-exports the :class:`DataProvider` interface and the
:class:`FileSystemProvider` implementation, plus a lazily-initialised
singleton via :func:`get_provider`.
"""

from providers.base import DataProvider
from providers.filesystem import FileSystemProvider

_provider: DataProvider | None = None


def get_provider() -> DataProvider:
    """Return the application-wide data provider (singleton).

    Used as a FastAPI dependency::

        @router.get("/assets")
        async def get_assets(provider: DataProvider = Depends(get_provider)):
            ...

    The provider is lazily created on first call.  Tests can override this
    dependency via ``app.dependency_overrides[get_provider]``.
    """
    global _provider
    if _provider is None:
        _provider = FileSystemProvider()
    return _provider
