"""State loader: validates + assembles a PortfolioSnapshot from the portfolio/ folder."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import yaml
from jsonschema import validate, ValidationError as JSONSchemaError


class ValidationError(Exception):
    pass


@dataclass
class Account:
    id: str
    broker: str
    market: str
    currency: str
    source: str
    residency: str


@dataclass
class HoldingLot:
    """Persisted lot in holdings.yaml — richer than utils.fifo.Lot (adds account/market/instrument)."""
    account: str
    symbol: str
    market: str
    instrument: str
    qty: float
    entry_date: str
    avg_cost_inr: float | None = None
    avg_cost_usd: float | None = None
    cost_basis_inr: float | None = None
    cost_basis_usd: float | None = None


@dataclass
class PortfolioSnapshot:
    as_of: str
    fx_usdinr: float
    accounts: list[Account] = field(default_factory=list)
    lots: list[HoldingLot] = field(default_factory=list)
    targets: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    tax_rules: list = field(default_factory=list)
    universes: dict[str, dict] = field(default_factory=dict)


def _load_yaml(path: Path) -> Any:
    with open(path) as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"{path.name}: {str(e)}") from e


def _validate(data: Any, schema_path: Path) -> None:
    with open(schema_path) as f:
        schema = json.load(f)
    try:
        validate(data, schema)
    except JSONSchemaError as e:
        raise ValidationError(f"{schema_path.name}: {e.message}") from e


def load_snapshot(portfolio_dir: str) -> PortfolioSnapshot:
    p = Path(portfolio_dir)
    schemas = Path(__file__).parent.parent / "schemas"

    accounts_raw = _load_yaml(p / "accounts.yaml")
    _validate(accounts_raw, schemas / "accounts.schema.json")

    targets = _load_yaml(p / "targets.yaml")
    _validate(targets, schemas / "targets.schema.json")

    constraints = _load_yaml(p / "constraints.yaml")
    _validate(constraints, schemas / "constraints.schema.json")

    tax_rules_raw = _load_yaml(p / "tax-rules.yaml")
    _validate(tax_rules_raw, schemas / "tax-rules.schema.json")

    holdings_raw = _load_yaml(p / "holdings.yaml")
    _validate(holdings_raw, schemas / "holdings.schema.json")

    universes: dict[str, dict] = {}
    for m, fname in (("IN", "universe-in.yaml"), ("US", "universe-us.yaml")):
        u = _load_yaml(p / fname)
        _validate(u, schemas / "universe.schema.json")
        universes[m] = u

    accounts = [Account(**a) for a in accounts_raw["accounts"]]
    lots = [HoldingLot(**l) for l in holdings_raw["lots"]]

    return PortfolioSnapshot(
        as_of=holdings_raw["as_of"],
        fx_usdinr=holdings_raw["fx"]["USDINR"],
        accounts=accounts,
        lots=lots,
        targets=targets,
        constraints=constraints,
        tax_rules=tax_rules_raw["rules"],
        universes=universes,
    )
