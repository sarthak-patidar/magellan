# Agentic Portfolio Manager — Design Spec

**Date:** 2026-04-20
**Owner:** Symplora
**Status:** Draft for review

---

## 1. Problem framing

Build a personal AI portfolio manager that lives entirely inside Claude (Cowork) as a composition of **skills, subagents, tools, and state files** — with effectively zero custom code. The system supports **investing and momentum-driven rotation with a minimum holding period of ~1 month** across two markets:

- **India:** Zerodha Kite (equity) and Zerodha Coin (mutual funds)
- **US:** IndMoney (US equities, Alpaca-backed)

The user is the portfolio owner (self + occasional family portfolios). The agent is **advisory only** — it analyses, recommends, and drafts; the user executes trades manually in the respective brokerage apps.

### In scope
- Load, normalize, and reconcile holdings across three accounts into a single canonical model
- Produce drift-based rebalance recommendations against a personal IPS
- Produce momentum-driven rotation recommendations per market, respecting minimum hold and LTCG windows
- Periodic portfolio reviews (performance, drift, concentration, news)
- On-demand ticker research memos
- Personal IPS authoring and updates
- Consolidated INR reporting with per-market drill-down

### Out of scope (explicit)
- Trade execution, order placement, or any write-side broker interaction
- Options, futures, F&O, intraday, margin, shorting
- Multi-tenant auth, user management, DB persistence, compliance audit log
- DocuSign / e-signature flows
- Client-facing workflows (client reviews, prospect proposals, client reports)
- Scheduled / autonomous runs (v1 is user-triggered; reuse existing `schedule` skill later if wanted)

### Constraints
- No Kite Connect subscription available → no live Kite API in v1
- IndMoney does not expose a customer API → file-based ingestion only
- Must live inside Cowork as a single installable plugin

### Success criteria
- User can trigger a rotation or rebalance workflow conversationally and receive a trade list grounded in real, validated holdings and prices
- Every number in every output traces back to a tool call or state file — zero hallucinated figures
- Minimum-hold and LTCG-window rules are enforced automatically with no manual cross-checking
- New markets, accounts, or rules can be added by editing a YAML file, not by writing code

---

## 2. Architectural overview

Three layers, one deployment artifact (a Cowork plugin).

```
┌─────────────────────────────────────────────────────────────┐
│  SKILLS (markdown playbooks — entry points)                │
│  portfolio-state · holdings-import · rebalance · rotation   │
│  portfolio-review · research-memo · financial-plan          │
└─────────────────────────────────────────────────────────────┘
                         │ dispatches via Task tool
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  SUBAGENTS (bounded specialists)                            │
│  market-analyst · momentum-screener · risk-reviewer         │
│  tax-optimizer · doc-writer                                 │
└─────────────────────────────────────────────────────────────┘
                         │ tool calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  TOOLS (MCPs + state files)                                 │
│  market-data (yfinance) · AMFI NAV · FX · Kite MCP (opt.)   │
│  Gmail · Drive · local files in portfolio/                  │
└─────────────────────────────────────────────────────────────┘
```

**Guiding principles**

- **Files are the database.** All portfolio state — holdings, lots, IPS, targets, universes, tax rules — lives as plain YAML / markdown in a Cowork-mounted folder. User-editable, inspectable, versionable. No DB, no ORM, no migrations.
- **Skills are playbooks, not code.** Each skill is a `SKILL.md` that defines inputs, steps, subagent dispatches, and output contract. Evolving a skill means editing markdown.
- **Subagents are for isolation.** Dispatched when context isolation or parallelism buys something. Default to inline for simple cases.
- **Every output number is grounded.** No figure appears in a report unless it came from a tool call or a state file loaded in the current run.
- **Jurisdiction-aware from day one.** Tax and regulatory rules live in data, not prompts.

---

## 3. State files (the canonical model)

All files live under a Cowork-mounted `portfolio/` folder owned by the user.

```
portfolio/
  ips.md                    # personal IPS prose: objectives, risk, constraints
  targets.yaml              # allocation bands by asset class + per-market caps
  constraints.yaml          # min_hold_days, turnover_cap, concentration caps
  universe-in.yaml          # Nifty 50 tickers + optional watchlist additions
  universe-us.yaml          # Nasdaq 100 tickers + optional watchlist additions
  tax-rules.yaml            # dual-jurisdiction brackets and thresholds
  accounts.yaml             # registry: id, broker, market, currency, source type
  holdings.yaml             # canonical normalized holdings + lots (derived)
  imports/
    YYYY-MM-DD/
      kite-holdings.csv
      kite-tradebook.csv
      coin-holdings.csv
      indmoney-holdings.csv
      indmoney-trades.csv
```

### `accounts.yaml` (example shape)

```yaml
accounts:
  - id: kite-eq
    broker: zerodha_kite
    market: IN
    currency: INR
    source: csv            # or 'mcp' if Kite MCP becomes available
    residency: IN          # tax residency of account holder
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
    residency: IN          # <- triggers foreign-equity tax treatment
```

### `targets.yaml` (example shape)

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

### `constraints.yaml` (example shape)

```yaml
min_hold_days: 30
turnover_cap_monthly: 0.30
concentration_caps:
  single_issuer: 0.08
  sector: 0.30
benchmarks:
  IN: "^NSEI"    # Nifty 50
  US: "^NDX"     # Nasdaq 100
```

### `tax-rules.yaml` (example shape)

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
  - id: us_equity_for_in_resident
    match: {market: US, instrument: equity, residency: IN}
    stcg: {hold_lt_days: 730, rate: "slab"}   # unlisted foreign equity treatment
    ltcg: {hold_gte_days: 730, rate: 0.125}
```

> **Note on `us_equity_for_in_resident`:** US equities held by Indian residents are treated as unlisted foreign equity for Indian tax purposes — LTCG boundary is **24 months**, not 12. This differs materially from US-resident treatment and from Indian listed equity. This rule table is the authoritative source; tax-optimizer reads from it, never hardcodes.

### `holdings.yaml` (canonical, derived)

```yaml
as_of: 2026-04-20
fx:
  USDINR: 83.42
lots:
  - account: kite-eq
    symbol: RELIANCE.NS
    market: IN
    instrument: equity
    qty: 50
    avg_cost_inr: 2450.00
    entry_date: 2025-11-12
    cost_basis_inr: 122500.00
  - account: indmoney-us
    symbol: NVDA
    market: US
    instrument: equity
    qty: 10
    avg_cost_usd: 785.00
    entry_date: 2024-09-03
    cost_basis_usd: 7850.00
```

---

## 4. Skills

Each skill is an entry point. Invoked by intent or slash command. Defined as `SKILL.md` with frontmatter (name, description, trigger words) and a step-by-step runbook.

### 4.1 `portfolio-state`

**Purpose:** canonical loader. Every other skill calls this first.

**Inputs:** optional `as_of` date (defaults to today), optional `account_id` filter.

**Steps:**
1. Load `accounts.yaml`, `ips.md`, `targets.yaml`, `constraints.yaml`, `tax-rules.yaml`, universes.
2. Load `holdings.yaml`. If stale (older than 7 days) or missing, emit a warning and prompt the user to run `holdings-import`.
3. Call FX tool for current USD/INR. Cache for session.
4. Call market-data tool for current quotes for all held symbols.
5. Compute market values (native and INR-converted), current weights, drift vs targets, per-lot hold-days and tax status.
6. Validate: no negative quantities, no unknown symbols, no lots without entry dates (fail loudly).

**Output contract:** structured `PortfolioSnapshot` with `accounts`, `lots`, `positions_by_symbol`, `weights`, `drift`, `tax_status_by_lot`, `warnings`.

### 4.2 `holdings-import`

**Purpose:** ingest CSV drops, reconstruct lots via FIFO, update `holdings.yaml`.

**Inputs:** path to the import folder (default: latest `imports/YYYY-MM-DD/`).

**Steps:**
1. Detect available files (kite-holdings, kite-tradebook, coin-holdings, indmoney-holdings, indmoney-trades).
2. Parse each per its known schema (each broker has a different CSV shape — skill contains the column maps).
3. For each account: apply tradebook/trade history chronologically → build FIFO lots → reconcile against current holdings snapshot; flag discrepancies.
4. Merge across accounts, write `holdings.yaml`.
5. Emit a reconciliation report (what changed since previous `holdings.yaml`).

**Output contract:** updated `holdings.yaml` + reconciliation diff printed to user.

**Upgrade hook:** if `accounts.yaml` marks any account `source: mcp` and a Kite MCP is registered, skip the CSV step for that account and pull live via the MCP. Same output.

### 4.3 `rebalance`

**Purpose:** drift-to-IPS recommendations (asset-class bands, per-market caps).

**Steps:**
1. Call `portfolio-state`.
2. Compare current weights to bands in `targets.yaml`.
3. For each band breach, propose reallocation at the asset-class level (not single-ticker level — that's `rotation`'s job).
4. Dispatch `risk-reviewer` subagent on the proposed allocation → pass/warn/fail.
5. Dispatch `tax-optimizer` on any sell-side implications → flag LTCG windows and min-hold violations.
6. Emit a final recommendation: reallocation table + cash flow required + rationale.

### 4.4 `rotation`

**Purpose:** per-market momentum-driven position changes.

**Steps:**
1. Call `portfolio-state`.
2. Dispatch `momentum-screener` for IN and US universes in **parallel** → two ranked tables. The screener's input universe for each market = the market's universe file ∪ symbols currently held in that market. This ensures currently-held off-universe names (e.g., a mid-cap held while the universe is Nifty 50) are ranked on the same basis as candidates.
3. Compare current holdings' momentum rank vs universe leaders. Identify:
   - Decay candidates (current holdings dropping out of top quartile)
   - Entry candidates (universe leaders not currently held)
4. Filter out proposed exits that violate `min_hold_days` (from `constraints.yaml`).
5. Dispatch `tax-optimizer` → flag exits inside LTCG-deferral window (e.g., lot 10-14 months old for IN equity; 20-24 months for US equity).
6. Dispatch `risk-reviewer` → concentration, sector, per-market caps, turnover budget check.
7. Emit per-market rotation proposals: {sells, buys, rationale, risk flags, tax flags}.

### 4.5 `portfolio-review`

**Purpose:** periodic check-in digest.

**Steps:**
1. `portfolio-state`.
2. Performance: period return (user-specified or default 1m/3m/YTD) vs benchmarks from `constraints.yaml`.
3. Drift snapshot.
4. Concentration + sector breakdown.
5. Dispatch `market-analyst` for top holdings → news digest.
6. Optional: invoke `doc-writer` to produce a Word doc.

### 4.6 `research-memo`

**Purpose:** on-demand ticker deep-dive.

**Steps:**
1. Validate ticker is in one of the universes (or explicit override).
2. Dispatch `market-analyst` (fundamentals, valuation, news).
3. Dispatch `momentum-screener` (single-ticker mode — rank metrics for this ticker only).
4. Synthesize: thesis, key metrics, risk factors, fit-for-IPS commentary.
5. Optional `doc-writer`.

### 4.7 `financial-plan`

**Purpose:** author or update the personal IPS.

**Steps:**
1. Interactive (or read from prior draft): objectives, risk tolerance, horizon, liquidity needs, constraints.
2. Propose asset-class bands + per-market caps.
3. Emit `ips.md`, `targets.yaml`, `constraints.yaml` updates.
4. Validate internal consistency (bands sum sanity, caps reasonable, benchmarks valid).

---

## 5. Subagents

Defined in the plugin as agent configs. Each has a narrow role, defined input schema, and output contract.

### 5.1 `market-analyst`
- **Input:** `{tickers: [...], market: IN|US, need: [quotes|fundamentals|news]}`
- **Behavior:** calls market-data MCP + web search for news; synthesizes a structured digest.
- **Output:** `{ticker: {price, pe, mcap, ytd_return, news_headlines}}`

### 5.2 `momentum-screener`
- **Input:** `{market: IN|US, tickers: [...], as_of: date, lookbacks: [3m,6m,12m]}`
- **Behavior:** reads the market's benchmark from `constraints.yaml` (`benchmarks.IN` or `benchmarks.US`); fetches EOD price history for `tickers` and benchmark; computes standard momentum stack (total return over lookbacks, 52-week-high proximity, 200-day MA distance, relative strength vs benchmark); produces composite rank with equal-weighted lookbacks by default.
- **Output:** ranked table `[{ticker, composite_rank, momentum_score, 3m, 6m, 12m, rs_vs_bench}]`

### 5.3 `risk-reviewer`
- **Input:** `{current_holdings, proposed_changes, constraints}`
- **Behavior:** applies constraint checks — single-issuer cap, sector cap, per-market cap, turnover budget, beta/vol drift.
- **Output:** `{status: pass|warn|fail, findings: [{rule, severity, detail}]}`

### 5.4 `tax-optimizer`
- **Input:** `{lots, proposed_sells, tax_rules}`
- **Behavior:** for each proposed sell, classifies STCG vs LTCG from rule table; flags lots approaching LTCG boundary (within configurable window, default 60 days); suggests lot-selection (highest-cost-basis within tax-equivalent lots); identifies min-hold violations.
- **Output:** `{per_sell: {stcg_or_ltcg, days_to_ltcg, lot_selection_advice, warnings}}`

### 5.5 `doc-writer`
- **Input:** `{report_type, payload}`
- **Behavior:** renders to Word or PDF via existing `docx` / `pdf` skills; saves to outputs folder.
- **Output:** file path + preview.

---

## 6. Tools (MCPs)

Registered by the plugin manifest:

| Tool | Type | Purpose | Notes |
|---|---|---|---|
| `market-data` | MCP (off-the-shelf or thin custom) | EOD quotes, history, fundamentals for `.NS` and Nasdaq tickers | yfinance-backed; community MCP preferred; build only if no fit |
| `amfi-nav` | Skill-level fetch (no MCP) | Daily AMFI NAV file for Indian MF valuation | Public URL, ~1MB daily CSV |
| `fx` | MCP / skill-level | USDINR spot | yfinance `USDINR=X` is sufficient |
| `kite-mcp` | MCP (optional upgrade) | Live Kite equity + Coin MF holdings | Registered via plugin manifest as remote SSE to `mcp.kite.trade` |
| `gmail` | MCP (existing) | Optional future automation of IndMoney statement parsing | Out of v1 scope but wired in |
| `drive` | MCP (existing) | Optional output delivery | Out of v1 scope for MVP |

**Kite MCP registration note:** the hosted Zerodha MCP is SSE/remote. Cowork plugins register remote MCPs in the plugin manifest under the MCP config block. Once registered, its tools surface into skills and subagents running in sessions with this plugin installed. This sidesteps the earlier issue of it being configured only in Claude Desktop's `developer settings` (which does not propagate to Cowork).

---

## 7. Orchestration pattern

Example: user says *"let's do this month's rotation review."*

1. Session invokes `rotation` skill.
2. `rotation` calls `portfolio-state` (inline, same context).
3. `portfolio-state` validates, loads, enriches with FX + quotes. Returns `PortfolioSnapshot`.
4. `rotation` dispatches `momentum-screener(IN)` and `momentum-screener(US)` **in parallel** via Task tool (isolated subagent contexts).
5. Results return. `rotation` computes decay candidates and entry candidates per market.
6. `rotation` dispatches `tax-optimizer` with proposed sells.
7. `rotation` dispatches `risk-reviewer` with full proposed change-set.
8. `rotation` synthesizes: per-market proposal tables with tax + risk flags.
9. Optionally invokes `doc-writer` for a Word artifact.
10. Returns a conversational summary + artifact link.

All of step-logic lives in `rotation/SKILL.md`. No code.

---

## 8. Tradeoffs

### Files as state
- **Pro:** zero infra, user-editable, Git-friendly, inspectable, easy to back up.
- **Con:** no schema enforcement; no concurrency control.
- **Mitigation:** `portfolio-state` validates shape on every load and fails loudly on drift. Solo use = concurrency is a non-issue.

### CSV ingestion vs live API
- **Pro:** works with any broker, no subscriptions, no OAuth fragility, no rate limits.
- **Con:** manual ritual (weekly export). Staleness risk if user forgets.
- **Mitigation:** `portfolio-state` emits a loud warning if `holdings.yaml` age > 7 days. Kite MCP is a drop-in upgrade when wanted.

### Subagent dispatch cost
- **Pro:** context isolation, parallelism, cleaner output contracts.
- **Con:** token overhead; not free.
- **Mitigation:** default to inline; promote to subagent only where isolation or parallelism earns it. Current promotions: `market-analyst`, `momentum-screener` (parallelism), `risk-reviewer`, `tax-optimizer` (clean contract + reusability), `doc-writer` (large output context).

### Advisory-only vs executable
- **Pro:** removes 80% of integration risk (auth scopes, idempotency, slippage, compliance).
- **Con:** user is the execution bottleneck; errors possible in manual entry.
- **Mitigation:** trade lists are emitted in a copy-pasteable format with exact quantities and limit-price suggestions.

### Monolithic "PM agent" vs layered skills+subagents
- Rejected monolithic approach: hard to evolve, no parallelism, context bloat, painful to debug when one step misbehaves. Layered wins on every axis at this scale.

---

## 9. Risks & edge cases

| Risk | Impact | Mitigation |
|---|---|---|
| **Hallucinated prices or tickers** | Wrong trade recommendations | Every numeric output must trace to a tool call; skills include a verification step before emitting outputs; `portfolio-state` validates symbols against universe files |
| **Missing lot-level entry dates** | Can't enforce min-hold or LTCG windows | Tradebook CSVs are mandatory inputs in the import ritual; `portfolio-state` fails loudly on any lot without an entry date |
| **Stale quotes vs stale holdings** | Inconsistent picture | `holdings.yaml` has `as_of`; quotes are intraday-refresh; report shows both timestamps explicitly |
| **Wrong tax jurisdiction applied** | Bad LTCG advice (e.g., 12mo instead of 24mo for US equity held by IN resident) | Rules are data in `tax-rules.yaml`, matched by `{market, instrument, residency}` triple; no hardcoded tax logic anywhere; unit-test the matcher with jurisdiction fixtures |
| **Concentration creep in momentum rotation** | Portfolio piles into hot sectors | `risk-reviewer` enforces sector + per-market caps on every rotation; fails the recommendation if caps breached |
| **Universe drift (Nifty 50 or Nasdaq 100 rebalance)** | Stale universe files | `financial-plan` / manual refresh workflow; document the annual refresh ritual in `ips.md` |
| **IndMoney CSV schema changes** | Import breaks silently | `holdings-import` asserts expected columns and fails loudly with a clear diff |
| **USDINR spike between review and execution** | INR allocations miss targets | Recommendations emit native-currency quantities AND INR equivalents at a captured FX rate; user knows to treat INR figures as indicative |
| **User runs rotation daily and churns portfolio** | Momentum edge destroyed by costs | `risk-reviewer` enforces `turnover_cap_monthly`; skill prompts user if frequency exceeds monthly cadence |

---

## 10. Future (explicitly deferred)

- **Kite MCP live integration** — drop-in upgrade to CSV ingestion when registered in plugin manifest. Same `holdings-import` output contract.
- **Scheduled runs** — use existing `schedule` skill to run `portfolio-review` monthly.
- **IndMoney Gmail parser** — auto-import from statement emails if the CSV ritual proves too fiddly.
- **TLH skill** — tax-loss harvesting is deferred (not in P0 list) but the `tax-optimizer` subagent is scaffolded to support it.
- **Universe expansion** — Nifty 500 for India if Nifty 50 signals are noisy; S&P 500 + sector ETFs for US if Nasdaq 100 is too tech-concentrated for rotation diversity.
- **Multi-portfolio (family members)** — the `account_id` + `residency` fields in `accounts.yaml` and the `portfolio-state` skill's account-filter arg are designed to extend cleanly. Adding a portfolio means a new folder + new accounts file.

---

## 11. Deliverables for implementation

A single Cowork plugin (`personal-pm.plugin`) containing:

1. Plugin manifest with MCP registrations (market-data, fx, optional kite-mcp).
2. Seven skill markdown files.
3. Five subagent definition files.
4. A `portfolio/` folder template with example YAMLs and an `ips.md` starter.
5. A README with the import ritual, install steps, and first-run walkthrough.

Custom code: target zero. Only acceptable custom code is a thin market-data MCP if no off-the-shelf option covers both `.NS` and Nasdaq tickers with EOD history — and in that case ≤200 LOC.

---

## 12. Open questions (resolve before implementation plan)

None blocking. Items to revisit during planning:

1. Exact community MCP for yfinance-backed EOD data (evaluate 2–3, pick one).
2. Whether AMFI NAV fetch should be a skill-level curl or a thin MCP (lean: skill).
3. Momentum scoring weights (equal-weight 3/6/12m by default; revisit after 2–3 months of use).
