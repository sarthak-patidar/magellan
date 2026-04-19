"""Thin yfinance MCP: quotes, history, FX. EOD only."""
from __future__ import annotations
from datetime import date
import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("market-data")


@mcp.tool()
def quote(symbol: str) -> dict:
    """Return latest EOD close, previous close, and day change for a ticker."""
    t = yf.Ticker(symbol)
    hist = t.history(period="5d")
    if hist.empty:
        return {"error": f"no data for {symbol}"}
    last = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) >= 2 else last
    return {
        "symbol": symbol,
        "close": float(last["Close"]),
        "prev_close": float(prev["Close"]),
        "change_pct": float((last["Close"] / prev["Close"] - 1) * 100),
        "as_of": str(hist.index[-1].date()),
    }


@mcp.tool()
def history(symbol: str, period: str = "1y") -> dict:
    """Return daily closes over a period. period: 1mo, 3mo, 6mo, 1y, 2y, 5y."""
    t = yf.Ticker(symbol)
    hist = t.history(period=period)
    if hist.empty:
        return {"error": f"no data for {symbol}"}
    return {
        "symbol": symbol,
        "closes": [
            {"date": str(d.date()), "close": float(c)}
            for d, c in hist["Close"].items()
        ],
    }


@mcp.tool()
def fx_usdinr() -> dict:
    """Return latest USD/INR spot close."""
    t = yf.Ticker("USDINR=X")
    hist = t.history(period="5d")
    if hist.empty:
        return {"error": "no FX data"}
    return {
        "pair": "USDINR",
        "rate": float(hist.iloc[-1]["Close"]),
        "as_of": str(hist.index[-1].date()),
    }


@mcp.tool()
def fundamentals(symbol: str) -> dict:
    """Return basic fundamentals: PE, market cap, sector."""
    t = yf.Ticker(symbol)
    info = t.info
    return {
        "symbol": symbol,
        "pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }


if __name__ == "__main__":
    mcp.run()
