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
