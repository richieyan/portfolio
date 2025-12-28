from __future__ import annotations

import asyncio
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.tushare_client import TushareService
from backend.app.tasks import JobRunner


async def refresh_symbols(
    session: AsyncSession,
    ts_codes: Iterable[str],
    include_financials: bool = True,
    include_valuations: bool = True,
) -> list[str]:
    """Refresh price/financial/valuation data for symbols in sequence."""
    service = TushareService(session)
    logs: list[str] = []
    for ts_code in ts_codes:
        try:
            await service.fetch_daily_prices(ts_code=ts_code)
            if include_financials:
                await service.fetch_financials(ts_code=ts_code)
            if include_valuations:
                await service.fetch_valuations(ts_code=ts_code)
            logs.append(f"{ts_code}: ok")
        except Exception as exc:  # pragma: no cover - external API
            logs.append(f"{ts_code}: error {exc}")
    return logs


async def run_refresh_job(
    session_factory,
    ts_codes: Iterable[str],
    include_financials: bool = True,
    include_valuations: bool = True,
) -> None:
    """Spawn a new session to run a refresh job and record status."""
    async with session_factory() as session:
        runner = JobRunner(session)
        job = await runner.start_job("batch_refresh")
        logs = await refresh_symbols(session, ts_codes, include_financials, include_valuations)
        status = "succeeded" if all("ok" in log for log in logs) else "failed"
        await runner.finish_job(job, status=status, logs="\n".join(logs))
        await session.commit()
