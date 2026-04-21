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
