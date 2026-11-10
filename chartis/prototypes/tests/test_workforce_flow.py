import pytest

from chartis_proto import patient_flow, workforce

from conftest import CONTRACT_KEYS


@pytest.mark.parametrize("mod", [workforce, patient_flow])
def test_contract_and_determinism(mod):
    a, b = mod.run(seed=7), mod.run(seed=7)
    assert set(a) == CONTRACT_KEYS
    assert a == b
    assert a["synthetic_data"] is True
    assert a["table"] and a["assumptions"]
    assert all({"label", "value", "unit", "display"} <= set(m) for m in a["headline_metrics"])


@pytest.mark.parametrize("seed", range(1, 11))
def test_workforce_seed_sweep(seed):
    r = workforce.run(seed)
    m = {x["label"].split(" (")[0]: x["value"] for x in r["headline_metrics"]}
    assert 0 < m["Census forecast error"] < 15
    assert m["Turnover: top-risk decile vs overall"] > 1.5
    # calibrated to ~16.4% turnover (sampling noise allowed)
    assert 0.11 < r["details"]["overall_turnover_rate"] < 0.22
    baseline = sum(u["annual_cost_baseline"] for u in r["table"])
    assert 0 < r["annual_value_usd"] / baseline < 0.10  # modest share of RN labor


def test_workforce_core_quantile_is_newsvendor():
    assert 0 < workforce.CORE_QUANTILE < 1
    assert workforce.STAFF_RATE < workforce._GAP_RATE


@pytest.mark.parametrize("seed", range(1, 11))
def test_patient_flow_seed_sweep(seed):
    r = patient_flow.run(seed)
    m = {x["label"]: x["value"] for x in r["headline_metrics"]}
    assert 80 < m["Occupancy (modeled)"] < 95
    assert 0 < m["Staffed beds released"] < 50  # < 10% of a 500-bed hospital
    assert m["Admission-time delay model AUC"] > 0.55
    assert m["Days freed by playbook / yr"] < m["Excess days / yr"]
    assert r["annual_value_usd"] > 0 and r["soft_value_usd"] >= 0
    hard = sum(x["hard_value_yr"] for x in r["table"])
    assert abs(hard - r["annual_value_usd"]) / r["annual_value_usd"] < 0.001  # rounding only
    # attributed + unexplained never exceeds total excess
    attributed = sum(x["excess_days_yr"] for x in r["table"])
    assert attributed + r["details"]["unexplained_excess_days_yr"] <= m["Excess days / yr"] + 5


def test_auc_matches_bruteforce():
    import random

    rr = random.Random(0)
    s = [round(rr.random(), 1) for _ in range(200)]
    y = [rr.random() < 0.3 + 0.4 * v for v in s]
    pos = [a for a, b in zip(s, y) if b]
    neg = [a for a, b in zip(s, y) if not b]
    brute = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
    assert abs(patient_flow._auc(s, y) - brute) < 1e-9
