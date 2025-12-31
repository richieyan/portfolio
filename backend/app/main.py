from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.db import models
from backend.app.db.session import engine
from backend.app.api import analyses, financials, holdings, jobs, portfolios, prices, valuations


app = FastAPI(title=get_settings().app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"]
)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

app.include_router(prices.router)
app.include_router(financials.router)
app.include_router(valuations.router)
app.include_router(analyses.router)
app.include_router(jobs.router)
app.include_router(portfolios.router)
app.include_router(holdings.router)
