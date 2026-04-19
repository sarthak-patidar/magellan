import pandas as pd
import pytest
from utils.momentum import compute_momentum, MomentumScore


def _prices(start, n, step):
    """Linear-step synthetic price series."""
    return pd.Series(
        [100 + step * i for i in range(n)],
        index=pd.bdate_range(start=start, periods=n),
    )


def test_strong_uptrend_gives_positive_composite():
    prices = _prices("2025-01-01", 260, step=0.5)  # ~1 year of rising
    bench = _prices("2025-01-01", 260, step=0.2)
    score = compute_momentum("ABC", prices, bench)
    assert score.m3 > 0
    assert score.m6 > 0
    assert score.m12 > 0
    assert score.rs_vs_bench > 0
    assert score.above_200dma is True


def test_downtrend_is_penalized():
    prices = _prices("2025-01-01", 260, step=-0.5)
    bench = _prices("2025-01-01", 260, step=0.2)
    score = compute_momentum("XYZ", prices, bench)
    assert score.m12 < 0
    assert score.rs_vs_bench < 0
    assert score.above_200dma is False


def test_insufficient_history_raises():
    prices = _prices("2025-01-01", 30, step=0.5)  # only 30 days
    bench = _prices("2025-01-01", 30, step=0.2)
    with pytest.raises(ValueError, match="history"):
        compute_momentum("SHORT", prices, bench)
