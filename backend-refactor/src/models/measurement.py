"""Measurement models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Measurement(BaseModel):
    """A single timestamped measurement reading for a signal.

    The CSV source uses pipe-delimited columns ``Ts|SignalId|MeasurementValue``
    with European-style comma decimals (e.g. ``116,129`` → ``116.129``).
    Parsing that CSV is *not* this model's job — by the time data reaches
    here the values should already be proper Python types.
    """

    model_config = {"populate_by_name": True}

    timestamp: datetime = Field(alias="Ts", examples=["2023-01-15T10:30:00.000000"])
    signal_id: int = Field(alias="SignalId", examples=[100001])
    value: float = Field(alias="MeasurementValue", examples=[230.5])


class MeasurementList(BaseModel):
    """A list of measurements for one or more signals.

    Used as the response model for endpoints that return measurement
    time-series data.  Each :class:`Measurement` already carries its own
    ``signal_id``, so the wrapper intentionally omits a top-level signal
    identifier — this lets the same model serve both single-signal
    (``GET /signals/{id}/measurements``) and multi-signal
    (``GET /measurements?signal_ids=1,2,3``) responses.
    """

    count: int = Field(examples=[50])
    measurements: list[Measurement] = Field(examples=[[]])
