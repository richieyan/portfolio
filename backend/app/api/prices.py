from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.schemas import PriceHistoryRead
from backend.app.db.session import get_session
from backend.app.services.tushare_client import TushareService

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


@router.post("/{ts_code}/refresh", response_model=List[PriceHistoryRead])
async def refresh_prices(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    prices = await service.fetch_daily_prices(ts_code=ts_code)
    return prices


@router.get("/{ts_code}", response_model=List[PriceHistoryRead])
async def list_prices(
    ts_code: str,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    return await service.list_prices(ts_code=ts_code, limit=limit)
