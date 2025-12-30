from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import models
from backend.app.db.schemas import PortfolioCreate, PortfolioRead, HoldingRead
from backend.app.db.session import get_session

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    payload: PortfolioCreate,
    session: AsyncSession = Depends(get_session),
) -> models.Portfolio:
    portfolio = models.Portfolio(name=payload.name)
    session.add(portfolio)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(portfolio)
    return portfolio


@router.get("", response_model=List[PortfolioRead])
async def list_portfolios(
    session: AsyncSession = Depends(get_session),
) -> list:
    result = await session.execute(
        select(models.Portfolio).order_by(models.Portfolio.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{portfolio_id}/holdings", response_model=List[HoldingRead])
async def list_holdings_for_portfolio(
    portfolio_id: int,
    session: AsyncSession = Depends(get_session),
) -> list:
    exists = await session.execute(
        select(models.Portfolio.id).where(models.Portfolio.id == portfolio_id)
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    result = await session.execute(
        select(models.Holding)
        .where(models.Holding.portfolio_id == portfolio_id)
        .order_by(models.Holding.id.desc())
    )
    return list(result.scalars().all())
