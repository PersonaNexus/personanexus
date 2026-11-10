import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chartis_proto import rural  # noqa: E402

KEYS = {"key", "problem", "question", "headline_metrics", "annual_value_usd", "value_basis",
        "assumptions", "table_title", "table", "details", "synthetic_data"}


def test_contract():
    r = rural.run()
    assert KEYS <= set(r)
    assert r["key"] == "rural" and r["synthetic_data"] is True
    assert len(r["table"]) == 15 and r["assumptions"] == rural.ASSUMPTIONS


def test_deterministic():
    assert rural.run(7) == rural.run(7)
    assert rural.run(7) != rural.run(8)


def test_ranges():
    r = rural.run()
    assert 0 < r["annual_value_usd"] < 1e8
    assert abs(sum(rural.WEIGHTS.values()) - 1.0) < 1e-9
    for row in r["table"]:
        assert 0 <= row["score_shock"] <= 100
    scores = [row["score_shock"] for row in r["table"]]
    assert scores == sorted(scores, reverse=True)


def test_shock_never_improves_margin():
    h = {"npr": 20e6, "op_margin": 0.01, "medicaid_pct": 0.25, "selfpay_pct": 0.05,
         "outpatient_heavy": True, "days_cash": 60, "births": 0, "miles_to_next": 40,
         "beds": 20, "adc": 4}
    s = rural.apply_scenario(h, medicaid_cut=0.1, site_neutral=True)
    assert s["op_margin"] < h["op_margin"] and s["annual_delta_usd"] < 0
    assert rural.score(s) >= rural.score(h)


def test_reh_conversion_helps_tiny_hospital():
    h = {"npr": 12e6, "op_margin": -0.08, "medicaid_pct": 0.2, "selfpay_pct": 0.05,
         "outpatient_heavy": False, "days_cash": 30, "births": 0, "miles_to_next": 40,
         "beds": 15, "adc": 2}
    assert rural.reh_eligible(h)
    assert rural.apply_scenario(h, convert_reh=True)["annual_delta_usd"] > 0
