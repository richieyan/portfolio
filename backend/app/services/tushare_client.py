from __future__ import annotations

import asyncio
from datetime import datetime, date
from typing import Iterable

import pandas as pd
import tushare as ts
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db import models


class TushareService:
    def __init__(self, session: AsyncSession):
        self.settings = get_settings()
        self.session = session
        ts.set_token(self.settings.tushare_token)
        self.api = ts.pro_api()

    async def _get_status(self, ts_code: str, data_type: str) -> models.DataStatus | None:
        result = await self.session.execute(
            select(models.DataStatus).where(
                models.DataStatus.ts_code == ts_code,
                models.DataStatus.data_type == data_type,
            )
        )
        return result.scalar_one_or_none()

    async def _mark_status(
        self,
        ts_code: str,
        data_type: str,
        ttl_seconds: int,
        stale: bool,
        error_code: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        stmt = insert(models.DataStatus).values(
            ts_code=ts_code,
            data_type=data_type,
            ttl_seconds=ttl_seconds,
            last_updated=datetime.utcnow(),
            stale=stale,
            error_code=error_code,
            error_msg=error_msg,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.DataStatus.ts_code, models.DataStatus.data_type],
            set_=dict(
                ttl_seconds=ttl_seconds,
                last_updated=datetime.utcnow(),
                stale=stale,
                error_code=error_code,
                error_msg=error_msg,
            ),
        )
        await self.session.execute(stmt)

    async def _is_stale(self, ts_code: str, data_type: str, ttl_seconds: int) -> bool:
        status = await self._get_status(ts_code, data_type)
        if not status or not status.last_updated:
            return True
        elapsed = (datetime.utcnow() - status.last_updated).total_seconds()
        return elapsed >= ttl_seconds or status.stale

    async def fetch_daily_prices(
        self, ts_code: str, start_date: str | None = None, end_date: str | None = None
    ) -> list[models.PriceHistory]:
        """Cache-first fetch of daily OHLCV for a single symbol."""
        ttl = self.settings.price_ttl_seconds
        if not await self._is_stale(ts_code, "price_history", ttl_seconds=ttl):
            existing = await self.session.execute(
                select(models.PriceHistory)
                .where(models.PriceHistory.ts_code == ts_code)
                .order_by(models.PriceHistory.trade_date.desc())
            )
            return list(existing.scalars().all())

        df = await self._run_with_retry(self.api.daily, ts_code=ts_code, start_date=start_date, end_date=end_date)
        records = self._normalize_prices(df)
        await self._upsert_prices(records)
        await self._mark_status(ts_code, "price_history", ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.PriceHistory)
            .where(models.PriceHistory.ts_code == ts_code)
            .order_by(models.PriceHistory.trade_date.desc())
        )
        return list(result.scalars().all())

    async def _run_with_retry(self, func, max_attempts: int = 3, **kwargs):
        delay = 1.0
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return func(**kwargs)
            except Exception as exc:  # pragma: no cover - external API
                last_exc = exc
                if attempt == max_attempts:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
        if last_exc:
            raise last_exc

    def _normalize_prices(self, df: pd.DataFrame) -> Iterable[dict]:
        if df is None or df.empty:
            return []
        df = df.copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.date
        cols = ["ts_code", "trade_date", "close", "open", "high", "low", "vol"]
        for _, row in df[cols].iterrows():
            yield {
                "ts_code": row["ts_code"],
                "trade_date": row["trade_date"],
                "close": float(row.get("close")),
                "open": float(row.get("open")) if pd.notna(row.get("open")) else None,
                "high": float(row.get("high")) if pd.notna(row.get("high")) else None,
                "low": float(row.get("low")) if pd.notna(row.get("low")) else None,
                "volume": float(row.get("vol")) if pd.notna(row.get("vol")) else None,
            }

    async def _upsert_prices(self, records: Iterable[dict]) -> None:
        stmt = insert(models.PriceHistory).values(list(records))
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.PriceHistory.ts_code, models.PriceHistory.trade_date],
            set_={
                "close": stmt.excluded.close,
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "volume": stmt.excluded.volume,
            },
        )
        await self.session.execute(stmt)

    async def list_prices(self, ts_code: str, limit: int = 200) -> list[models.PriceHistory]:
        result = await self.session.execute(
            select(models.PriceHistory)
            .where(models.PriceHistory.ts_code == ts_code)
            .order_by(models.PriceHistory.trade_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
