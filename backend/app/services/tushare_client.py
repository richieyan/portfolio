from __future__ import annotations

import asyncio
from datetime import datetime, date, timedelta
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

    async def _ensure_stock(self, ts_code: str) -> None:
        """Guarantee a stock row exists to satisfy FK constraints."""
        result = await self.session.execute(select(models.Stock).where(models.Stock.ts_code == ts_code))
        if result.scalar_one_or_none():
            return
        stock = models.Stock(ts_code=ts_code, active=True)
        self.session.add(stock)
        await self.session.flush()

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
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, "price_history", ttl_seconds=ttl):
            existing = await self.session.execute(
                select(models.PriceHistory)
                .where(models.PriceHistory.ts_code == ts_code)
                .order_by(models.PriceHistory.trade_date.desc())
            )
            return list(existing.scalars().all())

        last_date = await self._get_last_trade_date(ts_code)
        incremental_start = start_date or self._next_date_str(last_date)
        df = await self._run_with_retry(
            self.api.daily,
            ts_code=ts_code,
            start_date=incremental_start,
            end_date=end_date,
        )
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

    async def _get_last_trade_date(self, ts_code: str) -> date | None:
        result = await self.session.execute(
            select(models.PriceHistory.trade_date)
            .where(models.PriceHistory.ts_code == ts_code)
            .order_by(models.PriceHistory.trade_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _next_date_str(self, last_date: date | None) -> str | None:
        if not last_date:
            return None
        return (last_date + timedelta(days=1)).strftime("%Y%m%d")

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
        records_list = list(records)
        if not records_list:
            return
        stmt = insert(models.PriceHistory).values(records_list)
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

    async def fetch_financials(self, ts_code: str) -> list[models.Financial]:
        """Cache-first fetch of financial indicators for a single symbol.

        Uses Tushare `fina_indicator` to populate ROE, ROA, and debt ratio.
        Revenue and profit are optional and may be unavailable from this endpoint.
        """
        ttl = self.settings.financial_ttl_seconds
        data_type = "financials"
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, data_type, ttl_seconds=ttl):
            result = await self.session.execute(
                select(models.Financial)
                .where(models.Financial.ts_code == ts_code)
                .order_by(models.Financial.period.desc())
            )
            return list(result.scalars().all())

        df = await self._run_with_retry(self.api.fina_indicator, ts_code=ts_code)
        records = self._normalize_financials(df)
        await self._upsert_financials(records)
        await self._mark_status(ts_code, data_type, ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.Financial)
            .where(models.Financial.ts_code == ts_code)
            .order_by(models.Financial.period.desc())
        )
        return list(result.scalars().all())

    def _normalize_financials(self, df: pd.DataFrame) -> Iterable[dict]:
        if df is None or df.empty:
            return []
        df = df.copy()
        # Period: use end_date from fina_indicator (YYYYMMDD string)
        df["period"] = df["end_date"].astype(str)
        # Map fields safely if present
        cols = [
            "ts_code",
            "period",
            "roe",
            "roa",
            "debt_to_assets",
        ]
        # Fill missing columns with NaN for robustness
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA
        for _, row in df[cols].iterrows():
            yield {
                "ts_code": row["ts_code"],
                "period": row["period"],
                "revenue": None,
                "profit": None,
                "roe": float(row["roe"]) if pd.notna(row["roe"]) else None,
                "roa": float(row["roa"]) if pd.notna(row["roa"]) else None,
                "debt_ratio": float(row["debt_to_assets"]) if pd.notna(row["debt_to_assets"]) else None,
            }

    async def _upsert_financials(self, records: Iterable[dict]) -> None:
        records_list = list(records)
        if not records_list:
            return
        stmt = insert(models.Financial).values(records_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.Financial.ts_code, models.Financial.period],
            set_={
                "revenue": stmt.excluded.revenue,
                "profit": stmt.excluded.profit,
                "roe": stmt.excluded.roe,
                "roa": stmt.excluded.roa,
                "debt_ratio": stmt.excluded.debt_ratio,
            },
        )
        await self.session.execute(stmt)

    async def list_financials(self, ts_code: str, limit: int = 40) -> list[models.Financial]:
        result = await self.session.execute(
            select(models.Financial)
            .where(models.Financial.ts_code == ts_code)
            .order_by(models.Financial.period.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def fetch_valuations(self, ts_code: str) -> list[models.Valuation]:
        """Cache-first fetch of valuation snapshots for a single symbol.

        Uses Tushare `daily_basic` to populate PE, PB, and PS. EV/EBITDA
        is optional and left as None in MVP.
        """
        ttl = self.settings.valuation_ttl_seconds
        data_type = "valuations"
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, data_type, ttl_seconds=ttl):
            result = await self.session.execute(
                select(models.Valuation)
                .where(models.Valuation.ts_code == ts_code)
                .order_by(models.Valuation.date.desc())
            )
            return list(result.scalars().all())

        df = await self._run_with_retry(self.api.daily_basic, ts_code=ts_code)
        records = self._normalize_valuations(df)
        await self._upsert_valuations(records)
        await self._mark_status(ts_code, data_type, ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.Valuation)
            .where(models.Valuation.ts_code == ts_code)
            .order_by(models.Valuation.date.desc())
        )
        return list(result.scalars().all())

    def _normalize_valuations(self, df: pd.DataFrame) -> Iterable[dict]:
        if df is None or df.empty:
            return []
        df = df.copy()
        df["date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.date
        # Ensure columns exist
        for c in ["pe_ttm", "pb", "ps_ttm"]:
            if c not in df.columns:
                df[c] = pd.NA
        cols = ["ts_code", "date", "pe_ttm", "pb", "ps_ttm"]
        for _, row in df[cols].iterrows():
            yield {
                "ts_code": row["ts_code"],
                "date": row["date"],
                "pe": float(row["pe_ttm"]) if pd.notna(row["pe_ttm"]) else None,
                "pb": float(row["pb"]) if pd.notna(row["pb"]) else None,
                "ps": float(row["ps_ttm"]) if pd.notna(row["ps_ttm"]) else None,
                "ev_ebitda": None,
            }

    async def _upsert_valuations(self, records: Iterable[dict]) -> None:
        records_list = list(records)
        if not records_list:
            return
        stmt = insert(models.Valuation).values(records_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=[models.Valuation.ts_code, models.Valuation.date],
            set_={
                "pe": stmt.excluded.pe,
                "pb": stmt.excluded.pb,
                "ps": stmt.excluded.ps,
                "ev_ebitda": stmt.excluded.ev_ebitda,
            },
        )
        await self.session.execute(stmt)

    async def list_valuations(self, ts_code: str, limit: int = 60) -> list[models.Valuation]:
        result = await self.session.execute(
            select(models.Valuation)
            .where(models.Valuation.ts_code == ts_code)
            .order_by(models.Valuation.date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
