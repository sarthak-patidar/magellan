# tests/test_amfi_nav.py
from utils.amfi_nav import parse_amfi_nav_file


def test_parse_amfi_nav_snippet(tmp_path):
    # AMFI daily NAV file format (subset):
    content = """Open Ended Schemes(Equity Scheme - Large Cap Fund)
;;;;;
Axis Mutual Fund
;;;;;
Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
120505;INF846K01EW2;;Axis Bluechip Fund - Direct Plan - Growth;67.1234;19-Apr-2026
"""
    f = tmp_path / "nav.txt"
    f.write_text(content)
    navs = parse_amfi_nav_file(str(f))
    assert "INF846K01EW2" in navs
    assert navs["INF846K01EW2"]["nav"] == 67.1234
    assert navs["INF846K01EW2"]["scheme_name"].startswith("Axis Bluechip")
