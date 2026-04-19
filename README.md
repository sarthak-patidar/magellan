# personal-pm

Personal agentic portfolio manager built as a Cowork plugin. Advisory only — no trade execution.

## Install (inside Cowork)
1. In Cowork: Plugins → Install from folder → select this directory.
2. On first run, invoke the `financial-plan` skill to author your IPS.
3. Drop CSVs into `imports/YYYY-MM-DD/` and invoke `holdings-import`.

## Markets & brokers
- India: Zerodha Kite (equity) and Zerodha Coin (MF) — CSV or Kite MCP.
- US: IndMoney (Alpaca-backed) — CSV only (no public API).

## Smoke test
First-run checklist is in [`tests/smoke/README.md`](tests/smoke/README.md). Work top-down; stop at the first red flag.

See `docs/superpowers/specs/2026-04-20-agentic-portfolio-manager-design.md` for the full design.
