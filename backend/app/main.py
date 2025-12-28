import asyncio
import math
from typing import List

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db import models
from backend.app.db.session import SessionLocal, engine, get_session
from backend.app.db.schemas import (
    AnalysisCreate,
    AnalysisRead,
    FinancialRead,
    PriceHistoryRead,
    RefreshRequest,
    ValuationRead,
)
from backend.app.services.analysis_engine import AnalysisEngine
from backend.app.services.deepseek_service import DeepSeekService
from backend.app.services.tushare_client import TushareService
from backend.app.tasks.refresh import run_refresh_job


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


@app.post("/api/v1/financials/{ts_code}/refresh", response_model=List[FinancialRead])
async def refresh_financials(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    items = await service.fetch_financials(ts_code=ts_code)
    return items


@app.get("/api/v1/financials/{ts_code}", response_model=List[FinancialRead])
async def list_financials(
    ts_code: str,
    limit: int = 40,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    return await service.list_financials(ts_code=ts_code, limit=limit)


@app.post("/api/v1/valuations/{ts_code}/refresh", response_model=List[ValuationRead])
async def refresh_valuations(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    items = await service.fetch_valuations(ts_code=ts_code)
    return items


@app.get("/api/v1/valuations/{ts_code}", response_model=List[ValuationRead])
async def list_valuations(
    ts_code: str,
    limit: int = 60,
    session: AsyncSession = Depends(get_session),
) -> list:
    service = TushareService(session)
    return await service.list_valuations(ts_code=ts_code, limit=limit)


@app.post("/api/v1/analyses", response_model=AnalysisRead)
async def create_analysis(
    payload: AnalysisCreate,
    session: AsyncSession = Depends(get_session),
) -> models.Analysis:
    service = TushareService(session)
    prices = []
    if payload.ts_code:
        prices = await service.fetch_daily_prices(ts_code=payload.ts_code)
    returns = _compute_log_returns(prices)
    mu, sigma = AnalysisEngine.estimate_mu_sigma(returns)
    probability = AnalysisEngine.gbm_target_probability(
        mu, sigma, payload.target_return, payload.horizon_years
    )
    reporter = DeepSeekService()
    report = await reporter.generate_report(
        ts_code=payload.ts_code,
        target_return=payload.target_return,
        horizon_years=payload.horizon_years,
        mu=mu,
        sigma=sigma,
        probability=probability,
    )
    analysis = models.Analysis(
        ts_code=payload.ts_code,
        method=payload.method,
        target_return=payload.target_return,
        horizon_years=payload.horizon_years,
        probability=probability,
        params_json={
            "mu": mu,
            "sigma": sigma,
            "n_returns": len(returns),
            "report": report,
        },
    )
    session.add(analysis)
    await session.commit()
    await session.refresh(analysis)
    return analysis


@app.post("/api/v1/jobs/refresh")
async def enqueue_refresh(payload: RefreshRequest) -> dict:
    # Fire-and-forget background refresh job using a fresh session.
    asyncio.create_task(run_refresh_job(SessionLocal, payload.ts_codes))
    return {"status": "queued", "symbols": payload.ts_codes}


def _compute_log_returns(prices: list[models.PriceHistory]) -> list[float]:
    if len(prices) < 2:
        return []
    ordered = sorted(prices, key=lambda p: p.trade_date)
    returns: list[float] = []
    for prev, curr in zip(ordered, ordered[1:]):
        if prev.close and curr.close:
            returns.append(float(math.log(curr.close / prev.close)))
    return returns
