from typing import List

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db import models
from backend.app.db.session import engine, get_session
from backend.app.db.schemas import PriceHistoryRead
from backend.app.services.tushare_client import TushareService

app = FastAPI(title=get_settings().app_name)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/prices/{ts_code}/refresh", response_model=List[PriceHistoryRead])
async def refresh_prices(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    prices = await service.fetch_daily_prices(ts_code=ts_code)
    return prices


@app.get("/api/v1/prices/{ts_code}", response_model=List[PriceHistoryRead])
async def list_prices(
    ts_code: str,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    return await service.list_prices(ts_code=ts_code, limit=limit)
