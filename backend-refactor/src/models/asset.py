"""Asset model."""

from pydantic import BaseModel, Field


class Asset(BaseModel):
    """A physical asset (substation) with geographic coordinates.

    JSON data uses PascalCase keys — note the source file has ``AssetID``
    (capital D), not ``AssetId``.  The ``descri`` field in the source data
    is a truncated form of "description"; we accept both via alias.
    """

    model_config = {"populate_by_name": True}

    asset_id: int = Field(alias="AssetID", examples=[42])
    latitude: float = Field(alias="Latitude", examples=[46.9480])
    longitude: float = Field(alias="Longitude", examples=[7.4474])
    description: str = Field(alias="descri", examples=["UW Beispiel"])
