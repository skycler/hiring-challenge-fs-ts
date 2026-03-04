"""Signal routes.

Endpoints
---------
- ``GET /signals`` — list all signals
- ``GET /signals/{signal_id}`` — get a single signal by ID
- ``GET /signals/{signal_id}/stats`` — aggregate statistics for a signal
- ``GET /signals/{signal_id}/measurements`` — measurements for a signal
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from models.measurement import MeasurementList
from models.signal import Signal, SignalStats
from services import get_measurement_service, get_signal_service
from services.measurement import MeasurementService
from services.signal import SignalService

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[Signal], response_model_by_alias=False)
async def get_signals(
    svc: SignalService = Depends(get_signal_service),
) -> list[Signal]:
    """Return all signals."""
    return svc.get_all()


@router.get(
    "/{signal_id}",
    response_model=Signal,
    response_model_by_alias=False,
    responses={404: {"description": "Signal not found"}},
)
async def get_signal(
    signal_id: int,
    svc: SignalService = Depends(get_signal_service),
) -> Signal:
    """Return a single signal by its ID."""
    signal = svc.find_by_id(signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id!r} not found")
    return signal


@router.get(
    "/{signal_id}/stats",
    response_model=SignalStats,
    response_model_by_alias=False,
    responses={
        400: {"description": "Invalid date range"},
        404: {"description": "Signal not found"},
    },
)
async def get_signal_stats(
    signal_id: int,
    from_date: datetime = Query(..., alias="from", description="Start datetime (ISO 8601)"),
    to_date: datetime = Query(..., alias="to", description="End datetime (ISO 8601)"),
    signal_svc: SignalService = Depends(get_signal_service),
    measurement_svc: MeasurementService = Depends(get_measurement_service),
) -> SignalStats:
    """Calculate aggregate statistics for a signal over a date range."""
    if signal_svc.find_by_id(signal_id) is None:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id!r} not found")
    try:
        measurement_svc.validate_date_range(from_date, to_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return measurement_svc.calculate_signal_stats(signal_id, from_date, to_date)


@router.get(
    "/{signal_id}/measurements",
    response_model=MeasurementList,
    response_model_by_alias=False,
    responses={
        400: {"description": "Invalid date range"},
        404: {"description": "Signal not found"},
    },
)
async def get_signal_measurements(
    signal_id: int,
    from_date: datetime = Query(..., alias="from", description="Start datetime (ISO 8601)"),
    to_date: datetime = Query(..., alias="to", description="End datetime (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    signal_svc: SignalService = Depends(get_signal_service),
    measurement_svc: MeasurementService = Depends(get_measurement_service),
) -> MeasurementList:
    """Return measurements for a signal within a date range."""
    if signal_svc.find_by_id(signal_id) is None:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id!r} not found")
    try:
        measurement_svc.validate_date_range(from_date, to_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return measurement_svc.get_measurements(
        [signal_id], from_date, to_date, limit=limit, offset=offset
    )
