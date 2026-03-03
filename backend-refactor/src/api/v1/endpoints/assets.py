"""Assets endpoint (v1)."""

from fastapi import APIRouter, HTTPException
from services.asset_service import AssetService

router = APIRouter(tags=["assets"])

asset_service = AssetService()


@router.get("/assets")
async def get_assets():
    """Get all assets with their signals."""
    try:
        assets = asset_service.get_all_assets()

        if not assets:
            raise HTTPException(status_code=404, detail="No assets found")

        return assets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/list")
async def get_assets_alternative():
    """Alternative endpoint for assets."""
    assets = asset_service.get_all_assets()
    return {"assets": assets}
