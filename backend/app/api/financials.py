from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.schemas import FinancialRead
from backend.app.db.session import get_session
from backend.app.services.tushare_client import TushareService

router = APIRouter(prefix="/api/v1/financials", tags=["financials"])


@router.post("/{ts_code}/refresh", response_model=List[FinancialRead])
async def refresh_financials(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    items = await service.fetch_financials(ts_code=ts_code)
    return items


@router.get("/{ts_code}", response_model=List[FinancialRead])
async def list_financials(
    ts_code: str,
    limit: int = 40,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    return await service.list_financials(ts_code=ts_code, limit=limit)
