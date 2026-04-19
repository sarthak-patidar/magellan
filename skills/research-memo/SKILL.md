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
