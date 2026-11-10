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
    standalone = ai_portfolio.run(42)["annual_value_usd"] * k
    assert ai_line["hard_value_usd"] == pytest.approx(standalone - b["overlap_removed_usd"], abs=2)


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
    html = d.read_text()
    assert "/*__DATA__*/null" not in html and '"bundle"' in html
    assert "One-client value ledger" in capsys.readouterr().out


def test_cli_fast_skips_analysis(tmp_path):
    j = tmp_path / "r.json"
    assert main(["workforce", "--fast", "--json", str(j)]) == 0
    data = json.loads(j.read_text())
    assert data["bundle"] is None and "range" not in data["results"][0]
