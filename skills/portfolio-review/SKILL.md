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
