"""FIFO lot builder. Takes a list of trades, returns open lots per symbol."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class Trade:
    symbol: str
    side: str          # "BUY" or "SELL"
    qty: float
    price: float
    trade_date: date


@dataclass
class Lot:
    symbol: str
    qty: float
    cost_basis: float  # native currency
    entry_date: date


def build_lots(trades: List[Trade]) -> List[Lot]:
    """Reconstruct open lots by replaying trades chronologically, FIFO."""
    trades = sorted(trades, key=lambda t: t.trade_date)
    open_lots_by_symbol: dict[str, List[Lot]] = {}

    for tr in trades:
        book = open_lots_by_symbol.setdefault(tr.symbol, [])
        if tr.side == "BUY":
            book.append(Lot(
                symbol=tr.symbol,
                qty=tr.qty,
                cost_basis=tr.qty * tr.price,
                entry_date=tr.trade_date,
            ))
        elif tr.side == "SELL":
            remaining = tr.qty
            while remaining > 0 and book:
                lot = book[0]
                if lot.qty <= remaining:
                    remaining -= lot.qty
                    book.pop(0)
                else:
                    # partial consume: reduce qty and cost_basis proportionally
                    ratio = remaining / lot.qty
                    lot.cost_basis -= lot.cost_basis * ratio
                    lot.qty -= remaining
                    remaining = 0
            if remaining > 0:
                raise ValueError(f"oversell: {tr.symbol} sell {tr.qty} exceeds holdings on {tr.trade_date}")
        else:
            raise ValueError(f"unknown side: {tr.side}")

    result: List[Lot] = []
    for book in open_lots_by_symbol.values():
        result.extend(book)
    return result
