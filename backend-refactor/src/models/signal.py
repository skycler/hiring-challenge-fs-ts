"""Signal models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Signal(BaseModel):
    """A signal source associated with an asset.

    JSON data uses PascalCase keys (e.g. ``SignalId``).  Python code uses
    snake_case attributes.  The ``model_config`` below lets Pydantic
    populate fields from either form and serialize back to aliases.
    """

    model_config = {"populate_by_name": True}

    signal_g_id: str = Field(alias="SignalGId", examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
    signal_id: int = Field(alias="SignalId", examples=[100001])
    signal_name: str = Field(alias="SignalName", examples=["EXMPL110STATION_L01"])
    asset_id: int = Field(alias="AssetId", examples=[10])
    unit: str = Field(alias="Unit", examples=["kV"])


class SignalStats(BaseModel):
    """Aggregate statistics for a signal over a time range.

    Used as the response model for ``GET /signals/{signal_id}/stats``.
    Numeric fields are ``None`` when no measurements exist in the range.
    """

    signal_id: int = Field(examples=[100001])
    from_date: datetime = Field(examples=["2023-01-01T00:00:00"])
    to_date: datetime = Field(examples=["2023-01-31T23:59:59"])
    count: int = Field(examples=[150])
    mean: float | None = Field(default=None, examples=[225.75])
    min: float | None = Field(default=None, examples=[110.0])
    max: float | None = Field(default=None, examples=[340.5])
    median: float | None = Field(default=None, examples=[228.0])
    std_dev: float | None = Field(default=None, examples=[42.3])
