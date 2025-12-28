# Portfolio Management Agent (MVP)

FastAPI backend with local-first SQLite cache, Tushare-driven data fetch, and analysis utilities.

## Setup (uv)

1. Install uv (https://docs.astral.sh/uv/):

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Sync project dependencies into a local virtualenv:

```
uv sync
```

3. Export env vars:

```
export TUSHARE_TOKEN="<your_token>"
export DEEPSEEK_API_KEY="<optional_key>"
```

## Run Server

```
uv run python main.py
```

Server runs at http://localhost:8000

## API (MVP)

- GET /health — service status
- POST /api/v1/prices/{ts_code}/refresh — fetch+cache daily prices
- GET /api/v1/prices/{ts_code}?limit=200 — list cached prices
- POST /api/v1/financials/{ts_code}/refresh — fetch+cache financial indicators
- GET /api/v1/financials/{ts_code}?limit=40 — list financials
- POST /api/v1/valuations/{ts_code}/refresh — fetch+cache valuation snapshots
- GET /api/v1/valuations/{ts_code}?limit=60 — list valuations
- POST /api/v1/analyses — compute GBM probability (optionally fetch prices) and return analysis record
- POST /api/v1/jobs/refresh — enqueue batch refresh for symbols (prices/financials/valuations)

Notes:
- Data is cached in data/portfolio.db with TTLs from config.
- Financials use `fina_indicator` (ROE/ROA/debt ratio); revenue/profit optional.
- Valuations use `daily_basic` (PE, PB, PS).
- Use `uv run` to execute commands inside the project venv (e.g., `uv run uvicorn backend.app.main:app --reload`).
- Analyses use cached price history for mu/sigma estimation, compute GBM exceedance probability, and optionally call DeepSeek (if key set) for narrative.
