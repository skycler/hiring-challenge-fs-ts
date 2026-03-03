"""Signal routes.

Endpoints
---------
- ``GET /signals`` -- list all signals
- ``GET /signals/{signal_id}`` -- get a single signal by ID
- ``GET /signals/{signal_id}/stats`` -- aggregate statistics for a signal
- ``GET /signals/{signal_id}/measurements`` -- measurements for a signal
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from models.measurement import MeasurementList
from models.signal import Signal, SignalStats
from providers import get_provider
from providers.base import DataProvider
from services import get_measurement_service
from services.measurement_svc import MeasurementService

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[Signal], response_model_by_alias=False)
async def get_signals(provider: DataProvider = Depends(get_provider)) -> list[Signal]:
    """Return all signals."""
    return provider.load_signals()


@router.get("/{signal_id}", response_model=Signal, response_model_by_alias=False)
async def get_signal(
    signal_id: int,
    provider: DataProvider = Depends(get_provider),
) -> Signal:
    """Return a single signal by its ID."""
    signals = provider.load_signals()
    for s in signals:
        if s.signal_id == signal_id:
            return s
    raise HTTPException(status_code=404, detail=f"Signal {signal_id!r} not found")


@router.get("/{signal_id}/stats", response_model=SignalStats, response_model_by_alias=False)
async def get_signal_stats(
    signal_id: int,
    from_date: datetime = Query(..., alias="from", description="Start datetime (ISO 8601)"),
    to_date: datetime = Query(..., alias="to", description="End datetime (ISO 8601)"),
    provider: DataProvider = Depends(get_provider),
    svc: MeasurementService = Depends(get_measurement_service),
) -> SignalStats:
    """Calculate aggregate statistics for a signal over a date range."""
    signals = provider.load_signals()
    if not any(s.signal_id == signal_id for s in signals):
        raise HTTPException(status_code=404, detail=f"Signal {signal_id!r} not found")

    if from_date >= to_date:
        raise HTTPException(
            status_code=400,
            detail="Invalid date range: 'from' must be before 'to'",
        )

    return svc.calculate_signal_stats(signal_id, from_date, to_date)


@router.get(
    "/{signal_id}/measurements", response_model=MeasurementList, response_model_by_alias=False
)
async def get_signal_measurements(
    signal_id: int,
    from_date: datetime | None = Query(
        None, alias="from", description="Start datetime (ISO 8601)"
    ),
    to_date: datetime | None = Query(None, alias="to", description="End datetime (ISO 8601)"),
    provider: DataProvider = Depends(get_provider),
    svc: MeasurementService = Depends(get_measurement_service),
) -> MeasurementList:
    """Return measurements for a signal, optionally filtered by date range."""
    signals = provider.load_signals()
    if not any(s.signal_id == signal_id for s in signals):
        raise HTTPException(status_code=404, detail=f"Signal {signal_id!r} not found")

    if from_date is not None and to_date is not None and from_date >= to_date:
        raise HTTPException(
            status_code=400,
            detail="Invalid date range: 'from' must be before 'to'",
        )

    return svc.get_measurements([signal_id], from_date, to_date)
