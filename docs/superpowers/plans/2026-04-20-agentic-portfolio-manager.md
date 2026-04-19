# Agentic Portfolio Manager — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Cowork plugin that delivers a personal agentic portfolio manager for India (Zerodha Kite + Coin) and US (IndMoney) — advisory only, momentum + rebalance workflows, CSV-first ingestion with Kite MCP as a drop-in upgrade.

**Architecture:** Cowork plugin = plugin manifest + 7 skills (markdown playbooks) + 5 subagents (markdown definitions) + 3 small Python utilities (FIFO lot builder, tax rule matcher, momentum scorer) + one thin market-data MCP. All portfolio state lives as plain YAML/markdown in a `portfolio/` folder the user owns. Remote Kite MCP is registered in the plugin's MCP config so it's available inside Cowork sessions (bypassing the Desktop-only config).

**Tech Stack:**
- Claude Code plugin layout (works inside Cowork): `.claude-plugin/plugin.json`, `skills/`, `agents/`, `.mcp.json`
- Python 3.11+ with `pytest`, `pyyaml`, `yfinance`, `pandas` for utilities
- Zero-code surfaces everywhere possible; Python only where rule/logic correctness matters

**Spec reference:** `docs/superpowers/specs/2026-04-20-agentic-portfolio-manager-design.md`

**Conventions for every task below:**
- Use `~/PycharmProjects/portfolio-management` as the repo root. Paths below are relative to this root.
- Commit after every task with a conventional-commit-style message.
- Run `pytest` for the touched module after each code change; do not mark a step complete until it's green.

---

## Task 1: Initialize repository + plugin scaffold

**Files:**
- Create: `.gitignore`
- Create: `.claude-plugin/plugin.json`
- Create: `.mcp.json`
- Create: `README.md`
- Create folders: `skills/`, `agents/`, `utils/`, `portfolio/`, `tests/`, `imports/`

- [ ] **Step 1: Initialize git**

```bash
cd ~/PycharmProjects/portfolio-management
git init
git add docs/
git commit -m "docs: add brainstorming spec for agentic portfolio manager"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/

# IDE
.idea/

# Portfolio secrets — never commit live holdings/imports
/portfolio/holdings.yaml
/imports/
*.csv
*.xlsx

# OS
.DS_Store
```

- [ ] **Step 3: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "personal-pm",
  "version": "0.1.0",
  "description": "Personal agentic portfolio manager for India (Kite/Coin) and US (IndMoney). Advisory only, CSV-first.",
  "author": {"name": "Symplora"},
  "skills": ["skills"],
  "agents": ["agents"],
  "mcpServers": ".mcp.json"
}
```

- [ ] **Step 4: Create `.mcp.json` (MCP registrations)**

```json
{
  "mcpServers": {
    "kite": {
      "type": "sse",
      "url": "https://mcp.kite.trade/mcp"
    }
  }
}
```

(Market-data MCP gets added in Task 9. Kite is remote-SSE so no local install.)

- [ ] **Step 5: Create `README.md`**

```markdown
# personal-pm

Personal agentic portfolio manager built as a Cowork plugin. Advisory only — no trade execution.

## Install (inside Cowork)
1. In Cowork: Plugins → Install from folder → select this directory.
2. On first run, invoke the `financial-plan` skill to author your IPS.
3. Drop CSVs into `imports/YYYY-MM-DD/` and invoke `holdings-import`.

## Markets & brokers
- India: Zerodha Kite (equity) and Zerodha Coin (MF) — CSV or Kite MCP.
- US: IndMoney (Alpaca-backed) — CSV only (no public API).

See `docs/superpowers/specs/2026-04-20-agentic-portfolio-manager-design.md` for the full design.
```

- [ ] **Step 6: Create folders + placeholders**

```bash
mkdir -p skills agents utils portfolio tests imports
touch skills/.gitkeep agents/.gitkeep utils/.gitkeep tests/.gitkeep
```

- [ ] **Step 7: Commit**

```bash
git add .gitignore .claude-plugin/ .mcp.json README.md skills/ agents/ utils/ portfolio/ tests/ imports/
git commit -m "chore: scaffold personal-pm plugin"
```

---

## Task 2: State file JSON schemas

**Files:**
- Create: `schemas/accounts.schema.json`
- Create: `schemas/targets.schema.json`
- Create: `schemas/constraints.schema.json`
- Create: `schemas/tax-rules.schema.json`
- Create: `schemas/universe.schema.json`
- Create: `schemas/holdings.schema.json`

- [ ] **Step 1: Create `schemas/accounts.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["accounts"],
  "properties": {
    "accounts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "broker", "market", "currency", "source", "residency"],
        "properties": {
          "id": {"type": "string"},
          "broker": {"enum": ["zerodha_kite", "zerodha_coin", "indmoney_alpaca"]},
          "market": {"enum": ["IN", "US"]},
          "currency": {"enum": ["INR", "USD"]},
          "source": {"enum": ["csv", "mcp"]},
          "residency": {"enum": ["IN", "US"]}
        }
      }
    }
  }
}
```

- [ ] **Step 2: Create `schemas/targets.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["asset_class_bands", "per_market_caps"],
  "properties": {
    "asset_class_bands": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["target", "min", "max"],
        "properties": {
          "target": {"type": "number", "minimum": 0, "maximum": 1},
          "min": {"type": "number", "minimum": 0, "maximum": 1},
          "max": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    },
    "per_market_caps": {
      "type": "object",
      "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1}
    }
  }
}
```

- [ ] **Step 3: Create `schemas/constraints.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["min_hold_days", "turnover_cap_monthly", "concentration_caps", "benchmarks"],
  "properties": {
    "min_hold_days": {"type": "integer", "minimum": 0},
    "turnover_cap_monthly": {"type": "number", "minimum": 0, "maximum": 1},
    "concentration_caps": {
      "type": "object",
      "required": ["single_issuer", "sector"],
      "properties": {
        "single_issuer": {"type": "number"},
        "sector": {"type": "number"}
      }
    },
    "benchmarks": {
      "type": "object",
      "required": ["IN", "US"],
      "properties": {"IN": {"type": "string"}, "US": {"type": "string"}}
    }
  }
}
```

- [ ] **Step 4: Create `schemas/tax-rules.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["rules"],
  "properties": {
    "rules": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "match", "stcg", "ltcg"],
        "properties": {
          "id": {"type": "string"},
          "match": {
            "type": "object",
            "required": ["market", "instrument", "residency"],
            "properties": {
              "market": {"enum": ["IN", "US"]},
              "instrument": {"enum": ["equity", "equity_mf", "debt_mf"]},
              "residency": {"enum": ["IN", "US"]}
            }
          },
          "stcg": {
            "type": "object",
            "required": ["hold_lt_days", "rate"],
            "properties": {
              "hold_lt_days": {"type": "integer"},
              "rate": {}
            }
          },
          "ltcg": {
            "type": "object",
            "required": ["hold_gte_days", "rate"],
            "properties": {
              "hold_gte_days": {"type": "integer"},
              "rate": {},
              "exemption_inr": {"type": "number"}
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 5: Create `schemas/universe.schema.json` and `schemas/holdings.schema.json`**

```json
// schemas/universe.schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["market", "tickers"],
  "properties": {
    "market": {"enum": ["IN", "US"]},
    "tickers": {"type": "array", "items": {"type": "string"}},
    "watchlist": {"type": "array", "items": {"type": "string"}}
  }
}
```

```json
// schemas/holdings.schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["as_of", "fx", "lots"],
  "properties": {
    "as_of": {"type": "string", "format": "date"},
    "fx": {
      "type": "object",
      "required": ["USDINR"],
      "properties": {"USDINR": {"type": "number"}}
    },
    "lots": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["account", "symbol", "market", "instrument", "qty", "entry_date"],
        "properties": {
          "account": {"type": "string"},
          "symbol": {"type": "string"},
          "market": {"enum": ["IN", "US"]},
          "instrument": {"enum": ["equity", "equity_mf", "debt_mf"]},
          "qty": {"type": "number"},
          "avg_cost_inr": {"type": "number"},
          "avg_cost_usd": {"type": "number"},
          "entry_date": {"type": "string", "format": "date"},
          "cost_basis_inr": {"type": "number"},
          "cost_basis_usd": {"type": "number"}
        }
      }
    }
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add schemas/
git commit -m "feat: add JSON schemas for state files"
```

---

## Task 3: State file templates

**Files:**
- Create: `portfolio/ips.md.template`
- Create: `portfolio/targets.yaml.template`
- Create: `portfolio/constraints.yaml.template`
- Create: `portfolio/universe-in.yaml.template`
- Create: `portfolio/universe-us.yaml.template`
- Create: `portfolio/tax-rules.yaml.template`
- Create: `portfolio/accounts.yaml.template`

- [ ] **Step 1: IPS template (`portfolio/ips.md.template`)**

```markdown
# Investment Policy Statement

## Objectives
- [ ] Primary goal (e.g., long-term wealth compounding)
- [ ] Target nominal return / horizon
- [ ] Required liquidity buffer

## Risk tolerance
- Drawdown comfort: e.g., 25% peak-to-trough acceptable
- Volatility comfort: low / medium / high

## Strategy
- Rebalance band drift triggers monthly review
- Momentum rotation within bands on a monthly cadence
- Minimum hold: 30 days per lot
- No options, futures, F&O, intraday

## Constraints
- Tax residency: IN
- No individual stock > 8% of total portfolio
- Sector exposure cap: 30%

## Review cadence
- Monthly rotation review
- Quarterly IPS revisit
- Annual universe refresh (Nifty 50 and Nasdaq 100 reconstitutions)
```

- [ ] **Step 2: `portfolio/targets.yaml.template`**

```yaml
asset_class_bands:
  equity_in:   {target: 0.50, min: 0.40, max: 0.60}
  equity_us:   {target: 0.30, min: 0.20, max: 0.40}
  mf_in:       {target: 0.15, min: 0.10, max: 0.25}
  cash:        {target: 0.05, min: 0.00, max: 0.15}
per_market_caps:
  equity_in_single_stock: 0.08
  equity_us_single_stock: 0.08
  sector_cap: 0.30
```

- [ ] **Step 3: `portfolio/constraints.yaml.template`**

```yaml
min_hold_days: 30
turnover_cap_monthly: 0.30
concentration_caps:
  single_issuer: 0.08
  sector: 0.30
benchmarks:
  IN: "^NSEI"
  US: "^NDX"
```

- [ ] **Step 4: `portfolio/tax-rules.yaml.template`**

```yaml
rules:
  - id: in_listed_equity
    match: {market: IN, instrument: equity, residency: IN}
    stcg: {hold_lt_days: 365, rate: 0.20}
    ltcg: {hold_gte_days: 365, rate: 0.125, exemption_inr: 125000}
  - id: in_equity_mf
    match: {market: IN, instrument: equity_mf, residency: IN}
    stcg: {hold_lt_days: 365, rate: 0.20}
    ltcg: {hold_gte_days: 365, rate: 0.125, exemption_inr: 125000}
  - id: in_debt_mf
    match: {market: IN, instrument: debt_mf, residency: IN}
    stcg: {hold_lt_days: 99999, rate: "slab"}
    ltcg: {hold_gte_days: 99999, rate: "slab"}
  - id: us_equity_for_in_resident
    match: {market: US, instrument: equity, residency: IN}
    stcg: {hold_lt_days: 730, rate: "slab"}
    ltcg: {hold_gte_days: 730, rate: 0.125}
```

- [ ] **Step 5: `portfolio/accounts.yaml.template`**

```yaml
accounts:
  - id: kite-eq
    broker: zerodha_kite
    market: IN
    currency: INR
    source: csv
    residency: IN
  - id: coin-mf
    broker: zerodha_coin
    market: IN
    currency: INR
    source: csv
    residency: IN
  - id: indmoney-us
    broker: indmoney_alpaca
    market: US
    currency: USD
    source: csv
    residency: IN
```

- [ ] **Step 6: Universe templates**

```yaml
# portfolio/universe-in.yaml.template
market: IN
tickers:
  # Nifty 50 — refresh on NSE reconstitution dates
  - RELIANCE.NS
  - TCS.NS
  - HDFCBANK.NS
  - INFY.NS
  - ICICIBANK.NS
  # ... (populate with current Nifty 50 constituents at install time)
watchlist: []
```

```yaml
# portfolio/universe-us.yaml.template
market: US
tickers:
  # Nasdaq 100 — refresh on Nasdaq reconstitution dates
  - AAPL
  - MSFT
  - NVDA
  - GOOGL
  - AMZN
  # ... (populate with current Nasdaq 100 constituents at install time)
watchlist: []
```

- [ ] **Step 7: Commit**

```bash
git add portfolio/
git commit -m "feat: add portfolio state file templates"
```

---

## Task 4: FIFO lot builder utility (TDD)

**Files:**
- Create: `utils/fifo.py`
- Create: `tests/test_fifo.py`
- Create: `requirements.txt`

- [ ] **Step 1: Create `requirements.txt`**

```text
pytest==8.0.0
pyyaml==6.0.1
yfinance==0.2.38
pandas==2.2.0
jsonschema==4.21.0
```

Install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

- [ ] **Step 2: Write failing test (`tests/test_fifo.py`)**

```python
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
```

- [ ] **Step 3: Run test, confirm fail**

```bash
pytest tests/test_fifo.py -v
```
Expected: `ModuleNotFoundError: No module named 'utils.fifo'`.

- [ ] **Step 4: Implement `utils/fifo.py`**

```python
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
```

- [ ] **Step 5: Run tests, confirm pass**

```bash
pytest tests/test_fifo.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add utils/fifo.py tests/test_fifo.py requirements.txt
git commit -m "feat(utils): FIFO lot builder with tests"
```

---

## Task 5: Tax rule matcher utility (TDD)

**Files:**
- Create: `utils/tax.py`
- Create: `tests/test_tax.py`
- Create: `tests/fixtures/tax-rules.yaml`

- [ ] **Step 1: Fixture file `tests/fixtures/tax-rules.yaml`** (copy of the template, frozen for tests)

```yaml
rules:
  - id: in_listed_equity
    match: {market: IN, instrument: equity, residency: IN}
    stcg: {hold_lt_days: 365, rate: 0.20}
    ltcg: {hold_gte_days: 365, rate: 0.125, exemption_inr: 125000}
  - id: us_equity_for_in_resident
    match: {market: US, instrument: equity, residency: IN}
    stcg: {hold_lt_days: 730, rate: "slab"}
    ltcg: {hold_gte_days: 730, rate: 0.125}
```

- [ ] **Step 2: Write failing tests (`tests/test_tax.py`)**

```python
import pytest
from datetime import date
from utils.tax import classify, load_rules, NoMatchingRule


@pytest.fixture
def rules():
    return load_rules("tests/fixtures/tax-rules.yaml")


def test_in_equity_short_term(rules):
    r = classify(
        market="IN", instrument="equity", residency="IN",
        entry_date=date(2025, 10, 1), sell_date=date(2026, 4, 1),
        rules=rules,
    )
    assert r.classification == "STCG"
    assert r.rate == 0.20
    assert r.days_to_ltcg == 365 - (date(2026, 4, 1) - date(2025, 10, 1)).days


def test_in_equity_long_term(rules):
    r = classify(
        market="IN", instrument="equity", residency="IN",
        entry_date=date(2024, 1, 1), sell_date=date(2026, 2, 1),
        rules=rules,
    )
    assert r.classification == "LTCG"
    assert r.rate == 0.125
    assert r.exemption_inr == 125000


def test_us_equity_for_in_resident_needs_24_months(rules):
    # 18 months — still STCG under Indian unlisted-foreign-equity treatment
    r = classify(
        market="US", instrument="equity", residency="IN",
        entry_date=date(2024, 10, 1), sell_date=date(2026, 4, 1),
        rules=rules,
    )
    assert r.classification == "STCG"
    assert r.rate == "slab"

    # 25 months — LTCG
    r2 = classify(
        market="US", instrument="equity", residency="IN",
        entry_date=date(2023, 12, 1), sell_date=date(2026, 1, 1),
        rules=rules,
    )
    assert r2.classification == "LTCG"
    assert r2.rate == 0.125


def test_no_matching_rule_fails_loudly(rules):
    with pytest.raises(NoMatchingRule):
        classify(
            market="US", instrument="equity", residency="US",
            entry_date=date(2024, 1, 1), sell_date=date(2026, 4, 1),
            rules=rules,
        )
```

- [ ] **Step 3: Run, confirm fail.**

```bash
pytest tests/test_tax.py -v
```

- [ ] **Step 4: Implement `utils/tax.py`**

```python
"""Jurisdiction-aware tax classifier. Rules are data; no hardcoded brackets."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Union
import yaml


class NoMatchingRule(Exception):
    pass


@dataclass
class Classification:
    classification: str             # "STCG" | "LTCG"
    rate: Union[float, str]         # numeric or "slab"
    days_held: int
    days_to_ltcg: int               # 0 if already LTCG
    exemption_inr: Optional[float]
    rule_id: str


def load_rules(path: str) -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)["rules"]


def _match(rule: dict, market: str, instrument: str, residency: str) -> bool:
    m = rule["match"]
    return m["market"] == market and m["instrument"] == instrument and m["residency"] == residency


def classify(market: str, instrument: str, residency: str,
             entry_date: date, sell_date: date,
             rules: List[dict]) -> Classification:
    rule = next((r for r in rules if _match(r, market, instrument, residency)), None)
    if rule is None:
        raise NoMatchingRule(f"no rule for market={market} instrument={instrument} residency={residency}")

    days_held = (sell_date - entry_date).days
    ltcg_boundary = rule["ltcg"]["hold_gte_days"]

    if days_held >= ltcg_boundary:
        return Classification(
            classification="LTCG",
            rate=rule["ltcg"]["rate"],
            days_held=days_held,
            days_to_ltcg=0,
            exemption_inr=rule["ltcg"].get("exemption_inr"),
            rule_id=rule["id"],
        )
    return Classification(
        classification="STCG",
        rate=rule["stcg"]["rate"],
        days_held=days_held,
        days_to_ltcg=ltcg_boundary - days_held,
        exemption_inr=None,
        rule_id=rule["id"],
    )
```

- [ ] **Step 5: Run, confirm pass.**

```bash
pytest tests/test_tax.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add utils/tax.py tests/test_tax.py tests/fixtures/
git commit -m "feat(utils): jurisdiction-aware tax classifier with tests"
```

---

## Task 6: Momentum scorer utility (TDD)

**Files:**
- Create: `utils/momentum.py`
- Create: `tests/test_momentum.py`

- [ ] **Step 1: Write failing tests (`tests/test_momentum.py`)**

```python
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
```

- [ ] **Step 2: Run, confirm fail.**

- [ ] **Step 3: Implement `utils/momentum.py`**

```python
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
    above_200 = prices.iloc[-1] > prices.iloc[-200:].mean()
    composite = (m3 + m6 + m12) / 3.0   # equal-weighted by default

    return MomentumScore(
        ticker=ticker,
        m3=m3, m6=m6, m12=m12,
        rs_vs_bench=rs,
        above_200dma=above_200,
        composite=composite,
    )
```

- [ ] **Step 4: Run, confirm pass.**

- [ ] **Step 5: Commit**

```bash
git add utils/momentum.py tests/test_momentum.py
git commit -m "feat(utils): momentum scorer with tests"
```

---

## Task 7: CSV parsers (Kite, Coin, IndMoney) — TDD

**Files:**
- Create: `utils/csv_parsers.py`
- Create: `tests/test_csv_parsers.py`
- Create: `tests/fixtures/kite-tradebook.csv`
- Create: `tests/fixtures/indmoney-trades.csv`

- [ ] **Step 1: Create fixture CSVs**

`tests/fixtures/kite-tradebook.csv`:
```csv
symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time
RELIANCE,INE002A01018,2025-01-10,NSE,EQ,EQ,buy,false,10,2400.00,TR1,OR1,2025-01-10T10:15:30
RELIANCE,INE002A01018,2025-03-10,NSE,EQ,EQ,sell,false,4,2600.00,TR2,OR2,2025-03-10T11:30:15
TCS,INE467B01029,2025-02-01,NSE,EQ,EQ,buy,false,5,3500.00,TR3,OR3,2025-02-01T09:45:10
```

`tests/fixtures/indmoney-trades.csv`:
```csv
Date,Symbol,Action,Quantity,Price (USD),Total (USD)
2024-09-03,NVDA,BUY,10,785.00,7850.00
2025-01-15,AAPL,BUY,5,225.00,1125.00
```

- [ ] **Step 2: Write failing tests (`tests/test_csv_parsers.py`)**

```python
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
```

- [ ] **Step 3: Run, confirm fail.**

- [ ] **Step 4: Implement `utils/csv_parsers.py`**

```python
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
```

- [ ] **Step 5: Run, confirm pass.**

- [ ] **Step 6: Commit**

```bash
git add utils/csv_parsers.py tests/test_csv_parsers.py tests/fixtures/
git commit -m "feat(utils): CSV parsers for Kite + IndMoney with tests"
```

---

## Task 8: State loader (schema validator + PortfolioSnapshot)

**Files:**
- Create: `utils/state.py`
- Create: `tests/test_state.py`
- Create: `tests/fixtures/portfolio/` (minimal valid state set)

- [ ] **Step 1: Create test fixture state files**

Copy every `portfolio/*.yaml.template` into `tests/fixtures/portfolio/` (renamed to drop `.template`). Add a minimal `holdings.yaml`:

```yaml
# tests/fixtures/portfolio/holdings.yaml
as_of: 2026-04-20
fx:
  USDINR: 83.42
lots:
  - account: kite-eq
    symbol: RELIANCE.NS
    market: IN
    instrument: equity
    qty: 10
    avg_cost_inr: 2400.00
    entry_date: 2025-01-10
    cost_basis_inr: 24000.00
  - account: indmoney-us
    symbol: NVDA
    market: US
    instrument: equity
    qty: 10
    avg_cost_usd: 785.00
    entry_date: 2024-09-03
    cost_basis_usd: 7850.00
```

- [ ] **Step 2: Write failing tests (`tests/test_state.py`)**

```python
from utils.state import load_snapshot, ValidationError
import pytest


def test_loads_valid_state():
    snap = load_snapshot("tests/fixtures/portfolio")
    assert len(snap.accounts) == 3
    assert len(snap.lots) == 2
    assert snap.fx_usdinr == 83.42
    assert {l.symbol for l in snap.lots} == {"RELIANCE.NS", "NVDA"}


def test_fails_loudly_on_missing_entry_date(tmp_path, monkeypatch):
    # copy fixture dir and mutate holdings.yaml to drop entry_date on one lot
    import shutil
    shutil.copytree("tests/fixtures/portfolio", tmp_path / "p")
    bad = (tmp_path / "p" / "holdings.yaml").read_text().replace("entry_date: 2025-01-10\n", "")
    (tmp_path / "p" / "holdings.yaml").write_text(bad)
    with pytest.raises(ValidationError):
        load_snapshot(str(tmp_path / "p"))
```

- [ ] **Step 3: Run, confirm fail.**

- [ ] **Step 4: Implement `utils/state.py`**

```python
"""State loader: validates + assembles a PortfolioSnapshot from the portfolio/ folder."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import yaml
from jsonschema import validate, ValidationError as JSONSchemaError


class ValidationError(Exception):
    pass


@dataclass
class Account:
    id: str
    broker: str
    market: str
    currency: str
    source: str
    residency: str


@dataclass
class HoldingLot:
    """Persisted lot in holdings.yaml — richer than utils.fifo.Lot (adds account/market/instrument)."""
    account: str
    symbol: str
    market: str
    instrument: str
    qty: float
    entry_date: str
    avg_cost_inr: float | None = None
    avg_cost_usd: float | None = None
    cost_basis_inr: float | None = None
    cost_basis_usd: float | None = None


@dataclass
class PortfolioSnapshot:
    as_of: str
    fx_usdinr: float
    accounts: list[Account] = field(default_factory=list)
    lots: list[Lot] = field(default_factory=list)
    targets: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    tax_rules: list = field(default_factory=list)
    universes: dict[str, dict] = field(default_factory=dict)


def _load_yaml(path: Path) -> Any:
    with open(path) as f:
        return yaml.safe_load(f)


def _validate(data: Any, schema_path: Path) -> None:
    with open(schema_path) as f:
        schema = json.load(f)
    try:
        validate(data, schema)
    except JSONSchemaError as e:
        raise ValidationError(f"{schema_path.name}: {e.message}") from e


def load_snapshot(portfolio_dir: str) -> PortfolioSnapshot:
    p = Path(portfolio_dir)
    schemas = Path(__file__).parent.parent / "schemas"

    accounts_raw = _load_yaml(p / "accounts.yaml")
    _validate(accounts_raw, schemas / "accounts.schema.json")

    targets = _load_yaml(p / "targets.yaml")
    _validate(targets, schemas / "targets.schema.json")

    constraints = _load_yaml(p / "constraints.yaml")
    _validate(constraints, schemas / "constraints.schema.json")

    tax_rules_raw = _load_yaml(p / "tax-rules.yaml")
    _validate(tax_rules_raw, schemas / "tax-rules.schema.json")

    holdings_raw = _load_yaml(p / "holdings.yaml")
    _validate(holdings_raw, schemas / "holdings.schema.json")

    universes: dict[str, dict] = {}
    for m, fname in (("IN", "universe-in.yaml"), ("US", "universe-us.yaml")):
        u = _load_yaml(p / fname)
        _validate(u, schemas / "universe.schema.json")
        universes[m] = u

    accounts = [Account(**a) for a in accounts_raw["accounts"]]
    lots = [HoldingLot(**l) for l in holdings_raw["lots"]]

    return PortfolioSnapshot(
        as_of=holdings_raw["as_of"],
        fx_usdinr=holdings_raw["fx"]["USDINR"],
        accounts=accounts,
        lots=lots,
        targets=targets,
        constraints=constraints,
        tax_rules=tax_rules_raw["rules"],
        universes=universes,
    )
```

- [ ] **Step 5: Run, confirm pass.**

- [ ] **Step 6: Commit**

```bash
git add utils/state.py tests/test_state.py tests/fixtures/portfolio/
git commit -m "feat(utils): state loader with JSON schema validation"
```

---

## Task 9: Market-data MCP (yfinance-backed, minimal)

**Files:**
- Create: `mcps/market_data/server.py`
- Create: `mcps/market_data/requirements.txt`
- Modify: `.mcp.json`

Rationale: before writing custom code, check for a community yfinance MCP. If one exists that covers `.NS` and Nasdaq tickers, use it. Only write this if nothing suitable exists.

- [ ] **Step 1: Reconnaissance — 15 minutes**

Search for existing MCPs. Candidates to evaluate:
```bash
# In Cowork, use mcp-registry search (if plan executor doesn't have it, skip and build)
```
If a suitable one is found, skip to Step 5 and add its registration instead. Otherwise:

- [ ] **Step 2: Create `mcps/market_data/server.py` (FastMCP-based, ~80 LOC)**

```python
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
```

- [ ] **Step 3: Create `mcps/market_data/requirements.txt`**

```text
mcp==1.0.0
yfinance==0.2.38
```

- [ ] **Step 4: Smoke-test the server manually**

```bash
cd mcps/market_data
pip install -r requirements.txt
python server.py &
# issue a basic MCP handshake via the mcp CLI if available; otherwise proceed to registration
```

- [ ] **Step 5: Register in `.mcp.json`**

Add to existing `.mcp.json`:
```json
{
  "mcpServers": {
    "kite": {
      "type": "sse",
      "url": "https://mcp.kite.trade/mcp"
    },
    "market-data": {
      "command": "python",
      "args": ["mcps/market_data/server.py"]
    }
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add mcps/ .mcp.json
git commit -m "feat(mcp): thin yfinance market-data MCP + Kite registration"
```

---

## Task 10: AMFI NAV fetch helper

**Files:**
- Create: `utils/amfi_nav.py`
- Create: `tests/test_amfi_nav.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_amfi_nav.py
from utils.amfi_nav import parse_amfi_nav_file


def test_parse_amfi_nav_snippet(tmp_path):
    # AMFI daily NAV file format (subset):
    content = """Open Ended Schemes(Equity Scheme - Large Cap Fund)
;;;;;
Axis Mutual Fund
;;;;;
Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
120505;INF846K01EW2;;Axis Bluechip Fund - Direct Plan - Growth;67.1234;19-Apr-2026
"""
    f = tmp_path / "nav.txt"
    f.write_text(content)
    navs = parse_amfi_nav_file(str(f))
    assert "INF846K01EW2" in navs
    assert navs["INF846K01EW2"]["nav"] == 67.1234
    assert navs["INF846K01EW2"]["scheme_name"].startswith("Axis Bluechip")
```

- [ ] **Step 2: Run, confirm fail. Implement `utils/amfi_nav.py`**

```python
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
```

- [ ] **Step 3: Run, confirm pass. Commit.**

```bash
git add utils/amfi_nav.py tests/test_amfi_nav.py
git commit -m "feat(utils): AMFI NAV parser"
```

---

## Task 11: `market-analyst` subagent definition

**Files:**
- Create: `agents/market-analyst.md`

- [ ] **Step 1: Write the agent definition**

```markdown
---
name: market-analyst
description: Use when a skill needs quotes, fundamentals, or news for one or more tickers. Handles both IN (.NS suffixed) and US tickers. Returns a structured digest.
tools: mcp__market-data__quote, mcp__market-data__history, mcp__market-data__fundamentals, WebSearch
---

You are a market-data analyst subagent. Your job: fetch and synthesize data for the tickers you're given. Do not opine on trading decisions. Return structured facts.

## Input
The invoking skill passes a JSON blob:
```json
{"tickers": ["RELIANCE.NS", "NVDA"], "need": ["quotes", "fundamentals", "news"]}
```

## Steps
1. For each ticker in `tickers`:
   - If `"quotes"` in `need`: call `mcp__market-data__quote`.
   - If `"fundamentals"` in `need`: call `mcp__market-data__fundamentals`.
   - If `"news"` in `need`: call `WebSearch` with query `<ticker company name> earnings OR news site:reuters.com OR site:bloomberg.com`. Cap at 3 headlines per ticker.
2. Assemble a structured digest.

## Output contract
```json
{
  "RELIANCE.NS": {
    "quote": {...},
    "fundamentals": {...},
    "news": [{"title": "...", "source": "...", "url": "..."}]
  }
}
```

## Rules
- Never invent numbers. Every field must trace back to a tool call. If a call fails, return `null` for that field and add `"error"`.
- Do not write to any state file.
- Do not call more than 1 web search per ticker.
```

- [ ] **Step 2: Commit**

```bash
git add agents/market-analyst.md
git commit -m "feat(agents): market-analyst subagent"
```

---

## Task 12: `momentum-screener` subagent definition

**Files:**
- Create: `agents/momentum-screener.md`

- [ ] **Step 1: Write the agent definition**

```markdown
---
name: momentum-screener
description: Use when a skill needs a ranked momentum table for a universe of tickers. Runs per market (IN or US). Uses the momentum utility for scoring.
tools: mcp__market-data__history, Bash
---

You are a momentum screener. Your job: rank a universe of tickers by composite momentum.

## Input
```json
{"market": "IN", "tickers": ["RELIANCE.NS", "TCS.NS", ...], "benchmark": "^NSEI"}
```

## Steps
1. For each ticker in `tickers` (batch in parallel tool calls where possible):
   - Call `mcp__market-data__history(symbol=ticker, period="2y")`.
2. Call `mcp__market-data__history(symbol=benchmark, period="2y")`.
3. For each ticker with ≥260 business days of data, compute momentum by invoking the shared utility:

```bash
python -c "
import json, sys, pandas as pd
from utils.momentum import compute_momentum
data = json.load(sys.stdin)
# data = {'ticker', 'prices': [...], 'bench': [...]}
prices = pd.Series([p['close'] for p in data['prices']], index=pd.to_datetime([p['date'] for p in data['prices']]))
bench  = pd.Series([p['close'] for p in data['bench']],  index=pd.to_datetime([p['date'] for p in data['bench']]))
s = compute_momentum(data['ticker'], prices, bench)
print(json.dumps({'ticker': s.ticker, 'm3': s.m3, 'm6': s.m6, 'm12': s.m12, 'rs': s.rs_vs_bench, 'above_200dma': s.above_200dma, 'composite': s.composite}))
"
```

4. Sort descending by `composite`.

## Output contract
```json
{
  "market": "IN",
  "as_of": "2026-04-19",
  "ranked": [
    {"ticker": "...", "composite": 0.23, "m3": 0.08, "m6": 0.14, "m12": 0.21, "rs_vs_bench": 0.09, "above_200dma": true, "rank": 1},
    ...
  ],
  "skipped": [{"ticker": "...", "reason": "insufficient history"}]
}
```

## Rules
- Never hallucinate momentum values. Every `composite` must come from the utility.
- Tickers with insufficient history go in `skipped`, never in `ranked`.
```

- [ ] **Step 2: Commit**

```bash
git add agents/momentum-screener.md
git commit -m "feat(agents): momentum-screener subagent"
```

---

## Task 13: `risk-reviewer` subagent definition

**Files:**
- Create: `agents/risk-reviewer.md`

- [ ] **Step 1: Write the definition**

```markdown
---
name: risk-reviewer
description: Use when a skill needs to validate a proposed allocation or trade set against IPS constraints (concentration, sector, per-market caps, turnover).
tools: Read
---

You are a risk reviewer. Your job: take a proposed set of allocation changes and check them against `portfolio/targets.yaml` and `portfolio/constraints.yaml`. Return pass/warn/fail.

## Input
```json
{
  "current_weights": {"RELIANCE.NS": 0.09, "NVDA": 0.05, ...},
  "proposed_changes": [{"symbol": "RELIANCE.NS", "delta_weight": -0.03}, ...],
  "sectors": {"RELIANCE.NS": "Energy", "NVDA": "Technology", ...}
}
```

## Steps
1. Read `portfolio/targets.yaml` and `portfolio/constraints.yaml`.
2. Compute post-change weights.
3. Run checks:
   - **single_issuer**: no symbol > `concentration_caps.single_issuer`.
   - **sector**: no sector > `concentration_caps.sector`.
   - **per_market_caps**: weights of IN stocks + weights of US stocks individually respect caps.
   - **turnover**: sum of |delta_weight| / 2 <= `turnover_cap_monthly`.
4. For each breach, emit a finding with severity: `fail` if breach, `warn` if within 10% of cap.

## Output contract
```json
{
  "status": "pass" | "warn" | "fail",
  "findings": [
    {"rule": "single_issuer", "severity": "fail", "detail": "RELIANCE.NS at 0.11 exceeds cap 0.08"}
  ]
}
```

## Rules
- Do not modify any file.
- If required inputs are missing, emit a `fail` finding citing what's missing — do not silently pass.
```

- [ ] **Step 2: Commit**

```bash
git add agents/risk-reviewer.md
git commit -m "feat(agents): risk-reviewer subagent"
```

---

## Task 14: `tax-optimizer` subagent definition

**Files:**
- Create: `agents/tax-optimizer.md`

- [ ] **Step 1: Write the definition**

```markdown
---
name: tax-optimizer
description: Use when a skill has proposed sells. Classifies STCG vs LTCG per lot, flags LTCG-boundary proximity, and suggests lot selection.
tools: Bash, Read
---

You are a tax optimizer. Your job: for each proposed sell, use the shared rule-matcher utility to classify and flag.

## Input
```json
{
  "proposed_sells": [
    {"account": "indmoney-us", "symbol": "NVDA", "qty": 5, "sell_date": "2026-04-20"}
  ],
  "lots": [
    {"account": "indmoney-us", "symbol": "NVDA", "qty": 10, "entry_date": "2024-09-03", "avg_cost_usd": 785}
  ],
  "approaching_ltcg_window_days": 60
}
```

## Steps
1. Read `portfolio/accounts.yaml` to map each account → {market, instrument, residency}.
2. For each proposed sell, select the candidate lot(s) via FIFO from `lots`.
3. For each candidate lot, call the classifier:

```bash
python -c "
from datetime import date
from utils.tax import classify, load_rules
r = classify(market='US', instrument='equity', residency='IN',
             entry_date=date(2024,9,3), sell_date=date(2026,4,20),
             rules=load_rules('portfolio/tax-rules.yaml'))
print(r)
"
```

4. Flag lots where `days_to_ltcg <= approaching_ltcg_window_days` (LTCG-deferral candidate).
5. Check `min_hold_days` from `constraints.yaml` against `days_held`; violations become `min_hold_breach`.

## Output contract
```json
{
  "per_sell": [
    {
      "symbol": "NVDA",
      "classification": "STCG",
      "rate": "slab",
      "days_held": 594,
      "days_to_ltcg": 136,
      "flags": ["approaching_ltcg"],
      "lot_advice": "defer sell 136 days to qualify as LTCG at 12.5%"
    }
  ]
}
```

## Rules
- Never hardcode tax brackets. Always go through `utils.tax.classify`.
- If no rule matches, surface the `NoMatchingRule` error — do not swallow it.
```

- [ ] **Step 2: Commit**

```bash
git add agents/tax-optimizer.md
git commit -m "feat(agents): tax-optimizer subagent"
```

---

## Task 15: `doc-writer` subagent definition

**Files:**
- Create: `agents/doc-writer.md`

- [ ] **Step 1: Write the definition**

```markdown
---
name: doc-writer
description: Use when a skill has a finalized structured payload and wants a polished Word or PDF artifact. Uses the existing docx / pdf skills.
tools: Skill, Write
---

You are a document writer. Your job: convert a structured payload into a well-formatted artifact.

## Input
```json
{"report_type": "portfolio-review" | "rotation-proposal" | "research-memo", "payload": {...}, "format": "docx" | "pdf"}
```

## Steps
1. Invoke the appropriate skill for the target format:
   - `docx` → Skill tool with skill name `docx`
   - `pdf` → Skill tool with skill name `pdf`
2. Follow that skill's instructions to produce the artifact, using the payload as source content.
3. Save to the user-mounted outputs folder with a dated filename: `<report_type>-YYYY-MM-DD.<ext>`.

## Output contract
```json
{"path": "...", "format": "docx"}
```

## Rules
- Do not invent data. Only render what's in `payload`.
- Do not format numerics beyond 2 decimals for percentages and INR/USD figures.
```

- [ ] **Step 2: Commit**

```bash
git add agents/doc-writer.md
git commit -m "feat(agents): doc-writer subagent"
```

---

## Task 16: `portfolio-state` skill

**Files:**
- Create: `skills/portfolio-state/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: portfolio-state
description: Canonical loader — reads the portfolio/ folder and returns a validated PortfolioSnapshot. Called first by every other skill. Use when you need current holdings, IPS, targets, or tax rules for any workflow.
---

# portfolio-state

Load + validate the full portfolio state and enrich with live quotes and FX.

## Steps

1. **Check staleness.** Read `portfolio/holdings.yaml`. If `as_of` is older than 7 days, emit a warning:
   > "holdings.yaml is N days old — run `holdings-import` before relying on this snapshot."

2. **Load and validate** by running the state loader:

```bash
python -c "
import json
from dataclasses import asdict
from utils.state import load_snapshot
s = load_snapshot('portfolio')
print(json.dumps({
  'as_of': s.as_of, 'fx_usdinr': s.fx_usdinr,
  'accounts': [asdict(a) for a in s.accounts],
  'lots': [asdict(l) for l in s.lots],
  'targets': s.targets, 'constraints': s.constraints,
  'universes': s.universes,
}, default=str))
"
```

3. **Fetch live quotes.** For every unique symbol in `lots`, call `mcp__market-data__quote`. Batch where possible.

4. **Fetch FX.** Call `mcp__market-data__fx_usdinr`. If the returned rate differs from `holdings.yaml.fx.USDINR` by >1%, note the drift in the output.

5. **For MF lots (instrument == equity_mf)**, fetch AMFI NAV:
```bash
curl -sSL https://www.amfiindia.com/spages/NAVAll.txt > /tmp/amfi-nav.txt
python -c "
import json
from utils.amfi_nav import parse_amfi_nav_file
print(json.dumps(parse_amfi_nav_file('/tmp/amfi-nav.txt')))
" > /tmp/amfi-nav.json
```
Lookup MF lots by ISIN (stored in `symbol` field for MF).

6. **Compute derived fields:**
   - `market_value_native` = qty × price
   - `market_value_inr` = native * FX (for USD) or native (for INR)
   - `current_weight` = market_value_inr / total
   - `drift_vs_target` per asset class per `targets.yaml`

7. **Validate invariants.** Fail loudly if any lot has no `entry_date`, any symbol has no price, or any account referenced in a lot is not in `accounts.yaml`.

## Output
Return a `PortfolioSnapshot` JSON blob to the caller.

## Rules
- Every number traces to a source: `holdings.yaml`, a tool call, or a rules file.
- Stale holdings (>7 days) produces a warning, not a silent pass.
```

- [ ] **Step 2: Commit**

```bash
git add skills/portfolio-state/
git commit -m "feat(skills): portfolio-state canonical loader"
```

---

## Task 17: `holdings-import` skill

**Files:**
- Create: `skills/holdings-import/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: holdings-import
description: Ingest CSV drops from Kite / Coin / IndMoney under imports/YYYY-MM-DD/, rebuild lots via FIFO, update portfolio/holdings.yaml. Use when the user has dropped new broker exports.
---

# holdings-import

## Prerequisites
User has dropped CSVs into `imports/YYYY-MM-DD/`:
- `kite-tradebook.csv` (required for lot entry dates)
- `kite-holdings.csv` (optional, for reconciliation)
- `coin-holdings.csv` (optional — current Coin MF balance)
- `indmoney-trades.csv` (required)
- `indmoney-holdings.csv` (optional)

If any REQUIRED file is missing, abort and tell the user what's needed.

## Steps

1. **Find the latest import folder:**
```bash
ls -1d imports/*/ | sort -r | head -1
```

2. **Parse each file and build lots per account.** FIFO runs per `(account, symbol)` — do not pool trades across accounts. Invoke:

```bash
python - <<'PY'
import yaml
from datetime import date
from utils.csv_parsers import parse_kite_tradebook, parse_indmoney_trades
from utils.fifo import build_lots

# Each account gets its own trade stream + enrichment metadata.
per_account = [
    {"id": "kite-eq",     "market": "IN", "instrument": "equity", "currency": "INR",
     "trades": parse_kite_tradebook("imports/LATEST/kite-tradebook.csv")},
    {"id": "indmoney-us", "market": "US", "instrument": "equity", "currency": "USD",
     "trades": parse_indmoney_trades("imports/LATEST/indmoney-trades.csv")},
]

all_lots = []
for acc in per_account:
    lots = build_lots(acc["trades"])
    for l in lots:
        lot = {
            "account": acc["id"],
            "symbol": l.symbol,
            "market": acc["market"],
            "instrument": acc["instrument"],
            "qty": l.qty,
            "entry_date": l.entry_date.isoformat(),
        }
        if acc["currency"] == "INR":
            lot["avg_cost_inr"] = l.cost_basis / l.qty
            lot["cost_basis_inr"] = l.cost_basis
        else:
            lot["avg_cost_usd"] = l.cost_basis / l.qty
            lot["cost_basis_usd"] = l.cost_basis
        all_lots.append(lot)

doc = {
    "as_of": str(date.today()),
    "fx": {"USDINR": 0.0},  # filled by portfolio-state at read time
    "lots": all_lots,
}
print(yaml.safe_dump(doc, sort_keys=False))
PY
```

Replace `LATEST` with the actual folder.

3. **USD→INR cost basis enrichment.** For each US-currency lot in the output, fetch the USDINR rate on the lot's `entry_date` via `mcp__market-data__history` (or a fallback spot if historical is unavailable) and populate `avg_cost_inr` and `cost_basis_inr` alongside the USD fields. Indian tax computations require INR basis.

4. **Reconcile** the computed open-lot totals against `kite-holdings.csv` (current qty per symbol). Emit a diff report. If a symbol in `kite-holdings.csv` has no derived lot OR quantities disagree by >0.5%, flag loudly.

5. **Write** the assembled doc to `portfolio/holdings.yaml`.

6. **Emit a diff** vs the prior `holdings.yaml` (if any): new lots, closed lots, quantity changes.

## Upgrade hook: Kite MCP

If `portfolio/accounts.yaml` sets `source: mcp` for any Kite-based account AND the Kite MCP is reachable (`mcp__kite__*` tools present), skip CSV parsing for that account and call the MCP's holdings endpoint instead. Resolve trades/lots from the MCP's position + transaction endpoints. Output contract is identical.

## Rules
- Do not write `holdings.yaml` if any required input is missing.
- Do not write `holdings.yaml` if reconciliation fails — write to `holdings.yaml.proposed` and ask the user to review.
```

- [ ] **Step 2: Commit**

```bash
git add skills/holdings-import/
git commit -m "feat(skills): holdings-import from CSV + MCP upgrade hook"
```

---

## Task 18: `rebalance` skill

**Files:**
- Create: `skills/rebalance/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: rebalance
description: Drift-to-IPS rebalancing at the asset-class / per-market level. Use when the user wants to bring allocations back inside IPS bands. Emits reallocation table and cash-flow plan — does NOT pick individual tickers (that's rotation).
---

# rebalance

## Steps

1. Invoke the `portfolio-state` skill.

2. Compute current weights per asset class (equity_in, equity_us, mf_in, cash) from the snapshot.

3. For each asset class, compute:
   - `drift = current_weight - target`
   - `in_band` = `min <= current_weight <= max`

4. For each out-of-band class, propose reallocation to `target`:
   - Out-of-band high → sell down to `target`
   - Out-of-band low → buy up to `target`
   - Funding logic: prefer cash surplus first; otherwise pro-rata sell from over-weight classes.

5. **Dispatch `risk-reviewer`** subagent with `{current_weights, proposed_changes}` at the asset-class level.

6. **Dispatch `tax-optimizer`** subagent if any asset-class sells would be realized from taxable accounts. Pass only the candidate sell lots identified by FIFO from each overweight class.

7. **Synthesize** a user-facing output:
   - Current vs target allocation table
   - Reallocation plan (amounts in INR, with USD equivalents for US-side moves)
   - Tax flags per proposed sell
   - Risk flags
   - Executable note: "this is asset-class level. Run `rotation` for the per-ticker buys/sells that implement these deltas."

8. **Optional**: dispatch `doc-writer` if user asked for a Word/PDF.

## Output
Conversational summary + structured table + optional artifact path.

## Rules
- `rebalance` never recommends individual tickers. That's `rotation`'s job.
- If `risk-reviewer` returns `fail`, present the finding and stop — do not emit recommendations that violate IPS.
```

- [ ] **Step 2: Commit**

```bash
git add skills/rebalance/
git commit -m "feat(skills): rebalance skill"
```

---

## Task 19: `rotation` skill

**Files:**
- Create: `skills/rotation/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: rotation
description: Per-market momentum-driven rotation — identifies decay candidates (exits) and leaders (entries) within each market while respecting minimum hold and LTCG windows. Use when the user wants to run a monthly rotation review.
---

# rotation

## Steps

1. Invoke `portfolio-state`.

2. For each market (IN, US), build the screening universe:
   - Base = `portfolio/universe-<market>.yaml.tickers`
   - Add any symbols currently held in that market (`snapshot.lots` filtered by market) not already in the base.

3. **Dispatch `momentum-screener` in parallel for both markets** (use the Task tool with two concurrent calls):
   - IN: `{market: "IN", tickers: <IN universe>, benchmark: snapshot.constraints.benchmarks.IN}`
   - US: `{market: "US", tickers: <US universe>, benchmark: snapshot.constraints.benchmarks.US}`

4. For each market, compute:
   - **Decay candidates**: currently-held symbols whose rank falls outside the top quartile of ranked universe
   - **Entry candidates**: top-quartile symbols not currently held

5. **Filter decay candidates against `constraints.min_hold_days`**:
   - For each candidate, check each lot's `entry_date` vs today. If the oldest lot is newer than `min_hold_days`, drop the candidate with reason "min_hold_breach".

6. **Dispatch `tax-optimizer`** with the filtered decay candidates:
   - `{proposed_sells: [...], lots: [...], approaching_ltcg_window_days: 60}`
   - Any lot with `days_to_ltcg <= 60` gets an "LTCG-defer" note surfaced to the user.

7. **Dispatch `risk-reviewer`** with the proposed change set (decay sells + entry buys):
   - If `fail`, trim the candidate set (by dropping lowest-conviction additions) until it passes, or surface the breach and stop.

8. **Synthesize** per-market rotation tables:
   - Exits: symbol, lots, proceeds (native + INR), tax flag
   - Entries: symbol, proposed weight, composite rank, INR notional
   - Net cash needed per market
   - Summary: turnover % of portfolio, risk/tax flags

9. Optional `doc-writer`.

## Rules
- Minimum hold is a hard constraint. Never recommend a sell within `min_hold_days`.
- A proposed rotation that fails risk-reviewer is either trimmed or surfaced — never quietly emitted.
- Always return per-market tables; never cross-rank IN vs US.
```

- [ ] **Step 2: Commit**

```bash
git add skills/rotation/
git commit -m "feat(skills): rotation skill with parallel screening"
```

---

## Task 20: `portfolio-review` skill

**Files:**
- Create: `skills/portfolio-review/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: portfolio-review
description: Periodic check-in: performance vs benchmarks, drift, concentration breakdown, top-holdings news digest. Use for weekly/monthly reviews.
---

# portfolio-review

## Steps

1. Invoke `portfolio-state`.
2. Compute performance:
   - Since inception (if `holdings.yaml` has history), 1M, 3M, YTD
   - Benchmark comparison per market (^NSEI for IN, ^NDX for US)
3. Drift snapshot per asset class.
4. Concentration: top 10 holdings by weight, sector breakdown.
5. Dispatch `market-analyst` for top-5 holdings per market with `need: ["news"]`.
6. Synthesize a digest.
7. If user asked for a doc, dispatch `doc-writer` with `report_type: "portfolio-review"`.

## Output
Conversational summary + structured tables + optional artifact.

## Rules
- Never quote a return figure that wasn't computed from actual price data + holdings in this run.
- If benchmark history is unavailable, say so — do not skip silently.
```

- [ ] **Step 2: Commit**

```bash
git add skills/portfolio-review/
git commit -m "feat(skills): portfolio-review skill"
```

---

## Task 21: `research-memo` skill

**Files:**
- Create: `skills/research-memo/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: research-memo
description: On-demand deep-dive on a single ticker. Use when the user asks to "research NVDA" or similar.
---

# research-memo

## Steps
1. Validate the ticker: it should be in `universe-in.yaml` or `universe-us.yaml`, or the user must confirm an off-universe override.
2. Dispatch `market-analyst` with `need: ["quotes", "fundamentals", "news"]`.
3. Dispatch `momentum-screener` with a single-ticker list and the appropriate benchmark.
4. Compose a memo:
   - Thesis paragraph (grounded in fundamentals + momentum snapshot)
   - Valuation & fundamentals table
   - Momentum table
   - News summary
   - Fit-for-IPS: concentration/sector check, would this breach any caps if added at a default 2% weight?
5. Optional `doc-writer`.

## Rules
- Do not recommend buy/sell in isolation — surface the data and a fit-check, leave the decision explicit to the user.
```

- [ ] **Step 2: Commit**

```bash
git add skills/research-memo/
git commit -m "feat(skills): research-memo skill"
```

---

## Task 22: `financial-plan` skill

**Files:**
- Create: `skills/financial-plan/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: financial-plan
description: Author or update the personal IPS, asset-class targets, and constraints. Use on first run or when the user wants to revisit strategy.
---

# financial-plan

## Steps

1. If any of `portfolio/ips.md`, `targets.yaml`, `constraints.yaml` are missing, copy from their `.template` siblings and proceed with a new-IPS flow.
2. Otherwise, read current versions and proceed with an update flow.
3. **Interactive elicitation** — ask the user (one concern at a time):
   - Objective + horizon
   - Risk tolerance (drawdown, volatility)
   - Per-market allocation target + bands
   - Single-issuer and sector caps
   - Minimum hold + turnover cap
   - Benchmarks (default ^NSEI / ^NDX)
4. **Consistency check:** asset-class `min` ≤ `target` ≤ `max`; sum of `target`s ≈ 1.0 (warn if not 0.95–1.05); caps are plausible (single-issuer 5-15%, sector 20-40%).
5. Write updated files. Run the state loader as a final validation; if it fails, roll back and show the error.
6. Summarize changes for the user.

## Rules
- Never edit state files without showing the user the proposed diff first.
- Tax-rules.yaml is not touched here — it's jurisdiction law, not user preference.
```

- [ ] **Step 2: Commit**

```bash
git add skills/financial-plan/
git commit -m "feat(skills): financial-plan IPS authoring skill"
```

---

## Task 23: Install + smoke test

**Files:**
- Modify: `README.md` (add smoke-test section)
- Create: `tests/smoke/README.md`

- [ ] **Step 1: Seed test portfolio state**

```bash
cd ~/PycharmProjects/portfolio-management
for f in portfolio/*.template; do cp "$f" "${f%.template}"; done
# Now user edits portfolio/ips.md, portfolio/universe-in.yaml, portfolio/universe-us.yaml
# with their actual Nifty 50 / Nasdaq 100 constituents and personal IPS.
```

- [ ] **Step 2: Seed example imports**

Drop a real or fixture CSV into `imports/2026-04-20/`. Minimum: `kite-tradebook.csv` and `indmoney-trades.csv`.

- [ ] **Step 3: Install plugin in Cowork**

In the Cowork UI: Plugins → Install from folder → select `~/PycharmProjects/portfolio-management`.

Verify:
- The 7 skills appear in the skill list.
- The 5 subagents are available via the Task tool.
- `mcp__kite__*` and `mcp__market-data__*` tools are present in a fresh session.

- [ ] **Step 4: Smoke-test each skill, one at a time**

In order:
1. `/financial-plan` — create an IPS. Verify files written, state loader passes.
2. `/holdings-import` — ingest the seeded CSVs. Verify `portfolio/holdings.yaml` is produced and reconciliation diff is sensible.
3. `/portfolio-state` — verify snapshot loads cleanly with live quotes.
4. `/portfolio-review` — verify digest runs end-to-end with `market-analyst` subagent dispatch.
5. `/rebalance` — verify drift table + `risk-reviewer` + `tax-optimizer` all fire.
6. `/rotation` — verify parallel `momentum-screener` calls, filtering, tax flags.
7. `/research-memo NVDA` — verify single-ticker deep-dive.

At each step, confirm: no hallucinated numbers, every figure traces to a tool call, no silent failures.

- [ ] **Step 5: Write smoke-test log**

Create `tests/smoke/README.md` capturing what worked, what failed, what needs iteration. This is the v1 sign-off artifact.

- [ ] **Step 6: Final commit**

```bash
git add tests/smoke/ README.md
git commit -m "chore: smoke test plan and v1 sign-off checklist"
git tag v0.1.0
```

---

## Self-review (to run before handing off)

- [ ] **Spec coverage:** every section of the design spec maps to at least one task above. Verify Sections 3 (state files), 4 (skills), 5 (subagents), 6 (tools), and 9 (risks) are all implemented.
- [ ] **Placeholder scan:** grep this file for "TBD", "TODO", "later", "etc." — should find none.
- [ ] **Type consistency:** `Trade`, `Lot`, `Account`, `PortfolioSnapshot` names and fields match across `utils/*.py`, all tests, and all subagent definitions.
- [ ] **Commit discipline:** every task ends in a commit.

---

## Deferred (explicitly not in this plan)

- Coin MF CSV parser (stub in place; populate when a real export is available)
- Gmail parser for IndMoney statement auto-import
- Scheduled runs via `schedule` skill
- TLH skill (subagent is capable; dedicated skill not in v1)
- Multi-portfolio (family member) support — architecture permits; not used in v1
