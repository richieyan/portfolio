from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index, JSON, PrimaryKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Stock(Base):
    __tablename__ = "stocks"
    __table_args__ = (Index("idx_stock_active", "active"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(128))
    sector: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    prices: Mapped[list["PriceHistory"]] = relationship(back_populates="stock")
    holdings: Mapped[list["Holding"]] = relationship(back_populates="stock")


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date", name="uix_price_ts_date"),
        Index("idx_price_ts_date", "ts_code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(32), ForeignKey("stocks.ts_code"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    open: Mapped[Optional[float]] = mapped_column(Float)
    high: Mapped[Optional[float]] = mapped_column(Float)
    low: Mapped[Optional[float]] = mapped_column(Float)
    volume: Mapped[Optional[float]] = mapped_column(Float)

    stock: Mapped[Stock] = relationship(back_populates="prices")


class Financial(Base):
    __tablename__ = "financials"
    __table_args__ = (
        UniqueConstraint("ts_code", "period", name="uix_financial_ts_period"),
        Index("idx_financial_ts_period", "ts_code", "period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(32), ForeignKey("stocks.ts_code"), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    profit: Mapped[Optional[float]] = mapped_column(Float)
    roe: Mapped[Optional[float]] = mapped_column(Float)
    roa: Mapped[Optional[float]] = mapped_column(Float)
    debt_ratio: Mapped[Optional[float]] = mapped_column(Float)


class Valuation(Base):
    __tablename__ = "valuations"
    __table_args__ = (
        UniqueConstraint("ts_code", "date", name="uix_valuation_ts_date"),
        Index("idx_valuation_ts_date", "ts_code", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(32), ForeignKey("stocks.ts_code"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    pe: Mapped[Optional[float]] = mapped_column(Float)
    pb: Mapped[Optional[float]] = mapped_column(Float)
    ps: Mapped[Optional[float]] = mapped_column(Float)
    ev_ebitda: Mapped[Optional[float]] = mapped_column(Float)


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    holdings: Mapped[list["Holding"]] = relationship(back_populates="portfolio")


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ts_code", name="uix_holding_portfolio_ts"),
        Index("idx_holding_portfolio_ts", "portfolio_id", "ts_code"),
        Index("idx_holding_buy_date", "buy_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ts_code: Mapped[str] = mapped_column(String(32), ForeignKey("stocks.ts_code"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    buy_date: Mapped[Optional[date]] = mapped_column(Date)
    tags: Mapped[Optional[str]] = mapped_column(String(256))

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
    stock: Mapped[Stock] = relationship(back_populates="holdings")


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("idx_analysis_created", "created_at"),
        Index("idx_analysis_ts_created", "ts_code", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[Optional[str]] = mapped_column(String(32), ForeignKey("stocks.ts_code"))
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    target_return: Mapped[Optional[float]] = mapped_column(Float)
    horizon_years: Mapped[Optional[float]] = mapped_column(Float)
    probability: Mapped[Optional[float]] = mapped_column(Float)
    params_json: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_job_status", "status"),
        Index("idx_job_type", "type"),
        Index("idx_job_started", "started_at"),
        Index("idx_job_finished", "finished_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    progress: Mapped[Optional[float]] = mapped_column(Float)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    logs: Mapped[Optional[str]] = mapped_column(Text)


class DataStatus(Base):
    __tablename__ = "data_status"
    __table_args__ = (
        PrimaryKeyConstraint("ts_code", "data_type", name="pk_data_status"),
        Index("idx_data_status_stale", "stale"),
        {"sqlite_with_rowid": False, "sqlite_strict": True},
    )

    ts_code: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(64))
    error_msg: Mapped[Optional[str]] = mapped_column(String(256))
