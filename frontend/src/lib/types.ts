export interface PriceHistory {
  id: number;
  ts_code: string;
  trade_date: string;
  close: number;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  volume?: number | null;
}

export interface Financial {
  id: number;
  ts_code: string;
  period: string;
  revenue?: number | null;
  profit?: number | null;
  roe?: number | null;
  roa?: number | null;
  debt_ratio?: number | null;
}

export interface Valuation {
  id: number;
  ts_code: string;
  date: string;
  pe?: number | null;
  pb?: number | null;
  ps?: number | null;
  ev_ebitda?: number | null;
}

export interface Portfolio {
  id: number;
  name: string;
  created_at: string;
}

export interface Holding {
  id: number;
  portfolio_id: number;
  ts_code: string;
  qty: number;
  buy_price: number;
  buy_date?: string | null;
  tags?: string | null;
}

export interface Analysis {
  id: number;
  ts_code?: string | null;
  method: string;
  target_return?: number | null;
  horizon_years?: number | null;
  probability?: number | null;
  params_json?: {
    mu?: number;
    sigma?: number;
    n_returns?: number;
    report?: string;
  } | null;
  created_at: string;
}

export interface JobStatus {
  status: string;
  symbols?: string[];
}

export interface Stock {
  id: number;
  ts_code: string;
  name?: string | null;
  sector?: string | null;
  active: boolean;
}

export interface StockListResponse {
  stocks: Stock[];
  total: number;
}

export interface IncomeStatement {
  id: number;
  ts_code: string;
  period: string;
  revenue?: number | null;
  operating_profit?: number | null;
  total_profit?: number | null;
  net_profit?: number | null;
  basic_eps?: number | null;
  diluted_eps?: number | null;
}

export interface BalanceSheet {
  id: number;
  ts_code: string;
  period: string;
  total_assets?: number | null;
  total_liab?: number | null;
  total_equity?: number | null;
  fixed_assets?: number | null;
  current_assets?: number | null;
  current_liab?: number | null;
}

export interface CashFlowStatement {
  id: number;
  ts_code: string;
  period: string;
  net_profit?: number | null;
  oper_cash_flow?: number | null;
  inv_cash_flow?: number | null;
  fin_cash_flow?: number | null;
  free_cash_flow?: number | null;
}

export interface StockDetailResponse {
  stock: Stock;
  latest_price?: PriceHistory | null;
  latest_valuation?: Valuation | null;
  latest_financial?: Financial | null;
  income_statements: IncomeStatement[];
  balance_sheets: BalanceSheet[];
  cash_flow_statements: CashFlowStatement[];
}
