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

5. **Dispatch `risk-reviewer` subagent** with `{current_weights, proposed_changes}` at the asset-class level.

6. **Dispatch `tax-optimizer` subagent** if any asset-class sells would be realized from taxable accounts. Pass only the candidate sell lots identified by FIFO from each overweight class.

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
