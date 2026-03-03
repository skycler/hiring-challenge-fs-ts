"""Asset routes.

Endpoints
---------
- ``GET /assets`` -- list all assets
- ``GET /assets/{asset_id}/signals`` -- list signals belonging to an asset
"""

from fastapi import APIRouter, Depends, HTTPException

from models.asset import Asset
from models.signal import Signal
from providers import get_provider
from providers.base import DataProvider

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Asset], response_model_by_alias=False)
async def get_assets(provider: DataProvider = Depends(get_provider)) -> list[Asset]:
    """Return all assets."""
    return provider.load_assets()


@router.get("/{asset_id}/signals", response_model=list[Signal], response_model_by_alias=False)
async def get_asset_signals(
    asset_id: int,
    provider: DataProvider = Depends(get_provider),
) -> list[Signal]:
    """Return all signals belonging to the given asset."""
    assets = provider.load_assets()
    if not any(a.asset_id == asset_id for a in assets):
        raise HTTPException(status_code=404, detail=f"Asset {asset_id!r} not found")

    signals = provider.load_signals()
    return [s for s in signals if s.asset_id == asset_id]
