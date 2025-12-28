from __future__ import annotations

from typing import Optional

import httpx

from backend.app.config import get_settings
from backend.app.services.analysis_engine import AnalysisEngine


class DeepSeekService:
    """Generate analysis reports using computed metrics and optional DeepSeek API.

    If DEEPSEEK_API_KEY is absent, falls back to a local, deterministic summary.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.deepseek_api_key

    async def generate_report(
        self,
        ts_code: Optional[str],
        target_return: float,
        horizon_years: float,
        mu: float,
        sigma: float,
        probability: float,
    ) -> dict:
        summary = self._local_summary(ts_code, target_return, horizon_years, mu, sigma, probability)
        if not self.api_key:
            # Agent disabled; return local summary only.
            return {"source": "local", "summary": summary, "probability": probability, "mu": mu, "sigma": sigma}

        # Placeholder DeepSeek call with timeout/retries; falls back to local summary on failure.
        payload = {
            "model": "deepseek-chat",  # Placeholder model name; adjust if API differs.
            "messages": [
                {
                    "role": "system",
                    "content": "You are a risk analyst. Summarize probability and drivers succinctly.",
                },
                {
                    "role": "user",
                    "content": summary,
                },
            ],
        }

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {
                        "source": "deepseek",
                        "summary": content or summary,
                        "probability": probability,
                        "mu": mu,
                        "sigma": sigma,
                    }
            except Exception:  # pragma: no cover - external service
                if attempt == 2:
                    break
                continue

        # Fallback to local summary
        return {"source": "local-fallback", "summary": summary, "probability": probability, "mu": mu, "sigma": sigma}

    def _local_summary(
        self,
        ts_code: Optional[str],
        target_return: float,
        horizon_years: float,
        mu: float,
        sigma: float,
        probability: float,
    ) -> str:
        ident = ts_code or "portfolio"
        return (
            f"Analysis for {ident}: target_return={target_return:.2%}, "
            f"horizon={horizon_years:.2f}y, mu={mu:.4f}, sigma={sigma:.4f}, "
            f"probability={probability:.2%}."
        )
