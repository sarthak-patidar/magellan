import pytest
from datetime import date
from utils.tax import classify, load_rules, NoMatchingRule


@pytest.fixture
def rules():
    return load_rules("tests/fixtures/tax-rules.yaml")


def test_in_equity_short_term(rules):
    r = classify(
        market="IN", instrument="equity", residency="IN",
        entry_date=date(2025, 10, 1), sell_date=date(2026, 4, 1),
        rules=rules,
    )
    assert r.classification == "STCG"
    assert r.rate == 0.20
    assert r.days_to_ltcg == 365 - (date(2026, 4, 1) - date(2025, 10, 1)).days


def test_in_equity_long_term(rules):
    r = classify(
        market="IN", instrument="equity", residency="IN",
        entry_date=date(2024, 1, 1), sell_date=date(2026, 2, 1),
        rules=rules,
    )
    assert r.classification == "LTCG"
    assert r.rate == 0.125
    assert r.exemption_inr == 125000


def test_us_equity_for_in_resident_needs_24_months(rules):
    # 18 months — still STCG under Indian unlisted-foreign-equity treatment
    r = classify(
        market="US", instrument="equity", residency="IN",
        entry_date=date(2024, 10, 1), sell_date=date(2026, 4, 1),
        rules=rules,
    )
    assert r.classification == "STCG"
    assert r.rate == "slab"

    # 25 months — LTCG
    r2 = classify(
        market="US", instrument="equity", residency="IN",
        entry_date=date(2023, 12, 1), sell_date=date(2026, 1, 1),
        rules=rules,
    )
    assert r2.classification == "LTCG"
    assert r2.rate == 0.125


def test_no_matching_rule_fails_loudly(rules):
    with pytest.raises(NoMatchingRule):
        classify(
            market="US", instrument="equity", residency="US",
            entry_date=date(2024, 1, 1), sell_date=date(2026, 4, 1),
            rules=rules,
        )
