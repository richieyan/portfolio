from typing import List
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.schemas import PriceHistoryRead
from backend.app.db.session import get_session
from backend.app.services.tushare_client import TushareService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


@router.post("/{ts_code}/refresh", response_model=List[PriceHistoryRead])
async def refresh_prices(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    logger.info(f"[API] POST /prices/{ts_code}/refresh 请求进来")
    service = TushareService(session)
    prices = await service.fetch_daily_prices(ts_code=ts_code)
    logger.info(f"[API] POST /prices/{ts_code}/refresh 返回 {len(prices)} 条记录")
    return prices


@router.get("/{ts_code}", response_model=List[PriceHistoryRead])
async def list_prices(
    ts_code: str,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
) -> list:
    logger.info(f"[API] GET /prices/{ts_code} 请求进来，limit={limit}")
    service = TushareService(session)
    result = await service.list_prices(ts_code=ts_code, limit=limit)
    logger.info(f"[API] GET /prices/{ts_code} 返回 {len(result)} 条记录")
    return result
