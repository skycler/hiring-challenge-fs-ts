"""Health route.

Endpoints
---------
- ``GET /health`` -- application health check
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return application health status."""
    return {"status": "ok"}
