"""Measurement routes.

Endpoints
---------
- ``GET /measurements?signal_ids=1,2,3`` — measurements for multiple signals
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from models.measurement import MeasurementList
from providers import get_provider
from providers.base import DataProvider
from services import get_measurement_service
from services.measurement import MeasurementService

router = APIRouter(prefix="/measurements", tags=["measurements"])


def _validate_date_range(from_date: datetime | None, to_date: datetime | None) -> None:
    """Raise 400 if both dates are given and ``from_date >= to_date``."""
    if from_date is not None and to_date is not None and from_date >= to_date:
        raise HTTPException(
            status_code=400,
            detail="Invalid date range: 'from' must be before 'to'",
        )


@router.get("", response_model=MeasurementList, response_model_by_alias=False)
async def get_measurements(
    signal_ids: str = Query(..., description="Comma-separated signal IDs"),
    from_date: datetime | None = Query(
        None, alias="from", description="Start datetime (ISO 8601)"
    ),
    to_date: datetime | None = Query(None, alias="to", description="End datetime (ISO 8601)"),
    provider: DataProvider = Depends(get_provider),
    svc: MeasurementService = Depends(get_measurement_service),
) -> MeasurementList:
    """Return measurements for the given signal IDs, optionally filtered by date range."""
    stripped = [sid.strip() for sid in signal_ids.split(",") if sid.strip()]

    if not stripped:
        raise HTTPException(status_code=400, detail="At least one signal_id is required")

    try:
        id_list = [int(sid) for sid in stripped]
    except ValueError:
        raise HTTPException(status_code=400, detail="All signal_ids must be integers") from None

    known_ids = {s.signal_id for s in provider.load_signals()}
    unknown = [sid for sid in id_list if sid not in known_ids]
    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"Signal(s) {unknown} not found",
        )

    _validate_date_range(from_date, to_date)

    return svc.get_measurements(id_list, from_date, to_date)
