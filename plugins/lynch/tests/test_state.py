from utils.state import load_snapshot, ValidationError
import pytest
import os
import shutil
from pathlib import Path


def test_loads_valid_state():
    snap = load_snapshot("tests/fixtures/portfolio")
    assert len(snap.accounts) == 3
    assert len(snap.lots) == 2
    assert snap.fx_usdinr == 83.42
    assert {l.symbol for l in snap.lots} == {"RELIANCE.NS", "NVDA"}


def test_fails_loudly_on_missing_entry_date():
    # copy fixture dir and mutate holdings.yaml to drop entry_date on one lot
    tmp_path = Path("/tmp") / f"test-{os.getpid()}"
    try:
        shutil.copytree("tests/fixtures/portfolio", tmp_path / "p")
        bad = (tmp_path / "p" / "holdings.yaml").read_text().replace('entry_date: "2025-01-10"\n', "")
        (tmp_path / "p" / "holdings.yaml").write_text(bad)
        try:
            load_snapshot(str(tmp_path / "p"))
            assert False, "Expected ValidationError"
        except ValidationError:
            pass
    finally:
        shutil.rmtree(tmp_path)
