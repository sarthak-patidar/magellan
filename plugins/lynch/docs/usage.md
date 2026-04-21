# lynch — Usage & Integration Guide

End-to-end guide for installing, wiring, and operating the `lynch` plugin. Advisory-only portfolio manager for India (Zerodha Kite / Coin) and US (IndMoney) markets. Named after Peter Lynch — active, hands-on, rotation-aware.

- **Design spec:** `docs/superpowers/specs/2026-04-20-agentic-portfolio-manager-design.md`
- **Implementation plan:** `docs/superpowers/plans/2026-04-20-agentic-portfolio-manager.md`
- **Smoke test:** `tests/smoke/README.md`

---

## 1. What this plugin does

It is an advisory system that answers four questions, grounded in live market data and your personal IPS:

1. **Where am I today?** — `portfolio-review`, `portfolio-state`
2. **Am I drifting from targets?** — `rebalance`
3. **Should I rotate any positions?** — `rotation`
4. **What's the story on this ticker?** — `research-memo`

It never places trades. Every output is a proposal for you to review.

Seven user-facing skills compose five specialist subagents, two MCPs, and six pure-Python utilities. All state lives in YAML files under `portfolio/` so it's editable, diffable, and portable.

---

## 2. System architecture at a glance

```
┌─────────────────────────────────────────────────────────────┐
│  User invokes a skill (e.g., /rotation)                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Skill orchestrates: reads portfolio/, dispatches           │
│  subagents, calls MCPs, synthesizes output                  │
└─────────────────────────────────────────────────────────────┘
       │              │                │              │
       ▼              ▼                ▼              ▼
  Subagents       MCPs           Utilities       portfolio/
  (Task tool)   (stdio/SSE)    (utils/*.py)     (YAML state)
       │              │                │              │
       ▼              ▼                │              │
  market-       mcp__market-           │              │
  analyst       data__*                │              │
  momentum-     mcp__kite__*           │              │
  screener      (optional)             │              │
  risk-                                │              │
  reviewer                             │              │
  tax-                                 │              │
  optimizer                            │              │
  doc-writer                           │              │
```

---

## 3. Install

### 3.1 Cowork (primary path)

The plugin ships as a `.plugin` file (a zip of the repo at a tagged commit). To install:

1. Open Cowork → attach the `lynch.plugin` file in chat (or drag it in).
2. Cowork renders a rich install preview. Review the contents, click **Install**.
3. After install, run `/reload-plugins` (or start a new session) so all skills / subagents / MCPs are discovered.

To (re)build the `.plugin` from a source checkout:

```bash
cd /path/to/portfolio-management
git archive --format=zip HEAD -o /tmp/lynch.plugin
# Attach /tmp/lynch.plugin to a Cowork message
```

`git archive` produces a clean zip from tracked files only — no `.venv`, no `.idea`, no IDE clutter.

### 3.2 Claude Code (alternate path)

If you're running this in Claude Code CLI instead of Cowork:

```bash
# From inside a Claude Code session, pointing at the plugin folder
/plugin marketplace add /path/to/portfolio-management
/plugin install lynch@<marketplace-name>
/reload-plugins
```

### 3.3 Sanity check after install

In a fresh session, confirm:

- `/skill` picker lists: `financial-plan`, `holdings-import`, `portfolio-state`, `portfolio-review`, `rebalance`, `rotation`, `research-memo`
- `/agents` lists: `market-analyst`, `momentum-screener`, `risk-reviewer`, `tax-optimizer`, `doc-writer`
- `/mcp` shows both servers healthy: `kite` (SSE) and `market-data` (stdio)

If any of the above is missing, see §8 Troubleshooting.

---

## 4. External integrations

Four outside systems touch this plugin. Each has its own setup story.

### 4.1 Local market-data MCP (required)

A thin yfinance wrapper at `mcps/market_data/server.py`. Exposes four tools: `quote`, `history`, `fx_usdinr`, `fundamentals`.

**Setup** — create a Python env and install deps:

```bash
cd /path/to/portfolio-management
python3 -m venv .venv
source .venv/bin/activate
pip install -r mcps/market_data/requirements.txt    # mcp + yfinance
pip install pandas pyyaml jsonschema                # for utils/*.py + state loader
```

**Wire it to Cowork.** Edit `.mcp.json` to use the venv's Python interpreter explicitly. Cowork does not activate virtualenvs on your behalf.

```json
{
  "mcpServers": {
    "market-data": {
      "command": "/absolute/path/to/portfolio-management/.venv/bin/python",
      "args": ["mcps/market_data/server.py"]
    }
  }
}
```

**Rate limits.** yfinance scrapes Yahoo; it has no SLA. The skills batch reads and cache implicitly via the skill flow. If you hit an HTTP 429 burst, wait 5–10 minutes.

### 4.2 Zerodha Kite MCP (optional)

Remote SSE server at `https://mcp.kite.trade/mcp`. Gives you programmatic holdings and order placement from Kite Connect. In v0.1.0 we only *read* from it — we never place orders.

**Auth flow.** First tool call triggers Zerodha OAuth in a browser popup. Log in with your Kite credentials. The token lives in the SSE session and expires daily (6 AM IST per Kite policy) — expect to re-auth once per morning.

**Bypass.** If Kite MCP is flaky on your setup, skip it. Set `source: csv` (the default) in `portfolio/accounts.yaml` and use the CSV ingestion path via `/holdings-import`. You lose nothing except convenience.

### 4.3 Broker CSV exports (required if you skip Kite MCP)

The `holdings-import` skill reads from `imports/YYYY-MM-DD/`. Expected files:

| File                    | Required | Source                                                       |
| ----------------------- | -------- | ------------------------------------------------------------ |
| `kite-tradebook.csv`    | yes      | Kite Web → Reports → Tradebook → Download CSV for all years  |
| `kite-holdings.csv`     | no       | Kite Web → Holdings → Download CSV (used for reconciliation) |
| `coin-holdings.csv`     | no       | Coin → Holdings → Export (v0.1.0 parser is a stub)           |
| `indmoney-trades.csv`   | yes      | IndMoney app → Orders → Export                               |
| `indmoney-holdings.csv` | no       | IndMoney app → Portfolio → Export                            |

**Schema expectations** are encoded in `utils/csv_parsers.py`. If a broker changes their export format, that's the file to update.

### 4.4 AMFI daily NAV (automatic)

For mutual fund lots, the `portfolio-state` skill fetches the canonical daily NAV file from AMFI at runtime:

```
https://www.amfiindia.com/spages/NAVAll.txt
```

Semicolon-delimited, parsed by `utils/amfi_nav.py`. No auth, no API key. Cached to `/tmp/amfi-nav.txt` during the skill's invocation.

---

## 5. Day-1 setup

A clean checkout → working portfolio in ~15 minutes.

### Step 1: Seed the portfolio folder

Every file under `portfolio/` exists as a `.template`. Copy and edit:

```bash
cd /path/to/portfolio-management
for f in portfolio/*.template; do cp "$f" "${f%.template}"; done
```

Then edit — ideally via the `financial-plan` skill, which walks you through the fields interactively. Manual path:

| File               | What to fill in                                                     |
| ------------------ | ------------------------------------------------------------------- |
| `ips.md`           | Objective, horizon, risk tolerance — free-form markdown             |
| `targets.yaml`     | Asset-class targets and bands (equity_in, equity_us, mf_in, cash)   |
| `constraints.yaml` | Single-issuer cap, sector cap, min hold days, turnover cap, benchmarks |
| `universe-in.yaml` | Nifty 50 tickers you actually want screened (`.NS` suffix for yfinance) |
| `universe-us.yaml` | Nasdaq 100 subset you care about                                    |
| `accounts.yaml`    | Your broker accounts: id, market, instrument, currency, residency, source |
| `tax-rules.yaml`   | Leave as-is unless your residency isn't India                       |

After editing, validate:

```bash
source .venv/bin/activate
python -c "from utils.state import load_snapshot; load_snapshot('portfolio')"
```

A clean exit = all files parse and cross-validate against schemas.

### Step 2: Drop your first CSV exports

Create the imports folder for today's date and drop broker CSVs:

```bash
mkdir -p imports/$(date +%F)
# Copy kite-tradebook.csv and indmoney-trades.csv into that folder
```

### Step 3: Build holdings

In Cowork:

```
Run /holdings-import
```

What happens:

1. Skill finds the latest `imports/YYYY-MM-DD/` folder.
2. CSVs parsed via `utils/csv_parsers.py` → normalized trade stream per `(account, symbol)`.
3. FIFO replay via `utils/fifo.py` → open lots.
4. USD→INR basis enrichment for IndMoney lots (fetches historical FX on each lot's `entry_date`).
5. Reconciliation against `kite-holdings.csv` if present. If qty diverges by >0.5% for any symbol, the skill flags loudly and writes to `holdings.yaml.proposed` instead of `holdings.yaml`.
6. On clean reconciliation, writes `portfolio/holdings.yaml` and emits a diff vs. the prior snapshot.

### Step 4: Sanity snapshot

```
Run /portfolio-state
```

This is the canonical loader every other skill uses internally. Running it standalone lets you verify live data flows end-to-end before invoking heavier skills.

---

## 6. Operating cadence

Suggested rhythm. Adjust to taste; the plugin doesn't enforce schedules.

| Cadence    | Action                                      | Skill                    |
| ---------- | ------------------------------------------- | ------------------------ |
| Daily      | Refresh CSVs if you traded                  | `holdings-import`        |
| Weekly     | Drift + news check                          | `portfolio-review`       |
| Monthly    | Drift fix at asset-class level              | `rebalance`              |
| Monthly    | Per-ticker momentum rotation                | `rotation`               |
| On demand  | Deep dive on a ticker                       | `research-memo <TICKER>` |
| Annually   | Revisit IPS, targets, constraints           | `financial-plan`         |

**Rule of thumb:** run `rebalance` first to decide *how much* to move between asset classes, then `rotation` to decide *which tickers* implement that move.

---

## 7. Skill & subagent reference

### 7.1 Skills

| Skill              | Inputs                           | Primary output                                       | Internal dispatches                         |
| ------------------ | -------------------------------- | ---------------------------------------------------- | ------------------------------------------- |
| `financial-plan`   | Interactive Q&A                  | Written `portfolio/ips.md`, `targets.yaml`, `constraints.yaml` | None                                        |
| `holdings-import`  | `imports/YYYY-MM-DD/*.csv`       | `portfolio/holdings.yaml` + reconciliation report    | None                                        |
| `portfolio-state`  | `portfolio/*.yaml`               | In-memory `PortfolioSnapshot` + derived weights      | `mcp__market-data__*`                       |
| `portfolio-review` | Current snapshot                 | Performance + drift + news digest                    | `market-analyst` (news), `doc-writer` (opt) |
| `rebalance`        | Current snapshot + IPS           | Asset-class reallocation table + risk/tax flags      | `risk-reviewer`, `tax-optimizer`, `doc-writer` (opt) |
| `rotation`         | Current snapshot + universes     | Per-market exit/entry tables with tax flags          | `momentum-screener` (parallel per market), `tax-optimizer`, `risk-reviewer`, `doc-writer` (opt) |
| `research-memo`    | Ticker symbol                    | Thesis, valuation, momentum, news, IPS fit-check     | `market-analyst`, `momentum-screener`, `doc-writer` (opt) |

### 7.2 Subagents (dispatched, not invoked directly)

| Subagent            | Job                                                                         | Tools used                                                                                              |
| ------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `market-analyst`    | Pull quotes, fundamentals, news for a set of tickers. Returns structured digest. | `mcp__market-data__quote`, `mcp__market-data__history`, `mcp__market-data__fundamentals`, `WebSearch`     |
| `momentum-screener` | Rank a universe by composite 3/6/12m return + RS vs benchmark + 200-DMA.    | `mcp__market-data__history`, `Bash` (calls `utils.momentum.compute_momentum`)                             |
| `risk-reviewer`     | Validate a proposed change set against IPS concentration / sector / turnover caps. Returns pass / warn / fail. | `Read` (portfolio/targets.yaml, portfolio/constraints.yaml)                                              |
| `tax-optimizer`     | Classify proposed sells as STCG vs LTCG per lot. Flag LTCG-approaching lots. Flag min-hold breaches. | `Bash` (calls `utils.tax.classify`), `Read` (portfolio/accounts.yaml)                                    |
| `doc-writer`        | Convert a structured payload into a Word or PDF artifact.                   | `Skill` (invokes `docx` or `pdf`), `Write`                                                              |

**Key rule:** subagents never write state. Only skills do.

---

## 8. Troubleshooting

| Symptom                                           | Likely cause                                                  | Fix                                                                         |
| ------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Skill says "holdings.yaml is N days old"          | You haven't re-imported recently                              | Run `/holdings-import` with today's CSVs                                    |
| `market-data` MCP shows "not connected" in `/mcp` | Python interpreter can't find `yfinance` or `mcp`             | Fix `command` in `.mcp.json` to point at the venv's python; verify with `python mcps/market_data/server.py` in that shell |
| Live quotes come back `null`                      | yfinance rate-limited or ticker symbol wrong                  | Check ticker (e.g., `RELIANCE.NS` not `RELIANCE`); wait 10 min on rate limit |
| `kite` MCP fails with auth error                  | Token expired (happens daily 6 AM IST)                        | Re-auth by invoking any Kite tool — browser popup will reopen               |
| `portfolio-state` validation error                | One of `portfolio/*.yaml` out of sync with its schema         | Run `python -c "from utils.state import load_snapshot; load_snapshot('portfolio')"` — the exception names the offending file |
| `holdings-import` writes `.proposed` not `.yaml`  | Reconciliation failed (qty disagrees with `kite-holdings.csv`)  | Inspect the diff output, reconcile manually, then `mv holdings.yaml.proposed holdings.yaml` |
| `rotation` returns zero exit candidates           | All holdings are within `min_hold_days` (default 90)          | Expected behaviour during early lifetime of a rotation program              |
| `rebalance` says `risk-reviewer: fail` and stops   | Proposed change would breach a cap                             | Read the finding. Either loosen the cap (edit `constraints.yaml`) or pick a different reallocation |
| `tax-optimizer` raises `NoMatchingRule`           | Your `residency` + `market` + `instrument` combo has no rule   | Add the missing rule to `portfolio/tax-rules.yaml` — see the four existing rules as templates |
| Subagent dispatch times out                       | yfinance history call for a universe is slow                  | Trim `universe-*.yaml` — don't screen tickers you'd never actually trade    |

---

## 9. State file reference

Authoritative: `schemas/*.schema.json` (draft-07 JSON Schema). One-line summaries:

| File                      | Purpose                                                        | Who writes it                |
| ------------------------- | -------------------------------------------------------------- | ---------------------------- |
| `portfolio/accounts.yaml` | Broker accounts with market, instrument, residency, currency, source | `financial-plan`, manual     |
| `portfolio/ips.md`        | Your written investment policy statement                       | `financial-plan`, manual     |
| `portfolio/targets.yaml`  | Asset-class targets with min/max bands                         | `financial-plan`, manual     |
| `portfolio/constraints.yaml` | Caps, min hold days, turnover cap, per-market benchmarks     | `financial-plan`, manual     |
| `portfolio/universe-in.yaml` | Screened Indian tickers                                     | Manual                       |
| `portfolio/universe-us.yaml` | Screened US tickers                                         | Manual                       |
| `portfolio/tax-rules.yaml` | STCG / LTCG rules per market × instrument × residency          | Ships filled; edit only if your jurisdiction differs |
| `portfolio/holdings.yaml` | Current lots + FX snapshot                                     | `holdings-import` only       |

**Rule:** every skill *reads* `portfolio/` freely. Only `financial-plan` and `holdings-import` *write* to it. Others propose; the user applies.

---

## 10. Evolution notes

### 10.1 Deferred (not bugs — explicitly out of v0.1.0)

- Coin MF CSV parser (stub raises `NotImplementedError` — populate when a real export is available)
- Gmail parser for auto-ingesting IndMoney statements
- Scheduled runs via the `schedule` skill
- Dedicated tax-loss-harvesting skill (the `tax-optimizer` subagent is capable; a user-facing skill isn't in v0.1.0)
- Multi-portfolio / family-member support (architecture permits; not exercised)

### 10.2 Replacing the market-data MCP

The yfinance wrapper is 80 lines. Swap it for any better data source by preserving the four tool signatures: `quote(symbol) → {close, prev_close, change_pct, as_of}`, `history(symbol, period) → {closes: [{date, close}]}`, `fx_usdinr() → {rate, as_of}`, `fundamentals(symbol) → {pe, market_cap, sector, ...}`. Everything else keeps working unchanged.

### 10.3 Activating the Kite MCP read path

When you're ready to replace CSV reconciliation with live Kite reads, set `source: mcp` for the Kite-backed account in `portfolio/accounts.yaml`. The `holdings-import` skill has an explicit upgrade hook that prefers MCP when both are available.

### 10.4 Adding a new skill

Drop a `skills/<new-skill>/SKILL.md` file with frontmatter (`name`, `description`) and a body written in imperative voice. Run `/reload-plugins`. That's the whole flow.

---

## 11. What this plugin deliberately does not do

- **Place trades.** Every output is a proposal. You approve in your broker UI.
- **Rank across markets.** IN and US are always separate tables. Currency and tax regimes are not comparable on a single axis.
- **Hallucinate numbers.** Every figure must trace to a tool call or a file. Subagents have explicit "never invent numbers" rules.
- **Hide stale data.** A `holdings.yaml` older than 7 days produces a warning, not a silent pass.
- **Enforce schedules.** The plugin has no cron. You choose when to run each skill.
