"""Composite momentum score: returns over 3/6/12m + RS vs benchmark + 200-DMA posture."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd


@dataclass
class MomentumScore:
    ticker: str
    m3: float
    m6: float
    m12: float
    rs_vs_bench: float
    above_200dma: bool
    composite: float


def _return_over(prices: pd.Series, business_days: int) -> float:
    if len(prices) < business_days + 1:
        raise ValueError(f"insufficient history: need {business_days + 1} points, got {len(prices)}")
    return (prices.iloc[-1] / prices.iloc[-business_days - 1]) - 1.0


def compute_momentum(ticker: str, prices: pd.Series, bench: pd.Series) -> MomentumScore:
    if len(prices) < 260 or len(bench) < 260:
        raise ValueError("insufficient history: need >=260 business days for 12m momentum")

    m3 = _return_over(prices, 63)       # ~3 business months
    m6 = _return_over(prices, 126)
    m12 = _return_over(prices, 252)
    bench12 = _return_over(bench, 252)
    rs = m12 - bench12
    above_200 = bool(prices.iloc[-1] > prices.iloc[-200:].mean())
    composite = (m3 + m6 + m12) / 3.0   # equal-weighted by default

    return MomentumScore(
        ticker=ticker,
        m3=m3, m6=m6, m12=m12,
        rs_vs_bench=rs,
        above_200dma=above_200,
        composite=composite,
    )
