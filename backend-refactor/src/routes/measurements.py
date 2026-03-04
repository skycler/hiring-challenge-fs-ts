"""Measurement routes.

Endpoints
---------
- ``GET /measurements?signal_ids=1,2,3`` -- measurements for multiple signals
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from models.measurement import FlatMeasurementList, MeasurementList, ResponseFormat
from services import get_measurement_service, get_signal_service
from services.measurement import MeasurementService
from services.signal import SignalService

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.get(
    "",
    response_model=MeasurementList | FlatMeasurementList,
    response_model_by_alias=False,
    responses={
        400: {"description": "Invalid signal IDs or date range"},
        404: {"description": "One or more signals not found"},
    },
)
async def get_measurements(
    signal_ids: str = Query(..., description="Comma-separated signal IDs"),
    from_date: datetime = Query(..., alias="from", description="Start datetime (ISO 8601)"),
    to_date: datetime = Query(..., alias="to", description="End datetime (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    fmt: ResponseFormat = Query(
        ResponseFormat.OBJECTS, alias="format", description="Response layout: objects or flat"
    ),
    signal_svc: SignalService = Depends(get_signal_service),
    measurement_svc: MeasurementService = Depends(get_measurement_service),
) -> MeasurementList | FlatMeasurementList:
    """Return paginated measurements for one or more signals within a date range.

    The ``signal_ids`` query parameter accepts a comma-separated string of
    integer signal IDs (e.g. ``100,200,300``).

    Raises:
        HTTPException 400: If *signal_ids* is empty, contains non-integers,
            or the date range is invalid (``from >= to``).
        HTTPException 404: If any of the requested signal IDs are unknown.
    """
    stripped = [sid.strip() for sid in signal_ids.split(",") if sid.strip()]

    if not stripped:
        raise HTTPException(status_code=400, detail="At least one signal_id is required")

    MAX_SIGNAL_IDS = 100
    if len(stripped) > MAX_SIGNAL_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many signal_ids (max {MAX_SIGNAL_IDS})",
        )

    try:
        id_list = [int(sid) for sid in stripped]
    except ValueError:
        raise HTTPException(status_code=400, detail="All signal_ids must be integers") from None

    unknown = signal_svc.find_unknown_ids(id_list)
    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"Signal(s) {', '.join(map(str, unknown))} not found",
        )

    try:
        measurement_svc.validate_date_range(from_date, to_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return measurement_svc.get_measurements(
        id_list, from_date, to_date, limit=limit, offset=offset, fmt=fmt
    )
