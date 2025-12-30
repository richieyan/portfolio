import asyncio

from fastapi import APIRouter

from backend.app.db.schemas import RefreshRequest
from backend.app.db.session import SessionLocal
from backend.app.tasks.refresh import run_refresh_job

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/refresh")
async def enqueue_refresh(payload: RefreshRequest) -> dict:
    # Fire-and-forget background refresh job using a fresh session.
    asyncio.create_task(run_refresh_job(SessionLocal, payload.ts_codes))
    return {"status": "queued", "symbols": payload.ts_codes}
