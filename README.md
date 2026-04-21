# magellan

> *"The person that turns over the most rocks wins the game."* — Peter Lynch

A Claude Code / Cowork plugin marketplace for investing-flavored agents. Named after **Fidelity Magellan**, the fund Peter Lynch ran to 29% CAGR over thirteen years.

## Plugins

| Plugin | Description | Status |
| --- | --- | --- |
| [`lynch`](plugins/lynch) | Agentic portfolio manager — India (Kite/Coin) + US (IndMoney). Momentum rotation, IPS-disciplined rebalancing, tax-aware lot selection. Advisory only. | v0.1.0 |

## Install

### Claude Code / Cowork

Add this marketplace:

```
/plugin marketplace add https://github.com/<your-handle>/magellan
```

Install a plugin from it:

```
/plugin install lynch@magellan
```

### Alternative — direct `.plugin` install

Each plugin folder can also be built into a standalone `.plugin` file and dragged into Cowork. See the plugin's own README for that path.

## Layout

```
magellan/
├── .claude-plugin/marketplace.json   # marketplace manifest
├── plugins/
│   └── lynch/                        # one plugin = one folder
│       ├── .claude-plugin/plugin.json
│       ├── skills/
│       ├── agents/
│       └── ...
├── LICENSE                           # applies to all plugins in this repo
└── README.md                         # this file
```

Adding a new plugin: drop it under `plugins/<name>/` with its own `.claude-plugin/plugin.json`, then register it in the `plugins` array of `.claude-plugin/marketplace.json`.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

Copyright 2026 Sarthak Patidar.
