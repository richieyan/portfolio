from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import models
from backend.app.db.schemas import StockDetailResponse, StockListResponse, StockRead
from backend.app.db.session import get_session
from backend.app.services.tushare_client import TushareService

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


@router.get("", response_model=StockListResponse)
async def list_stocks(
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> StockListResponse:
    """List stocks with optional search and pagination."""
    service = TushareService(session)
    stocks, total = await service.list_stocks(search=search, limit=limit, offset=offset)
    return StockListResponse(stocks=[StockRead.model_validate(s) for s in stocks], total=total)


@router.get("/{ts_code}/detail", response_model=StockDetailResponse)
async def get_stock_detail(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> StockDetailResponse:
    """Get detailed information for a stock including latest price, valuation, financials, and statements."""
    service = TushareService(session)
    
    # Get stock info
    stock_result = await session.execute(select(models.Stock).where(models.Stock.ts_code == ts_code))
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
    
    # Get latest price
    price_result = await session.execute(
        select(models.PriceHistory)
        .where(models.PriceHistory.ts_code == ts_code)
        .order_by(models.PriceHistory.trade_date.desc())
        .limit(1)
    )
    latest_price = price_result.scalar_one_or_none()
    
    # Get latest valuation
    valuation_result = await session.execute(
        select(models.Valuation)
        .where(models.Valuation.ts_code == ts_code)
        .order_by(models.Valuation.date.desc())
        .limit(1)
    )
    latest_valuation = valuation_result.scalar_one_or_none()
    
    # Get latest financial
    financial_result = await session.execute(
        select(models.Financial)
        .where(models.Financial.ts_code == ts_code)
        .order_by(models.Financial.period.desc())
        .limit(1)
    )
    latest_financial = financial_result.scalar_one_or_none()
    
    # Get financial statements
    income_statements = await service.fetch_income_statement(ts_code)
    balance_sheets = await service.fetch_balance_sheet(ts_code)
    cash_flow_statements = await service.fetch_cash_flow(ts_code)
    
    from backend.app.db.schemas import (
        BalanceSheetRead,
        CashFlowStatementRead,
        FinancialRead,
        IncomeStatementRead,
        PriceHistoryRead,
        ValuationRead,
    )
    
    return StockDetailResponse(
        stock=StockRead.model_validate(stock),
        latest_price=PriceHistoryRead.model_validate(latest_price) if latest_price else None,
        latest_valuation=ValuationRead.model_validate(latest_valuation) if latest_valuation else None,
        latest_financial=FinancialRead.model_validate(latest_financial) if latest_financial else None,
        income_statements=[IncomeStatementRead.model_validate(s) for s in income_statements],
        balance_sheets=[BalanceSheetRead.model_validate(s) for s in balance_sheets],
        cash_flow_statements=[CashFlowStatementRead.model_validate(s) for s in cash_flow_statements],
    )

