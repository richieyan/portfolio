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


class HoldingUpdate(BaseModel):
    qty: Optional[int] = None
    buy_price: Optional[float] = None
    buy_date: Optional[date] = None
    tags: Optional[str] = None


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


class IncomeStatementRead(BaseModel):
    id: int
    ts_code: str
    period: str
    revenue: Optional[float] = None
    operating_profit: Optional[float] = None
    total_profit: Optional[float] = None
    net_profit: Optional[float] = None
    basic_eps: Optional[float] = None
    diluted_eps: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BalanceSheetRead(BaseModel):
    id: int
    ts_code: str
    period: str
    total_assets: Optional[float] = None
    total_liab: Optional[float] = None
    total_equity: Optional[float] = None
    fixed_assets: Optional[float] = None
    current_assets: Optional[float] = None
    current_liab: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CashFlowStatementRead(BaseModel):
    id: int
    ts_code: str
    period: str
    net_profit: Optional[float] = None
    oper_cash_flow: Optional[float] = None
    inv_cash_flow: Optional[float] = None
    fin_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class StockListResponse(BaseModel):
    stocks: list[StockRead]
    total: int


class StockDetailResponse(BaseModel):
    stock: StockRead
    latest_price: Optional[PriceHistoryRead] = None
    latest_valuation: Optional[ValuationRead] = None
    latest_financial: Optional[FinancialRead] = None
    income_statements: list[IncomeStatementRead] = []
    balance_sheets: list[BalanceSheetRead] = []
    cash_flow_statements: list[CashFlowStatementRead] = []
