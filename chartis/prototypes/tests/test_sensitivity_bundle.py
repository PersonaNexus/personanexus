import json

import pytest

from chartis_proto import MODULES, bundle, sensitivity, workforce
from chartis_proto.__main__ import main


def test_percentiles():
    assert sensitivity.summarize(range(1, 12)) == {"p10": 2, "p50": 6, "p90": 10}
    assert sensitivity.summarize([5]) == {"p10": 5, "p50": 5, "p90": 5}


def test_patched_restores_and_caps_shares():
    base = workforce.FLOAT_UTILIZATION
    with sensitivity.patched(workforce, "FLOAT_UTILIZATION", 1.3):
        assert workforce.FLOAT_UTILIZATION == 0.99  # share capped below 1
    assert workforce.FLOAT_UTILIZATION == base
    with pytest.raises(RuntimeError):
        with sensitivity.patched(workforce, "AGENCY_RATE", 2.0):
            raise RuntimeError
    assert workforce.AGENCY_RATE == 105.0  # restored even on error


@pytest.mark.parametrize("name", MODULES)
def test_analyze_module(name):
    out = sensitivity.analyze(name, seeds=range(1, 6))
    h = out["range"]["hard"]
    assert h["p10"] <= h["p50"] <= h["p90"]
    assert out["tornado"], "every module lists sensitivity assumptions"
    spreads = [t["spread"] for t in out["tornado"]]
    assert spreads == sorted(spreads, reverse=True)
    assert max(spreads) > 0  # at least one assumption moves the answer
    # patching must not leak: a fresh run still equals the recorded base
    mod = __import__(f"chartis_proto.{name}", fromlist=["run"])
    assert round(mod.run(42)["annual_value_usd"]) == out["tornado"][0]["base"]


def test_scale_multiplier_is_not_capped_like_a_share():
    from chartis_proto import patient_flow

    with sensitivity.patched(patient_flow, "EFFECT_SCALE", 1.3):
        assert patient_flow.EFFECT_SCALE == pytest.approx(1.3)
    rows = {t["attr"]: t for t in sensitivity.tornado(patient_flow)}
    assert rows["EFFECT_SCALE"]["low"] < rows["EFFECT_SCALE"]["base"] < rows["EFFECT_SCALE"]["high"]


def test_sourced_low_high_values_are_used():
    spec = {s["attr"]: s for s in sensitivity.specs(workforce)}
    assert spec["AGENCY_RATE"]["low_value"] == 90.54 and spec["AGENCY_RATE"]["low_at"] == "90.54"
    assert spec["REPLACEMENT_COST"]["low_at"] == "-30%"


def test_staff_rate_patch_reprices_overtime():
    """Overtime is derived from the staff rate at call time, not frozen at import."""
    base = workforce.gap_rate()
    with sensitivity.patched_value(workforce, "STAFF_RATE", 94.0):
        assert workforce.gap_rate() > base


def test_every_listed_assumption_moves_hard_value():
    for name in MODULES:
        for t in sensitivity.analyze(name, seeds=[1])["tornado"]:
            assert t["spread"] > 0, (name, t["assumption"])


def test_top_drivers_restore_and_bracket_the_ledger():
    before = {
        n: sensitivity.tornado(__import__(f"chartis_proto.{n}", fromlist=["x"]))[0] for n in MODULES
    }
    ar = bundle.assumption_range(42)
    mid = bundle.ledger(42)["hard_total_usd"]
    assert ar["low"]["hard_total_usd"] < mid < ar["high"]["hard_total_usd"]
    after = {
        n: sensitivity.tornado(__import__(f"chartis_proto.{n}", fromlist=["x"]))[0] for n in MODULES
    }
    assert before == after  # nothing left patched


def test_workforce_value_depends_on_agency_premium():
    """The review's key finding: no agency premium, no scheduling savings."""
    rows = {t["attr"]: t for t in sensitivity.tornado(workforce)}
    assert rows["AGENCY_RATE"]["low"] < rows["AGENCY_RATE"]["base"] < rows["AGENCY_RATE"]["high"]


@pytest.mark.parametrize("seed", range(1, 6))
def test_bundle_ledger(seed):
    b = bundle.ledger(seed)
    assert [ln["key"] for ln in b["lines"]] == MODULES
    assert b["hard_total_usd"] == pytest.approx(
        sum(ln["hard_value_usd"] for ln in b["lines"]), abs=len(MODULES)
    )
    assert b["overlap_removed_usd"] >= 0
    assert b["supportable_annual_fees_usd"] == pytest.approx(b["hard_total_usd"] / 5, abs=1)
    # bundle hard value stays a small share of the client's revenue
    assert 0 < b["hard_total_usd"] / b["client"]["net_patient_revenue"] < 0.015


def test_bundle_removes_overlap_from_ai_line():
    from chartis_proto import ai_portfolio

    b = bundle.ledger(42)
    k = bundle.CLIENT["net_patient_revenue"] / bundle.AI_MODEL_NPR
    ai_line = next(ln for ln in b["lines"] if ln["key"] == "ai_portfolio")
    a = ai_portfolio.run(42)
    fixed = a["details"]["amortized_one_time_annual"]  # one-time costs do not scale down
    standalone = (a["annual_value_usd"] + fixed) * k - fixed
    assert ai_line["hard_value_usd"] == pytest.approx(standalone - b["overlap_removed_usd"], abs=2)
    assert b["overlap_removed_usd"] > 0


def test_bundle_scales_with_client():
    bigger = dict(bundle.CLIENT, net_patient_revenue=4.0e9)
    assert bundle.ledger(42, bigger)["hard_total_usd"] > bundle.ledger(42)["hard_total_usd"]


def test_cli_writes_json_and_dashboard(tmp_path, capsys):
    j, d = tmp_path / "r.json", tmp_path / "d.html"
    assert main(["--json", str(j), "--dashboard", str(d)]) == 0
    data = json.loads(j.read_text())
    assert [r["key"] for r in data["results"]] == MODULES
    assert all("range" in r and "tornado" in r for r in data["results"])
    assert data["bundle"]["range"]["hard_total"]["p50"] > 0
    assert set(data["bundle"]["assumption_range"]) == {"low", "high"}
    html = d.read_text()
    assert "/*__DATA__*/null" not in html and '"bundle"' in html
    assert "One-client value ledger" in capsys.readouterr().out


def test_cli_fast_skips_analysis(tmp_path):
    j = tmp_path / "r.json"
    assert main(["workforce", "--fast", "--json", str(j)]) == 0
    data = json.loads(j.read_text())
    assert data["bundle"] is None and "range" not in data["results"][0]
