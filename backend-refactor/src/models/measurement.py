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
    """A paginated list of measurements for one or more signals.

    Used as the response model for endpoints that return measurement
    time-series data.  Each :class:`Measurement` already carries its own
    ``signal_id``, so the wrapper intentionally omits a top-level signal
    identifier — this lets the same model serve both single-signal
    (``GET /signals/{id}/measurements``) and multi-signal
    (``GET /measurements?signal_ids=1,2,3``) responses.

    Pagination fields:

    - ``total`` — total number of measurements matching the query (before
      pagination).
    - ``count`` — number of measurements in this page (``len(measurements)``).
    - ``limit`` — maximum number of measurements per page.
    - ``offset`` — zero-based offset into the full result set.
    """

    total: int = Field(description="Total matching measurements", examples=[9500])
    count: int = Field(description="Measurements in this page", examples=[50])
    limit: int = Field(description="Page size", examples=[1000])
    offset: int = Field(description="Page offset", examples=[0])
    measurements: list[Measurement] = Field(examples=[[]])
