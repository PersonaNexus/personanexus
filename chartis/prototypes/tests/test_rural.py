import itertools

import pytest

from chartis_proto import common, rural

from conftest import CONTRACT_KEYS


def test_contract():
    r = rural.run()
    assert set(r) == CONTRACT_KEYS
    assert r["key"] == "rural" and r["synthetic_data"] is True
    assert len(r["table"]) == 15 and r["assumptions"] == rural.ASSUMPTIONS
    assert r["soft_value_usd"] == 0.0


def test_deterministic():
    assert rural.run(7) == rural.run(7)
    assert rural.run(7) != rural.run(8)


def test_ranges():
    r = rural.run()
    assert 0 < r["annual_value_usd"] < 1e8
    assert abs(sum(rural.WEIGHTS.values()) - 1.0) < 1e-9
    for row in r["table"]:
        assert 0 <= row["score_shock"] <= 100
        assert row["protects_access"] == "Yes"
    scores = [row["score_shock"] for row in r["table"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("seed", range(1, 11))
def test_seed_sweep_value_derived_from_options(seed):
    r = rural.run(seed)
    full = r["details"]["client_option_value_full"]
    assert full > 0
    assert r["annual_value_usd"] == pytest.approx(full * rural.REALIZATION, rel=1e-6, abs=1)
    # 20-hospital client value stays modest: < $1M per hospital per year
    assert 0 < r["annual_value_usd"] < rural.TOP_N_CLIENT * 1e6


def test_reh_post_conversion_margin_bounded_across_seeds():
    n = 0
    for seed in range(1, 21):
        g = common.rng(seed)
        for i in range(120):
            h = rural.apply_scenario(
                rural._hospital(g, i), medicaid_cut=rural.MEDICAID_CUT, site_neutral=True
            )
            if rural.reh_eligible(h):
                n += 1
                assert rural.apply_scenario(h, convert_reh=True)["op_margin"] <= 0.12
    assert n > 50


def test_documented_constants():
    text = " ".join(rural.ASSUMPTIONS)
    assert rural.OB_LINKED_REVENUE_SHARE == 0.08 and "8% of NPR" in text
    assert rural.OB_LINKED_REVENUE_CAP == 1.0e6 and "$1M" in text
    assert rural.REALIZATION == 0.15 and "15%" in text
    assert "PROXY" in text and "2027-28" in text


def test_shock_never_improves_margin():
    h = {
        "npr": 20e6,
        "op_margin": 0.01,
        "medicaid_pct": 0.25,
        "selfpay_pct": 0.05,
        "outpatient_heavy": True,
        "days_cash": 60,
        "births": 0,
        "miles_to_next": 40,
        "beds": 20,
        "adc": 4,
        "cah": True,
    }
    s = rural.apply_scenario(h, medicaid_cut=0.1, site_neutral=True)
    assert s["op_margin"] < h["op_margin"] and s["annual_delta_usd"] < 0
    assert rural.score(s) >= rural.score(h)


def test_reh_conversion_helps_tiny_hospital():
    h = {
        "npr": 12e6,
        "op_margin": -0.08,
        "medicaid_pct": 0.2,
        "selfpay_pct": 0.05,
        "outpatient_heavy": False,
        "days_cash": 30,
        "births": 0,
        "miles_to_next": 40,
        "beds": 15,
        "adc": 2,
        "cah": True,
    }
    assert rural.reh_eligible(h)
    assert rural.apply_scenario(h, convert_reh=True)["annual_delta_usd"] > 0
    assert not rural.reh_eligible({**h, "op_margin": 0.03})  # healthy: not a candidate


def test_isolated_ob_closure_is_never_recommended():
    for miles, births in itertools.product((10, 50), (120,)):
        h = {
            "npr": 15e6,
            "op_margin": -0.05,
            "medicaid_pct": 0.25,
            "selfpay_pct": 0.05,
            "outpatient_heavy": False,
            "days_cash": 30,
            "births": births,
            "miles_to_next": miles,
            "beds": 60,
            "adc": 20,
            "cah": False,
        }
        name, best, rejected = rural.best_option(h)
        if miles > rural.ACCESS_MILES:
            assert "Consolidate OB (low volume)" in rejected and not best["access_loss"]
        else:
            assert rejected == []
