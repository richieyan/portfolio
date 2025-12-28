# Copilot Instructions: Portfolio Management Agent (Local-First)

Purpose: Align contributions with the PRD and enforce local-first, MCP-driven data access, accurate math models, and minimal, focused changes. See the product spec in [docs/PRD.md](docs/PRD.md).

## Core Principles
- Local-first cache: read from SQLite first; miss/expired → fetch via MCP, then write back.
- MCP-only data source: call `tushare-mcp` via CLI; do not `import tushare`.
- Accurate math: implement GBM/DCF using NumPy/SciPy; avoid pseudocode.
- Minimal changes: fix root causes, avoid unrelated edits, preserve existing style.
- Async-first backend: prefer SQLAlchemy Async + FastAPI.

## Environment
- Backend: Python 3.10+, FastAPI, SQLAlchemy (Async), Pydantic.
- Frontend: Next.js 14+ (App Router), TailwindCSS, shadcn/ui, Recharts.
- Data/Math: SQLite, Pandas, NumPy/SciPy.
- Env vars: `TUSHARE_TOKEN`, `DEEPSEEK_API_KEY`.

## MCP Usage (Required)
- Data must be fetched through MCP CLI with `uv tool`:
  - Command pattern:
    - `uv tool run tushare-mcp call [tool_name] --args '{"key": "value"}'`
  - Use Python `subprocess` or `asyncio.subprocess` to invoke CLI.
  - Parse JSON stdout; implement retries with backoff on transient errors/ratelimits.

## Database & Indexing (SQLite)
- Deduplication: unique composite keys per PRD.
- Recommended tables and keys (MVP):
  - `stocks(id, ts_code UNIQUE, name, sector, active)`; indexes: `active`, `sector`.
  - `price_history(id, ts_code, trade_date, close, open, high, low, volume)`; UNIQUE `(ts_code, trade_date)`; index `(ts_code, trade_date)`.
  - `financials(id, ts_code, period, revenue, profit, roe, roa, debt_ratio, ...)`; UNIQUE `(ts_code, period)`; index `(ts_code, period)`.
  - `valuations(id, ts_code, date, pe, pb, ps, ev_ebitda, ...)`; UNIQUE `(ts_code, date)`; index `(ts_code, date)`.
  - `portfolios(id, name UNIQUE, created_at)`; index `created_at`.
  - `holdings(id, portfolio_id, ts_code, qty, buy_price, buy_date, tags)`; UNIQUE `(portfolio_id, ts_code)`; indexes `(portfolio_id, ts_code)`, `buy_date`.
  - `analyses(id, ts_code NULLABLE, method, target_return, horizon, probability, params_json, created_at)`; indexes `created_at`, `(ts_code, created_at)`.
  - `jobs(id, type, status, progress, started_at, finished_at, logs)`; indexes `status`, `type`, `started_at`, `finished_at`.
- TTL/refresh metadata:
  - `data_status(ts_code, data_type, last_updated, ttl_seconds, stale, error_code, error_msg)`; PK `(ts_code, data_type)`; indexes `(ts_code, data_type)`, `stale`.
  - TTL defaults: prices ~1 day; financials ~90 days; valuations ~1 day (configurable).
- Integrity & performance:
  - Enable `PRAGMA foreign_keys=ON`.
  - Consider `STRICT` tables for type safety; `WITHOUT ROWID` for `data_status`.
  - Use REAL for ratios/prices in MVP; INTEGER for quantities; `CHECK probability BETWEEN 0 AND 1`.

## Project Structure (Suggested)
- `backend/`
  - `app/main.py` — FastAPI startup
  - `app/api/` — route modules
  - `app/db/models.py` — SQLAlchemy ORM models
  - `app/db/schemas.py` — Pydantic DTOs
  - `app/db/session.py` — async engine/session + PRAGMAs
  - `app/crud/` — query helpers
  - `app/services/tushare_mcp.py` — MCP CLI wrapper
  - `app/services/analysis_engine.py` — GBM/DCF calculators
  - `app/tasks/` — schedulers/job runners
  - `app/config.py` — env & settings
- `frontend/` — Next.js App Router UI
- `data/` — SQLite files & backups
- `scripts/` — maintenance/bootstrapping

## Service Layer Contracts
- `TushareMCPService`:
  - Methods per tool, input validation, retries/backoff, JSON parse, normalized outputs.
  - Error taxonomy: network/ratelimit/field-missing; structured logs.
- Caching policy:
  - Query path: check SQLite + TTL → (stale/miss) MCP fetch → write-back; enforce dedup by unique keys.
- `AnalysisEngine`:
  - GBM probability: estimate `mu`, `sigma`; compute $P = 1 - \Phi\left(\frac{\ln(1+R) - (\mu - \frac{1}{2}\sigma^2)T}{\sigma\sqrt{T}}\right)$.
  - DCF valuation: finite horizon + terminal value with discount; sensitivity flags (risk-free comparison, cash flow stability).

## Agent Integration
- DeepSeek Agent:
  - Prompt templates consume computed metrics (probabilities, valuation, sensitivity) and produce readable risk assessments.
  - Implement retries and timeouts; capture report in `analyses.params_json` and/or dedicated report storage.

## Workflow (MVP)
1. Step 1 — Database design: implement models, constraints, indexes.
2. Step 2 — Services: `TushareMCPService`, `AnalysisEngine` (GBM/DCF).
3. Step 3 — Agent orchestration: prompt templates + report generation.
4. Step 4 — API & Frontend: FastAPI routes, minimal Next.js pages.

## Collaboration & Quality
- Prefer surgical edits; do not reformat unrelated code.
- Update docs when schema/service contracts change.
- Write targeted tests around changed code; expand scope after confidence.
- Avoid adding license headers unless requested.

## References
- Product spec: [docs/PRD.md](docs/PRD.md)
- Design notes: [docs/deveploer.md](docs/deveploer.md), [docs/product-designer.md](docs/product-designer.md)


## Meta-Instructions: How to Update This File
You (Copilot) are responsible for maintaining this `copilot-instructions.md` file. 
When I command **"Update Instructions"** or **"Save Memory"**:
1.  **Reflect**: Analyze the current chat session, the code we just wrote, and any new architectural decisions or libraries we adopted.
2.  **Filter**: Only extract high-level patterns, strict constraints, or project-wide conventions. Do NOT include specific business logic or temporary code snippets.
3.  **Action**: Propose an edit to this file (`.github/copilot-instructions.md`).
    * If it's a new tech stack choice, update the "Tech Stack" section.
    * If it's a coding style rule, update the "Constraints" section.
    * Keep the file concise and structured.