from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Portfolio Management Agent"
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/portfolio.db",
        description="SQLite database URL for local-first cache",
    )
    tushare_token: str = Field(..., env="TUSHARE_TOKEN")
    deepseek_api_key: str | None = Field(default=None, env="DEEPSEEK_API_KEY")

    price_ttl_seconds: int = Field(default=24 * 60 * 60, description="TTL for price data")
    financial_ttl_seconds: int = Field(default=90 * 24 * 60 * 60, description="TTL for financials")
    valuation_ttl_seconds: int = Field(default=24 * 60 * 60, description="TTL for valuation snapshots")

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
