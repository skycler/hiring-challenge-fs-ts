"""Asset routes.

Endpoints
---------
- ``GET /assets`` -- list all assets
- ``GET /assets/{asset_id}/signals`` -- list signals belonging to an asset
"""

from fastapi import APIRouter, Depends, HTTPException

from models.asset import Asset
from models.signal import Signal
from services import get_asset_service, get_signal_service
from services.asset import AssetService
from services.signal import SignalService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Asset], response_model_by_alias=False)
async def get_assets(svc: AssetService = Depends(get_asset_service)) -> list[Asset]:
    """Return every asset in the system."""
    return svc.get_all()


@router.get(
    "/{asset_id}/signals",
    response_model=list[Signal],
    response_model_by_alias=False,
    responses={404: {"description": "Asset not found"}},
)
async def get_asset_signals(
    asset_id: int,
    asset_svc: AssetService = Depends(get_asset_service),
    signal_svc: SignalService = Depends(get_signal_service),
) -> list[Signal]:
    """Return all signals belonging to the given asset.

    Raises:
        HTTPException 404: If no asset with *asset_id* exists.
    """
    if asset_svc.find_by_id(asset_id) is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return signal_svc.find_by_asset_id(asset_id)
