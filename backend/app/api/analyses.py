import math
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import models
from backend.app.db.schemas import AnalysisCreate, AnalysisRead
from backend.app.db.session import get_session
from backend.app.services.analysis_engine import AnalysisEngine
from backend.app.services.deepseek_service import DeepSeekService
from backend.app.services.tushare_client import TushareService

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisRead)
async def create_analysis(
    payload: AnalysisCreate,
    session: AsyncSession = Depends(get_session),
) -> models.Analysis:
    service = TushareService(session)
    prices: List[models.PriceHistory] = []
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


def _compute_log_returns(prices: List[models.PriceHistory]) -> list[float]:
    if len(prices) < 2:
        return []
    ordered = sorted(prices, key=lambda p: p.trade_date)
    returns: list[float] = []
    for prev, curr in zip(ordered, ordered[1:]):
        if prev.close and curr.close:
            returns.append(float(math.log(curr.close / prev.close)))
    return returns
