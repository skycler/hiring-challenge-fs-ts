"""Measurement models.

Defines the core :class:`Measurement` model and two response-list variants:

- :class:`MeasurementList` — traditional array-of-objects format
  (``format=objects``, the default).
- :class:`FlatMeasurementList` — parallel-arrays / columnar format
  (``format=flat``), significantly more compact for large payloads.

Both list variants inherit shared pagination fields from
:class:`PaginatedBase`.

The :class:`ResponseFormat` enum lets callers choose between them via
a ``format`` query parameter.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ResponseFormat(str, Enum):
    """Supported serialisation layouts for measurement list responses.

    - ``objects`` — each measurement is a JSON object with ``timestamp``,
      ``signal_id``, and ``value`` keys (default, backward-compatible).
    - ``flat`` — three parallel arrays (``timestamps``, ``signal_ids``,
      ``values``), eliminating per-row key repetition.
    """

    OBJECTS = "objects"
    FLAT = "flat"


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


class PaginatedBase(BaseModel):
    """Shared pagination fields for measurement list responses.

    Both :class:`MeasurementList` and :class:`FlatMeasurementList` inherit
    these fields so that pagination metadata is defined in one place.

    - ``total`` — total number of measurements matching the query (before
      pagination).
    - ``count`` — number of measurements in this page.
    - ``limit`` — maximum number of measurements per page.
    - ``offset`` — zero-based offset into the full result set.
    """

    total: int = Field(description="Total matching measurements", examples=[9500])
    count: int = Field(description="Measurements in this page", examples=[50])
    limit: int = Field(description="Page size", examples=[1000])
    offset: int = Field(description="Page offset", examples=[0])


class MeasurementList(PaginatedBase):
    """A paginated list of measurements (array-of-objects format).

    Used as the response model for endpoints that return measurement
    time-series data when ``format=objects`` (the default).
    """

    measurements: list[Measurement] = Field(examples=[[]])


class FlatMeasurementList(PaginatedBase):
    """A paginated list of measurements (parallel-arrays / flat format).

    Returned when ``format=flat``.  Instead of an array of objects, the
    three measurement fields are each represented as a single array,
    eliminating the per-row repetition of JSON keys.  The *i*-th element
    in ``timestamps``, ``signal_ids``, and ``values`` corresponds to the
    same measurement.
    """

    timestamps: list[datetime] = Field(
        description="Measurement timestamps", examples=[["2023-01-15T10:30:00"]]
    )
    signal_ids: list[int] = Field(
        description="Signal IDs corresponding to each measurement", examples=[[100001]]
    )
    values: list[float] = Field(description="Measurement values", examples=[[230.5]])
