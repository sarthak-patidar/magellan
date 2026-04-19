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
