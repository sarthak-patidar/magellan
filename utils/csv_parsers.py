"""Broker-specific CSV parsers. Each returns a list[Trade] using the utils.fifo.Trade dataclass."""
from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import List
import csv

from utils.fifo import Trade


def parse_kite_tradebook(path: str | Path) -> List[Trade]:
    trades: list[Trade] = []
    with open(path) as f:
        for row in csv.DictReader(f):
            symbol = f"{row['symbol']}.NS"  # yfinance-style
            side = row["trade_type"].strip().upper()
            trades.append(Trade(
                symbol=symbol,
                side=side,
                qty=float(row["quantity"]),
                price=float(row["price"]),
                trade_date=date.fromisoformat(row["trade_date"]),
            ))
    return trades


def parse_indmoney_trades(path: str | Path) -> List[Trade]:
    trades: list[Trade] = []
    with open(path) as f:
        for row in csv.DictReader(f):
            trades.append(Trade(
                symbol=row["Symbol"].strip().upper(),
                side=row["Action"].strip().upper(),
                qty=float(row["Quantity"]),
                price=float(row["Price (USD)"]),
                trade_date=datetime.strptime(row["Date"], "%Y-%m-%d").date(),
            ))
    return trades


# Coin MF has its own shape — stub for now; populate when user provides a real export
def parse_coin_mf_tradebook(path: str | Path) -> List[Trade]:
    raise NotImplementedError(
        "Populate this parser once a real Zerodha Coin tradebook export is available. "
        "The column shape differs from equity Kite Tradebook."
    )
