from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StockBase(BaseModel):
    ts_code: str
    name: Optional[str] = None
    sector: Optional[str] = None
    active: bool = True


class StockCreate(StockBase):
    pass


class StockRead(StockBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PriceHistoryRead(BaseModel):
    id: int
    ts_code: str
    trade_date: date
    close: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class FinancialRead(BaseModel):
    id: int
    ts_code: str
    period: str
    revenue: Optional[float]
    profit: Optional[float]
    roe: Optional[float]
    roa: Optional[float]
    debt_ratio: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class ValuationRead(BaseModel):
    id: int
    ts_code: str
    date: date
    pe: Optional[float]
    pb: Optional[float]
    ps: Optional[float]
    ev_ebitda: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class PortfolioCreate(BaseModel):
    name: str


class PortfolioRead(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HoldingCreate(BaseModel):
    portfolio_id: int
    ts_code: str
    qty: int
    buy_price: float
    buy_date: Optional[date] = None
    tags: Optional[str] = None


class HoldingRead(HoldingCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AnalysisRead(BaseModel):
    id: int
    ts_code: Optional[str]
    method: str
    target_return: Optional[float]
    horizon_years: Optional[float]
    probability: Optional[float]
    params_json: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisCreate(BaseModel):
    ts_code: Optional[str]
    target_return: float
    horizon_years: float
    method: str = "gbm"


class RefreshRequest(BaseModel):
    ts_codes: list[str]


class JobRead(BaseModel):
    id: int
    type: str
    status: str
    progress: Optional[float]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    logs: Optional[str]

    model_config = ConfigDict(from_attributes=True)
