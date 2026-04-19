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
