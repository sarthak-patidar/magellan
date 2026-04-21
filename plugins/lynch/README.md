# lynch

> *"Know what you own, and know why you own it."* — Peter Lynch

Agentic portfolio manager that straddles India and US markets. Momentum-driven rotation, IPS-disciplined rebalancing, tax-aware lot selection. Advisory only — never places a trade.

Named after **Peter Lynch**, who ran Fidelity Magellan at 29% CAGR over thirteen years by staying curious, staying hands-on, and rotating out of what had stopped working.

## What it does

Seven skills answer four questions:

| Question                          | Skill                              |
| --------------------------------- | ---------------------------------- |
| Where am I today?                 | `portfolio-review`, `portfolio-state` |
| Am I drifting from targets?       | `rebalance`                        |
| Should I rotate any positions?    | `rotation`                         |
| What's the story on this ticker?  | `research-memo <TICKER>`           |

Plus `financial-plan` (author your IPS) and `holdings-import` (ingest CSV exports).

## Markets & brokers

- **India** — Zerodha Kite (equity) and Zerodha Coin (MF). CSV or Kite MCP.
- **US** — IndMoney (Alpaca-backed). CSV only (no public API).

## Quick install (Cowork)

1. Package and install the plugin: drag `lynch.plugin` into Cowork chat → click **Install**.
2. Prepare the Python env for the local market-data MCP — see [`docs/usage.md` §4.1](docs/usage.md#41-local-market-data-mcp-required).
3. Run `/financial-plan` to author your IPS.
4. Drop broker CSVs into `imports/YYYY-MM-DD/` and run `/holdings-import`.

Full walkthrough in [`docs/usage.md`](docs/usage.md).

## Principles

- **Every number traces to a source** — tool call or file, never invented.
- **IN and US stay separate** — different currencies, tax regimes, benchmarks.
- **Stale data warns loudly** — `holdings.yaml` > 7 days triggers a warning, never a silent pass.
- **User applies; plugin proposes** — no trade execution, ever.

## Documentation

- [`docs/usage.md`](docs/usage.md) — install, integrations, day-1 setup, operating cadence, skill reference, troubleshooting
- [`tests/smoke/README.md`](tests/smoke/README.md) — first-run sign-off checklist
- [`docs/superpowers/specs/2026-04-20-agentic-portfolio-manager-design.md`](docs/superpowers/specs/2026-04-20-agentic-portfolio-manager-design.md) — full design spec
- [`docs/superpowers/plans/2026-04-20-agentic-portfolio-manager.md`](docs/superpowers/plans/2026-04-20-agentic-portfolio-manager.md) — implementation plan

## Disclaimer

**`lynch` is not financial advice.** It is a decision-support tool that surfaces drift, momentum signals, and tax-lot candidates from *your* data against *your* IPS. Every output is a proposal — you are the one who decides what to trade, and you are the one who places the trade with your broker.

- No warranties, express or implied. See `LICENSE`.
- Markets can and will move against any signal this tool generates.
- Tax rules change. The built-in India/US tax logic is a best-effort approximation — verify with your CA/CPA before acting on any harvesting or LTCG suggestion.
- Past performance of any momentum rule does not predict future returns.

If you need regulated advice, talk to a SEBI-registered investment advisor (India) or a fiduciary RIA (US).

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

Copyright 2026 Sarthak Patidar.
