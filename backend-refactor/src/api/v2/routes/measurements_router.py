"""Measurements router (v2 style but registered as v1)."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from services.measurement_svc import MeasurementService

router = APIRouter(tags=["measurements"])

measurement_service = MeasurementService()


@router.get("/measurements/stats/{signal_id}")
async def get_signal_stats(
    signal_id: str,
    from_date: str = Query(..., alias="from", description="Start date (ISO format)"),
    to_date: str = Query(..., alias="to", description="End date (ISO format)"),
):
    """Calculate statistics for a signal over a date range.

    Returns:
        - count: Number of measurements
        - mean: Average value
        - min: Minimum value
        - max: Maximum value
        - median: Median value
        - std_dev: Standard deviation
    """
    try:
        from_dt = datetime.fromisoformat(from_date)
        to_dt = datetime.fromisoformat(to_date)

        stats = measurement_service.calculate_signal_stats(signal_id, from_dt, to_dt)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")
