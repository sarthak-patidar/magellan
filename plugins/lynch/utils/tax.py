"""Jurisdiction-aware tax classifier. Rules are data; no hardcoded brackets."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Union
import yaml


class NoMatchingRule(Exception):
    pass


@dataclass
class Classification:
    classification: str             # "STCG" | "LTCG"
    rate: Union[float, str]         # numeric or "slab"
    days_held: int
    days_to_ltcg: int               # 0 if already LTCG
    exemption_inr: Optional[float]
    rule_id: str


def load_rules(path: str) -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)["rules"]


def _match(rule: dict, market: str, instrument: str, residency: str) -> bool:
    m = rule["match"]
    return m["market"] == market and m["instrument"] == instrument and m["residency"] == residency


def classify(market: str, instrument: str, residency: str,
             entry_date: date, sell_date: date,
             rules: List[dict]) -> Classification:
    rule = next((r for r in rules if _match(r, market, instrument, residency)), None)
    if rule is None:
        raise NoMatchingRule(f"no rule for market={market} instrument={instrument} residency={residency}")

    days_held = (sell_date - entry_date).days
    ltcg_boundary = rule["ltcg"]["hold_gte_days"]

    if days_held >= ltcg_boundary:
        return Classification(
            classification="LTCG",
            rate=rule["ltcg"]["rate"],
            days_held=days_held,
            days_to_ltcg=0,
            exemption_inr=rule["ltcg"].get("exemption_inr"),
            rule_id=rule["id"],
        )
    return Classification(
        classification="STCG",
        rate=rule["stcg"]["rate"],
        days_held=days_held,
        days_to_ltcg=ltcg_boundary - days_held,
        exemption_inr=None,
        rule_id=rule["id"],
    )
