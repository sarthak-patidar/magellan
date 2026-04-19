from datetime import date
from utils.csv_parsers import parse_kite_tradebook, parse_indmoney_trades


def test_parse_kite_tradebook():
    trades = parse_kite_tradebook("tests/fixtures/kite-tradebook.csv")
    assert len(trades) == 3
    t = trades[0]
    assert t.symbol == "RELIANCE.NS"  # normalized to yfinance-style
    assert t.side == "BUY"
    assert t.qty == 10
    assert t.price == 2400.00
    assert t.trade_date == date(2025, 1, 10)


def test_parse_indmoney_trades():
    trades = parse_indmoney_trades("tests/fixtures/indmoney-trades.csv")
    assert len(trades) == 2
    t = trades[0]
    assert t.symbol == "NVDA"
    assert t.side == "BUY"
    assert t.qty == 10
    assert t.price == 785.00
    assert t.trade_date == date(2024, 9, 3)
