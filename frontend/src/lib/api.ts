import { Analysis, Financial, Holding, JobStatus, Portfolio, PriceHistory, Valuation } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return (await res.json()) as T;
}

export async function fetchPrices(tsCode: string, limit = 200): Promise<PriceHistory[]> {
  return request<PriceHistory[]>(`/api/v1/prices/${encodeURIComponent(tsCode)}?limit=${limit}`);
}

export async function refreshPrices(tsCode: string): Promise<PriceHistory[]> {
  return request<PriceHistory[]>(`/api/v1/prices/${encodeURIComponent(tsCode)}/refresh`, {
    method: "POST",
  });
}

export async function fetchValuations(tsCode: string, limit = 60): Promise<Valuation[]> {
  return request<Valuation[]>(`/api/v1/valuations/${encodeURIComponent(tsCode)}?limit=${limit}`);
}

export async function refreshValuations(tsCode: string): Promise<Valuation[]> {
  return request<Valuation[]>(`/api/v1/valuations/${encodeURIComponent(tsCode)}/refresh`, {
    method: "POST",
  });
}

export async function fetchFinancials(tsCode: string, limit = 40): Promise<Financial[]> {
  return request<Financial[]>(`/api/v1/financials/${encodeURIComponent(tsCode)}?limit=${limit}`);
}

export async function refreshFinancials(tsCode: string): Promise<Financial[]> {
  return request<Financial[]>(`/api/v1/financials/${encodeURIComponent(tsCode)}/refresh`, {
    method: "POST",
  });
}

export async function createAnalysis(payload: {
  ts_code?: string;
  target_return: number;
  horizon_years: number;
  method?: string;
}): Promise<Analysis> {
  return request<Analysis>(`/api/v1/analyses`, {
    method: "POST",
    body: JSON.stringify({ ...payload, method: payload.method || "gbm" }),
  });
}

export async function enqueueRefreshJob(tsCodes: string[]): Promise<JobStatus> {
  return request<JobStatus>(`/api/v1/jobs/refresh`, {
    method: "POST",
    body: JSON.stringify({ ts_codes: tsCodes }),
  });
}

export async function listPortfolios(): Promise<Portfolio[]> {
  return request<Portfolio[]>(`/api/v1/portfolios`);
}

export async function createPortfolio(name: string): Promise<Portfolio> {
  return request<Portfolio>(`/api/v1/portfolios`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listHoldings(portfolioId: number): Promise<Holding[]> {
  return request<Holding[]>(`/api/v1/portfolios/${portfolioId}/holdings`);
}

export async function createHolding(payload: {
  portfolio_id: number;
  ts_code: string;
  qty: number;
  buy_price: number;
  buy_date?: string;
  tags?: string;
}): Promise<Holding> {
  return request<Holding>(`/api/v1/holdings`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateHolding(holdingId: number, payload: Partial<Omit<Holding, "id" | "portfolio_id" | "ts_code">>): Promise<Holding> {
  return request<Holding>(`/api/v1/holdings/${holdingId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteHolding(holdingId: number): Promise<void> {
  await request(`/api/v1/holdings/${holdingId}`, { method: "DELETE" });
}
