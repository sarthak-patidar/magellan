# Smoke Test — v0.1.0 Sign-off

First-run checklist for the `personal-pm` plugin. Work top-down. Stop at the first red flag and fix before proceeding.

## 0. Prerequisites

- Python 3.10+ with `pip install pandas pyyaml jsonschema`
- For the local market-data MCP: `cd mcps/market_data && pip install -r requirements.txt`
- Cowork / Claude Code with plugin support

## 1. Seed portfolio state

```bash
cd <plugin-dir>
for f in portfolio/*.template; do cp "$f" "${f%.template}"; done
```

Then edit the copied files:
- `portfolio/ips.md` — your objective, horizon, risk stance
- `portfolio/universe-in.yaml` — Nifty 50 constituents you actually want screened
- `portfolio/universe-us.yaml` — Nasdaq 100 (or your own) subset
- `portfolio/targets.yaml` — asset-class targets + bands
- `portfolio/constraints.yaml` — caps, min hold, turnover
- `portfolio/accounts.yaml` — broker accounts
- `portfolio/tax-rules.yaml` — leave as-is unless your residency differs

Validate locally:
```bash
python -c "from utils.state import load_snapshot; load_snapshot('portfolio')"
```
Expect: no exception.

## 2. Seed example imports

Drop CSV exports into `imports/YYYY-MM-DD/`:
- `kite-tradebook.csv` (required)
- `indmoney-trades.csv` (required)
- `kite-holdings.csv` (optional — used for reconciliation)
- `coin-holdings.csv` (optional)
- `indmoney-holdings.csv` (optional)

If only testing: use the fixtures in `tests/fixtures/` as a minimal stand-in.

## 3. Install plugin in Cowork

Cowork UI → Plugins → Install from folder → select plugin root.

Verify in a fresh session:
- [ ] 7 skills appear: `financial-plan`, `holdings-import`, `portfolio-state`, `portfolio-review`, `rebalance`, `rotation`, `research-memo`
- [ ] 5 subagents dispatchable via Task: `market-analyst`, `momentum-screener`, `risk-reviewer`, `tax-optimizer`, `doc-writer`
- [ ] `mcp__market-data__*` tools present (quote, history, fx_usdinr, fundamentals)
- [ ] `mcp__kite__*` tools present if Kite MCP is wired

## 4. Skill-by-skill smoke

Run each in order. Confirm at every step: **no hallucinated numbers, every figure traces to a tool call, no silent failures.**

- [ ] **`/financial-plan`** — walks through IPS elicitation; writes `portfolio/*.yaml` + `portfolio/ips.md`; state loader passes on the updated files.
- [ ] **`/holdings-import`** — picks latest `imports/YYYY-MM-DD/`; FIFO-builds lots per `(account, symbol)`; writes `portfolio/holdings.yaml`; reconciliation diff against `kite-holdings.csv` is sane (<0.5% discrepancy per symbol).
- [ ] **`/portfolio-state`** — staleness check fires if `as_of` > 7 days; live quotes fetched per symbol; FX drift warning if >1% vs stored; derived `market_value_inr` and `drift_vs_target` populated.
- [ ] **`/portfolio-review`** — benchmarks (^NSEI, ^NDX) compared; top-10 holdings + sector breakdown rendered; `market-analyst` dispatched for news on top 5 per market.
- [ ] **`/rebalance`** — asset-class drift table; `risk-reviewer` run; `tax-optimizer` run on proposed sells from taxable accounts; output explicitly says "run rotation for ticker-level".
- [ ] **`/rotation`** — `momentum-screener` dispatched in parallel for IN + US; decay candidates filtered by `min_hold_days`; `tax-optimizer` flags LTCG-approaching lots; `risk-reviewer` passes or trims.
- [ ] **`/research-memo NVDA`** — validates ticker is in universe (or prompts override); `market-analyst` + `momentum-screener` run; memo includes thesis, valuation, momentum, news, IPS fit-check.

## 5. Known-not-implemented (v0.1.0)

Do NOT file these as bugs — they are explicitly deferred per plan:
- Coin MF CSV parser (stub only; `parse_coin_mf_tradebook` raises `NotImplementedError`)
- Gmail / auto-import of IndMoney statements
- Scheduled runs via `schedule` skill
- Dedicated TLH skill (subagent is capable; skill is post-v1)
- Multi-portfolio (family) support

## 6. Sign-off

When all boxes in §3 and §4 tick green, the plugin is v0.1.0-ready. Tag the repo:

```bash
git tag v0.1.0
```

Capture failures (with error trace + the skill / step that produced them) in a new section below titled "Run log — YYYY-MM-DD".
