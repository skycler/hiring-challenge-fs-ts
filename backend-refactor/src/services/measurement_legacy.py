from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from db.measurement_db import get_measurements as get_my_measurements

router = APIRouter(tags=["measurements"])


@router.get("/measurements")
async def get_measurements(
    signalIds: str = Query(..., description="Comma-separated signal IDs"),
    from_date: str = Query(..., alias="from", description="Start date (ISO format)"),
    to_date: str = Query(..., alias="to", description="End date (ISO format)"),
):
    """Get measurements for specified signals and date range."""
    try:
        signal_id_list = [sid.strip() for sid in signalIds.split(",")]

        from_dt = datetime.fromisoformat(from_date)
        to_dt = datetime.fromisoformat(to_date)

        if from_dt >= to_dt:
            raise HTTPException(
                status_code=400,
                detail="Invalid date range: 'from' must be before 'to'",
            )

        measurements = get_my_measurements(signal_id_list, from_dt, to_dt)
        return measurements

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
