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
