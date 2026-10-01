"""Health endpoint. Public: used to check a deployment is alive."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..deps import DatabaseDep
from ..schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthOut)
async def health(db: DatabaseDep):
    try:
        await db.ping()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )
    return {"status": "ok", "database": "ok"}
