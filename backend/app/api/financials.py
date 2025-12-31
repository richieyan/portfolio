from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.schemas import (
    BalanceSheetRead,
    CashFlowStatementRead,
    FinancialRead,
    IncomeStatementRead,
)
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


@router.get("/{ts_code}/income", response_model=List[IncomeStatementRead])
async def get_income_statement(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    """Get income statement for a stock."""
    service = TushareService(session)
    statements = await service.fetch_income_statement(ts_code=ts_code)
    return [IncomeStatementRead.model_validate(s) for s in statements]


@router.get("/{ts_code}/balance", response_model=List[BalanceSheetRead])
async def get_balance_sheet(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    """Get balance sheet for a stock."""
    service = TushareService(session)
    sheets = await service.fetch_balance_sheet(ts_code=ts_code)
    return [BalanceSheetRead.model_validate(s) for s in sheets]


@router.get("/{ts_code}/cashflow", response_model=List[CashFlowStatementRead])
async def get_cash_flow(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    """Get cash flow statement for a stock."""
    service = TushareService(session)
    statements = await service.fetch_cash_flow(ts_code=ts_code)
    return [CashFlowStatementRead.model_validate(s) for s in statements]
