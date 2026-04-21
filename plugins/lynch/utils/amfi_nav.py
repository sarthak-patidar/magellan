"""Parse AMFI's daily NAV file. Public URL: https://www.amfiindia.com/spages/NAVAll.txt"""
from __future__ import annotations
from pathlib import Path


def parse_amfi_nav_file(path: str | Path) -> dict[str, dict]:
    """Return {isin_growth: {scheme_name, nav, date}}.

    AMFI file is semi-structured text with ';' delimiters. Skip category/AMC
    headers (they have fewer than 6 fields).
    """
    result: dict[str, dict] = {}
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split(";")
            if len(parts) < 6:
                continue
            scheme_code, isin_growth, isin_div_reinv, scheme_name, nav, d = parts[:6]
            if not isin_growth or isin_growth == "ISIN Div Payout/ ISIN Growth":
                continue  # header row
            try:
                nav_f = float(nav)
            except ValueError:
                continue
            result[isin_growth] = {
                "scheme_code": scheme_code,
                "scheme_name": scheme_name,
                "nav": nav_f,
                "date": d,
            }
    return result


def fetch_amfi_nav_url() -> str:
    """Return the canonical URL. Downloaded lazily by a skill, not this module."""
    return "https://www.amfiindia.com/spages/NAVAll.txt"
