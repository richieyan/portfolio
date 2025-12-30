from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import models
from backend.app.db.schemas import HoldingCreate, HoldingRead, HoldingUpdate
from backend.app.db.session import get_session

router = APIRouter(prefix="/api/v1/holdings", tags=["holdings"])


async def _ensure_portfolio(session: AsyncSession, portfolio_id: int) -> None:
    exists = await session.execute(
        select(models.Portfolio.id).where(models.Portfolio.id == portfolio_id)
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


async def _ensure_stock(session: AsyncSession, ts_code: str) -> None:
    result = await session.execute(select(models.Stock).where(models.Stock.ts_code == ts_code))
    if result.scalar_one_or_none():
        return
    stock = models.Stock(ts_code=ts_code, active=True)
    session.add(stock)
    await session.flush()


@router.post("", response_model=HoldingRead, status_code=status.HTTP_201_CREATED)
async def create_holding(
    payload: HoldingCreate,
    session: AsyncSession = Depends(get_session),
) -> models.Holding:
    await _ensure_portfolio(session, payload.portfolio_id)
    await _ensure_stock(session, payload.ts_code)
    holding = models.Holding(
        portfolio_id=payload.portfolio_id,
        ts_code=payload.ts_code,
        qty=payload.qty,
        buy_price=payload.buy_price,
        buy_date=payload.buy_date,
        tags=payload.tags,
    )
    session.add(holding)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(holding)
    return holding


@router.patch("/{holding_id}", response_model=HoldingRead)
async def update_holding(
    holding_id: int,
    payload: HoldingUpdate,
    session: AsyncSession = Depends(get_session),
) -> models.Holding:
    result = await session.execute(
        select(models.Holding).where(models.Holding.id == holding_id)
    )
    holding = result.scalar_one_or_none()
    if holding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(holding, field, value)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(holding)
    return holding


@router.delete("/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(models.Holding).where(models.Holding.id == holding_id)
    )
    holding = result.scalar_one_or_none()
    if holding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    await session.delete(holding)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
