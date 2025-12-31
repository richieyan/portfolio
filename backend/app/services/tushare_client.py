from __future__ import annotations

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Iterable

import pandas as pd
import tushare as ts
from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db import models

logger = logging.getLogger(__name__)


class TushareService:
    def __init__(self, session: AsyncSession):
        self.settings = get_settings()
        self.session = session
        ts.set_token(self.settings.tushare_token)
        self.api = ts.pro_api()

    async def _ensure_stock(self, ts_code: str) -> None:
        """Guarantee a stock row exists to satisfy FK constraints. Updates name and sector if missing."""
        result = await self.session.execute(select(models.Stock).where(models.Stock.ts_code == ts_code))
        stock = result.scalar_one_or_none()
        if stock:
            # If stock exists but name/sector is missing, try to update
            if not stock.name or not stock.sector:
                await self._update_stock_info(ts_code)
            return
        # Create new stock and fetch info from Tushare
        await self._update_stock_info(ts_code)
        result = await self.session.execute(select(models.Stock).where(models.Stock.ts_code == ts_code))
        if not result.scalar_one_or_none():
            # If still not found after update, create minimal record
            stock = models.Stock(ts_code=ts_code, active=True)
            self.session.add(stock)
            await self.session.flush()

    async def _update_stock_info(self, ts_code: str) -> None:
        """Update stock name and sector from Tushare stock_basic API."""
        try:
            logger.info(f"[STOCK] 获取 {ts_code} 的基本信息")
            df = await self._run_with_retry(self.api.stock_basic, ts_code=ts_code, fields="ts_code,name,industry")
            if df is not None and not df.empty and len(df) > 0:
                row = df.iloc[0]
                name = str(row.get("name", "")) if pd.notna(row.get("name")) else None
                sector = str(row.get("industry", "")) if pd.notna(row.get("industry")) else None
                
                # Check if stock exists
                result = await self.session.execute(select(models.Stock).where(models.Stock.ts_code == ts_code))
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing record, only update if new value is not None
                    if name is not None:
                        existing.name = name
                    if sector is not None:
                        existing.sector = sector
                    existing.active = True
                else:
                    # Insert new record
                    stock = models.Stock(ts_code=ts_code, name=name, sector=sector, active=True)
                    self.session.add(stock)
                
                await self.session.flush()
                logger.info(f"[STOCK] 更新 {ts_code} 信息: name={name}, sector={sector}")
        except Exception as e:
            logger.warning(f"[STOCK] 获取 {ts_code} 基本信息失败: {e}，将创建最小记录")
            # If update fails, ensure at least a minimal record exists
            result = await self.session.execute(select(models.Stock).where(models.Stock.ts_code == ts_code))
            if not result.scalar_one_or_none():
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
        logger.info(f"[PRICE] 开始获取 {ts_code}，start_date={start_date}, end_date={end_date}")
        ttl = self.settings.price_ttl_seconds
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, "price_history", ttl_seconds=ttl):
            logger.info(f"[PRICE] {ts_code} 缓存未过期，返回本地数据")
            existing = await self.session.execute(
                select(models.PriceHistory)
                .where(models.PriceHistory.ts_code == ts_code)
                .order_by(models.PriceHistory.trade_date.desc())
            )
            return list(existing.scalars().all())

        last_date = await self._get_last_trade_date(ts_code)
        incremental_start = start_date or self._next_date_str(last_date)
        logger.info(f"[PRICE] 调用 Tushare API，ts_code={ts_code}, start_date={incremental_start}, end_date={end_date}")
        df = await self._run_with_retry(
            self.api.daily,
            ts_code=ts_code,
            start_date=incremental_start,
            end_date=end_date,
        )
        logger.info(f"[PRICE] Tushare 返回 {len(df) if df is not None and not df.empty else 0} 条记录")
        if df is not None and not df.empty:
            logger.debug(f"[PRICE] 返回数据的列: {list(df.columns)}")
        records = self._normalize_prices(df)
        records_list = list(records)
        logger.info(f"[PRICE] 规范化后得到 {len(records_list)} 条记录")
        await self._upsert_prices(records_list)
        await self._mark_status(ts_code, "price_history", ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.PriceHistory)
            .where(models.PriceHistory.ts_code == ts_code)
            .order_by(models.PriceHistory.trade_date.desc())
        )
        prices = list(result.scalars().all())
        logger.info(f"[PRICE] 最终返回 {len(prices)} 条数据")
        return prices

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
        func_name = getattr(func, '__name__', 'unknown')
        logger.info(f"[TUSHARE] 开始调用 {func_name}，参数: {kwargs}")
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(f"[TUSHARE] {func_name} 第 {attempt} 次尝试")
                result = func(**kwargs)
                logger.info(f"[TUSHARE] {func_name} 成功，返回类型: {type(result)}")
                return result
            except Exception as exc:  # pragma: no cover - external API
                last_exc = exc
                logger.error(f"[TUSHARE] {func_name} 第 {attempt} 次失败: {type(exc).__name__}: {str(exc)}")
                if attempt == max_attempts:
                    logger.error(f"[TUSHARE] {func_name} 已达最大重试次数，抛出异常")
                    raise
                logger.info(f"[TUSHARE] {func_name} 将在 {delay} 秒后进行第 {attempt + 1} 次重试")
                await asyncio.sleep(delay)
                delay *= 2
        if last_exc:
            raise last_exc

    def _normalize_prices(self, df: pd.DataFrame) -> Iterable[dict]:
        if df is None or df.empty:
            logger.warning("[PRICE] 返回的数据为空或 None")
            return []
        logger.debug(f"[PRICE] 规范化 {len(df)} 行数据，列: {list(df.columns)}")
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
            logger.warning("[PRICE] 没有记录要插入")
            return
        logger.info(f"[PRICE] 准备插入/更新 {len(records_list)} 条价格记录")
        # SQLite 参数限制约 999，每条记录约 7 个字段，分批插入，每批 100 条
        batch_size = 100
        for i in range(0, len(records_list), batch_size):
            batch = records_list[i : i + batch_size]
            stmt = insert(models.PriceHistory).values(batch)
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
            logger.debug(f"[PRICE] 已插入/更新第 {i//batch_size + 1} 批，共 {len(batch)} 条记录")

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
        logger.info(f"[FINANCIAL] 开始获取 {ts_code} 的财务数据")
        ttl = self.settings.financial_ttl_seconds
        data_type = "financials"
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, data_type, ttl_seconds=ttl):
            logger.info(f"[FINANCIAL] {ts_code} 缓存未过期，返回本地数据")
            result = await self.session.execute(
                select(models.Financial)
                .where(models.Financial.ts_code == ts_code)
                .order_by(models.Financial.period.desc())
            )
            return list(result.scalars().all())

        logger.info(f"[FINANCIAL] 调用 Tushare API 获取 fina_indicator，ts_code={ts_code}")
        df = await self._run_with_retry(self.api.fina_indicator, ts_code=ts_code)
        logger.info(f"[FINANCIAL] Tushare 返回 {len(df) if df is not None and not df.empty else 0} 条记录")
        if df is not None and not df.empty:
            logger.debug(f"[FINANCIAL] 返回数据的列: {list(df.columns)}")
        records = self._normalize_financials(df)
        records_list = list(records)
        logger.info(f"[FINANCIAL] 规范化后得到 {len(records_list)} 条记录")
        await self._upsert_financials(records_list)
        await self._mark_status(ts_code, data_type, ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.Financial)
            .where(models.Financial.ts_code == ts_code)
            .order_by(models.Financial.period.desc())
        )
        financials = list(result.scalars().all())
        logger.info(f"[FINANCIAL] 最终返回 {len(financials)} 条数据")
        return financials

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
        logger.info(f"[FINANCIAL] 准备插入/更新 {len(records_list)} 条财务记录")
        # SQLite 参数限制约 999，每条记录约 7 个字段，分批插入，每批 100 条
        batch_size = 100
        for i in range(0, len(records_list), batch_size):
            batch = records_list[i : i + batch_size]
            stmt = insert(models.Financial).values(batch)
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
            logger.debug(f"[FINANCIAL] 已插入/更新第 {i//batch_size + 1} 批，共 {len(batch)} 条记录")

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
        logger.info(f"[VALUATION] 开始获取 {ts_code} 的估值数据")
        ttl = self.settings.valuation_ttl_seconds
        data_type = "valuations"
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, data_type, ttl_seconds=ttl):
            logger.info(f"[VALUATION] {ts_code} 缓存未过期，返回本地数据")
            result = await self.session.execute(
                select(models.Valuation)
                .where(models.Valuation.ts_code == ts_code)
                .order_by(models.Valuation.date.desc())
            )
            return list(result.scalars().all())

        logger.info(f"[VALUATION] 调用 Tushare API 获取 daily_basic，ts_code={ts_code}")
        df = await self._run_with_retry(self.api.daily_basic, ts_code=ts_code)
        logger.info(f"[VALUATION] Tushare 返回 {len(df) if df is not None and not df.empty else 0} 条记录")
        if df is not None and not df.empty:
            logger.debug(f"[VALUATION] 返回数据的列: {list(df.columns)}")
        records = self._normalize_valuations(df)
        records_list = list(records)
        logger.info(f"[VALUATION] 规范化后得到 {len(records_list)} 条记录")
        await self._upsert_valuations(records_list)
        await self._mark_status(ts_code, data_type, ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.Valuation)
            .where(models.Valuation.ts_code == ts_code)
            .order_by(models.Valuation.date.desc())
        )
        valuations = list(result.scalars().all())
        logger.info(f"[VALUATION] 最终返回 {len(valuations)} 条数据")
        return valuations

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
        logger.info(f"[VALUATION] 准备插入/更新 {len(records_list)} 条估值记录")
        # SQLite 参数限制约 999，每条记录约 6 个字段，分批插入，每批 100 条
        batch_size = 100
        for i in range(0, len(records_list), batch_size):
            batch = records_list[i : i + batch_size]
            stmt = insert(models.Valuation).values(batch)
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
            logger.debug(f"[VALUATION] 已插入/更新第 {i//batch_size + 1} 批，共 {len(batch)} 条记录")

    async def list_valuations(self, ts_code: str, limit: int = 60) -> list[models.Valuation]:
        result = await self.session.execute(
            select(models.Valuation)
            .where(models.Valuation.ts_code == ts_code)
            .order_by(models.Valuation.date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_stocks(self, search: str | None = None, limit: int = 100, offset: int = 0) -> tuple[list[models.Stock], int]:
        """List stocks with optional search and pagination."""
        query = select(models.Stock)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (models.Stock.ts_code.like(search_pattern))
                | (models.Stock.name.like(search_pattern))
                | (models.Stock.sector.like(search_pattern))
            )
        query = query.order_by(models.Stock.ts_code)
        
        # Get total count
        count_query = select(func.count()).select_from(models.Stock)
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                (models.Stock.ts_code.like(search_pattern))
                | (models.Stock.name.like(search_pattern))
                | (models.Stock.sector.like(search_pattern))
            )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        stocks = list(result.scalars().all())
        return stocks, total

    async def fetch_income_statement(self, ts_code: str) -> list[models.IncomeStatement]:
        """Cache-first fetch of income statement for a single symbol."""
        logger.info(f"[INCOME] 开始获取 {ts_code} 的利润表数据")
        ttl = self.settings.financial_ttl_seconds
        data_type = "income_statement"
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, data_type, ttl_seconds=ttl):
            logger.info(f"[INCOME] {ts_code} 缓存未过期，返回本地数据")
            result = await self.session.execute(
                select(models.IncomeStatement)
                .where(models.IncomeStatement.ts_code == ts_code)
                .order_by(models.IncomeStatement.period.desc())
            )
            return list(result.scalars().all())

        logger.info(f"[INCOME] 调用 Tushare API 获取 income，ts_code={ts_code}")
        df = await self._run_with_retry(self.api.income, ts_code=ts_code)
        logger.info(f"[INCOME] Tushare 返回 {len(df) if df is not None and not df.empty else 0} 条记录")
        if df is not None and not df.empty:
            logger.debug(f"[INCOME] 返回数据的列: {list(df.columns)}")
        records = self._normalize_income_statement(df)
        records_list = list(records)
        logger.info(f"[INCOME] 规范化后得到 {len(records_list)} 条记录")
        await self._upsert_income_statements(records_list)
        await self._mark_status(ts_code, data_type, ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.IncomeStatement)
            .where(models.IncomeStatement.ts_code == ts_code)
            .order_by(models.IncomeStatement.period.desc())
        )
        statements = list(result.scalars().all())
        logger.info(f"[INCOME] 最终返回 {len(statements)} 条数据")
        return statements

    def _normalize_income_statement(self, df: pd.DataFrame) -> Iterable[dict]:
        if df is None or df.empty:
            return []
        df = df.copy()
        df["period"] = df["end_date"].astype(str)
        cols = ["ts_code", "period", "revenue", "operate_profit", "total_profit", "n_income", "basic_eps", "diluted_eps"]
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA
        for _, row in df[cols].iterrows():
            yield {
                "ts_code": row["ts_code"],
                "period": row["period"],
                "revenue": float(row["revenue"]) if pd.notna(row["revenue"]) else None,
                "operating_profit": float(row["operate_profit"]) if pd.notna(row["operate_profit"]) else None,
                "total_profit": float(row["total_profit"]) if pd.notna(row["total_profit"]) else None,
                "net_profit": float(row["n_income"]) if pd.notna(row["n_income"]) else None,
                "basic_eps": float(row["basic_eps"]) if pd.notna(row["basic_eps"]) else None,
                "diluted_eps": float(row["diluted_eps"]) if pd.notna(row["diluted_eps"]) else None,
            }

    async def _upsert_income_statements(self, records: Iterable[dict]) -> None:
        records_list = list(records)
        if not records_list:
            return
        logger.info(f"[INCOME] 准备插入/更新 {len(records_list)} 条利润表记录")
        batch_size = 100
        for i in range(0, len(records_list), batch_size):
            batch = records_list[i : i + batch_size]
            stmt = insert(models.IncomeStatement).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[models.IncomeStatement.ts_code, models.IncomeStatement.period],
                set_={
                    "revenue": stmt.excluded.revenue,
                    "operating_profit": stmt.excluded.operating_profit,
                    "total_profit": stmt.excluded.total_profit,
                    "net_profit": stmt.excluded.net_profit,
                    "basic_eps": stmt.excluded.basic_eps,
                    "diluted_eps": stmt.excluded.diluted_eps,
                },
            )
            await self.session.execute(stmt)
            logger.debug(f"[INCOME] 已插入/更新第 {i//batch_size + 1} 批，共 {len(batch)} 条记录")

    async def fetch_balance_sheet(self, ts_code: str) -> list[models.BalanceSheet]:
        """Cache-first fetch of balance sheet for a single symbol."""
        logger.info(f"[BALANCE] 开始获取 {ts_code} 的资产负债表数据")
        ttl = self.settings.financial_ttl_seconds
        data_type = "balance_sheet"
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, data_type, ttl_seconds=ttl):
            logger.info(f"[BALANCE] {ts_code} 缓存未过期，返回本地数据")
            result = await self.session.execute(
                select(models.BalanceSheet)
                .where(models.BalanceSheet.ts_code == ts_code)
                .order_by(models.BalanceSheet.period.desc())
            )
            return list(result.scalars().all())

        logger.info(f"[BALANCE] 调用 Tushare API 获取 balancesheet，ts_code={ts_code}")
        df = await self._run_with_retry(self.api.balancesheet, ts_code=ts_code)
        logger.info(f"[BALANCE] Tushare 返回 {len(df) if df is not None and not df.empty else 0} 条记录")
        if df is not None and not df.empty:
            logger.debug(f"[BALANCE] 返回数据的列: {list(df.columns)}")
        records = self._normalize_balance_sheet(df)
        records_list = list(records)
        logger.info(f"[BALANCE] 规范化后得到 {len(records_list)} 条记录")
        await self._upsert_balance_sheets(records_list)
        await self._mark_status(ts_code, data_type, ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.BalanceSheet)
            .where(models.BalanceSheet.ts_code == ts_code)
            .order_by(models.BalanceSheet.period.desc())
        )
        sheets = list(result.scalars().all())
        logger.info(f"[BALANCE] 最终返回 {len(sheets)} 条数据")
        return sheets

    def _normalize_balance_sheet(self, df: pd.DataFrame) -> Iterable[dict]:
        if df is None or df.empty:
            return []
        df = df.copy()
        df["period"] = df["end_date"].astype(str)
        cols = ["ts_code", "period", "total_assets", "total_liab", "total_equity", "fix_assets", "cur_assets", "cur_liab"]
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA
        for _, row in df[cols].iterrows():
            yield {
                "ts_code": row["ts_code"],
                "period": row["period"],
                "total_assets": float(row["total_assets"]) if pd.notna(row["total_assets"]) else None,
                "total_liab": float(row["total_liab"]) if pd.notna(row["total_liab"]) else None,
                "total_equity": float(row["total_equity"]) if pd.notna(row["total_equity"]) else None,
                "fixed_assets": float(row["fix_assets"]) if pd.notna(row["fix_assets"]) else None,
                "current_assets": float(row["cur_assets"]) if pd.notna(row["cur_assets"]) else None,
                "current_liab": float(row["cur_liab"]) if pd.notna(row["cur_liab"]) else None,
            }

    async def _upsert_balance_sheets(self, records: Iterable[dict]) -> None:
        records_list = list(records)
        if not records_list:
            return
        logger.info(f"[BALANCE] 准备插入/更新 {len(records_list)} 条资产负债表记录")
        batch_size = 100
        for i in range(0, len(records_list), batch_size):
            batch = records_list[i : i + batch_size]
            stmt = insert(models.BalanceSheet).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[models.BalanceSheet.ts_code, models.BalanceSheet.period],
                set_={
                    "total_assets": stmt.excluded.total_assets,
                    "total_liab": stmt.excluded.total_liab,
                    "total_equity": stmt.excluded.total_equity,
                    "fixed_assets": stmt.excluded.fixed_assets,
                    "current_assets": stmt.excluded.current_assets,
                    "current_liab": stmt.excluded.current_liab,
                },
            )
            await self.session.execute(stmt)
            logger.debug(f"[BALANCE] 已插入/更新第 {i//batch_size + 1} 批，共 {len(batch)} 条记录")

    async def fetch_cash_flow(self, ts_code: str) -> list[models.CashFlowStatement]:
        """Cache-first fetch of cash flow statement for a single symbol."""
        logger.info(f"[CASHFLOW] 开始获取 {ts_code} 的现金流量表数据")
        ttl = self.settings.financial_ttl_seconds
        data_type = "cash_flow"
        await self._ensure_stock(ts_code)
        if not await self._is_stale(ts_code, data_type, ttl_seconds=ttl):
            logger.info(f"[CASHFLOW] {ts_code} 缓存未过期，返回本地数据")
            result = await self.session.execute(
                select(models.CashFlowStatement)
                .where(models.CashFlowStatement.ts_code == ts_code)
                .order_by(models.CashFlowStatement.period.desc())
            )
            return list(result.scalars().all())

        logger.info(f"[CASHFLOW] 调用 Tushare API 获取 cashflow，ts_code={ts_code}")
        df = await self._run_with_retry(self.api.cashflow, ts_code=ts_code)
        logger.info(f"[CASHFLOW] Tushare 返回 {len(df) if df is not None and not df.empty else 0} 条记录")
        if df is not None and not df.empty:
            logger.debug(f"[CASHFLOW] 返回数据的列: {list(df.columns)}")
        records = self._normalize_cash_flow(df)
        records_list = list(records)
        logger.info(f"[CASHFLOW] 规范化后得到 {len(records_list)} 条记录")
        await self._upsert_cash_flow_statements(records_list)
        await self._mark_status(ts_code, data_type, ttl_seconds=ttl, stale=False)
        await self.session.commit()

        result = await self.session.execute(
            select(models.CashFlowStatement)
            .where(models.CashFlowStatement.ts_code == ts_code)
            .order_by(models.CashFlowStatement.period.desc())
        )
        statements = list(result.scalars().all())
        logger.info(f"[CASHFLOW] 最终返回 {len(statements)} 条数据")
        return statements

    def _normalize_cash_flow(self, df: pd.DataFrame) -> Iterable[dict]:
        if df is None or df.empty:
            return []
        df = df.copy()
        df["period"] = df["end_date"].astype(str)
        cols = ["ts_code", "period", "n_income", "c_oper_act", "c_inv_act", "c_fin_act", "free_cashflow"]
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA
        for _, row in df[cols].iterrows():
            yield {
                "ts_code": row["ts_code"],
                "period": row["period"],
                "net_profit": float(row["n_income"]) if pd.notna(row["n_income"]) else None,
                "oper_cash_flow": float(row["c_oper_act"]) if pd.notna(row["c_oper_act"]) else None,
                "inv_cash_flow": float(row["c_inv_act"]) if pd.notna(row["c_inv_act"]) else None,
                "fin_cash_flow": float(row["c_fin_act"]) if pd.notna(row["c_fin_act"]) else None,
                "free_cash_flow": float(row["free_cashflow"]) if pd.notna(row["free_cashflow"]) else None,
            }

    async def _upsert_cash_flow_statements(self, records: Iterable[dict]) -> None:
        records_list = list(records)
        if not records_list:
            return
        logger.info(f"[CASHFLOW] 准备插入/更新 {len(records_list)} 条现金流量表记录")
        batch_size = 100
        for i in range(0, len(records_list), batch_size):
            batch = records_list[i : i + batch_size]
            stmt = insert(models.CashFlowStatement).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[models.CashFlowStatement.ts_code, models.CashFlowStatement.period],
                set_={
                    "net_profit": stmt.excluded.net_profit,
                    "oper_cash_flow": stmt.excluded.oper_cash_flow,
                    "inv_cash_flow": stmt.excluded.inv_cash_flow,
                    "fin_cash_flow": stmt.excluded.fin_cash_flow,
                    "free_cash_flow": stmt.excluded.free_cash_flow,
                },
            )
            await self.session.execute(stmt)
            logger.debug(f"[CASHFLOW] 已插入/更新第 {i//batch_size + 1} 批，共 {len(batch)} 条记录")
