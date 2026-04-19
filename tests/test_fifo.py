import pytest
from datetime import date
from utils.fifo import build_lots, Trade, Lot


def t(symbol, side, qty, price, d):
    return Trade(symbol=symbol, side=side, qty=qty, price=price, trade_date=date.fromisoformat(d))


def test_single_buy_makes_one_lot():
    trades = [t("RELIANCE.NS", "BUY", 10, 2400.0, "2025-01-10")]
    lots = build_lots(trades)
    assert len(lots) == 1
    assert lots[0].qty == 10
    assert lots[0].cost_basis == 24000.0
    assert lots[0].entry_date == date(2025, 1, 10)


def test_two_buys_two_lots_separate_dates():
    trades = [
        t("RELIANCE.NS", "BUY", 10, 2400.0, "2025-01-10"),
        t("RELIANCE.NS", "BUY", 5, 2500.0, "2025-02-15"),
    ]
    lots = build_lots(trades)
    assert len(lots) == 2
    assert lots[0].entry_date == date(2025, 1, 10)
    assert lots[1].entry_date == date(2025, 2, 15)


def test_partial_sell_reduces_oldest_lot_first():
    trades = [
        t("RELIANCE.NS", "BUY", 10, 2400.0, "2025-01-10"),
        t("RELIANCE.NS", "BUY", 10, 2500.0, "2025-02-15"),
        t("RELIANCE.NS", "SELL", 6, 2600.0, "2025-03-10"),
    ]
    lots = build_lots(trades)
    assert len(lots) == 2
    assert lots[0].qty == 4              # oldest lot reduced 10 -> 4
    assert lots[0].entry_date == date(2025, 1, 10)
    assert lots[1].qty == 10             # newer lot untouched


def test_sell_exceeds_oldest_consumes_next_lot():
    trades = [
        t("RELIANCE.NS", "BUY", 10, 2400.0, "2025-01-10"),
        t("RELIANCE.NS", "BUY", 10, 2500.0, "2025-02-15"),
        t("RELIANCE.NS", "SELL", 12, 2600.0, "2025-03-10"),
    ]
    lots = build_lots(trades)
    assert len(lots) == 1                # first lot fully consumed
    assert lots[0].qty == 8
    assert lots[0].entry_date == date(2025, 2, 15)


def test_oversell_raises():
    trades = [
        t("RELIANCE.NS", "BUY", 10, 2400.0, "2025-01-10"),
        t("RELIANCE.NS", "SELL", 11, 2500.0, "2025-02-10"),
    ]
    with pytest.raises(ValueError, match="oversell"):
        build_lots(trades)


def test_trades_sorted_by_date_automatically():
    trades = [
        t("X", "SELL", 3, 110.0, "2025-02-01"),
        t("X", "BUY", 10, 100.0, "2025-01-01"),
    ]
    lots = build_lots(trades)
    assert len(lots) == 1
    assert lots[0].qty == 7
