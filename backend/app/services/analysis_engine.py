from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from scipy.stats import norm


class AnalysisEngine:
    @staticmethod
    def gbm_target_probability(mu: float, sigma: float, target_return: float, horizon_years: float) -> float:
        """Probability that return exceeds target under GBM.

        P = 1 - Phi((ln(1+R) - (mu - 0.5*sigma^2)T) / (sigma*sqrt(T)))
        """
        if sigma <= 0 or horizon_years <= 0:
            return 0.0
        threshold = math.log(1 + target_return)
        drift = (mu - 0.5 * sigma**2) * horizon_years
        diffusion = sigma * math.sqrt(horizon_years)
        z = (threshold - drift) / diffusion
        return float(1 - norm.cdf(z))

    @staticmethod
    def estimate_mu_sigma(returns: Iterable[float]) -> tuple[float, float]:
        arr = np.array(list(returns), dtype=float)
        if arr.size == 0:
            return 0.0, 0.0
        mu = float(np.mean(arr))
        sigma = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
        return mu, sigma

    @staticmethod
    def discounted_cash_flow(
        cash_flows: Iterable[float],
        discount_rate: float,
        terminal_growth: float = 0.0,
    ) -> float:
        """Finite horizon DCF with terminal value."""
        flows = list(cash_flows)
        if discount_rate <= terminal_growth:
            raise ValueError("Discount rate must exceed terminal growth")
        value = 0.0
        for t, cf in enumerate(flows, start=1):
            value += cf / ((1 + discount_rate) ** t)
        if flows:
            terminal_cf = flows[-1] * (1 + terminal_growth)
            terminal_value = terminal_cf / (discount_rate - terminal_growth)
            value += terminal_value / ((1 + discount_rate) ** len(flows))
        return float(value)
