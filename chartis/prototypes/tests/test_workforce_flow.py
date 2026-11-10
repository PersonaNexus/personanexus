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


def test_workforce_ranges():
    r = workforce.run()
    m = {x["label"]: x["value"] for x in r["headline_metrics"]}
    assert 0 < m["Census forecast error (MAPE, 4-wk)"] < 20
    assert m["Agency hours avoided / yr"] > 0
    assert m["Turnover: top-risk decile vs overall"] > 1.2
    # savings should be a modest share of total RN labor, not fantasy
    reactive = sum(u["annual_cost_reactive"] for u in r["table"])
    assert 0 < r["annual_value_usd"] / reactive < 0.25


def test_patient_flow_ranges():
    r = patient_flow.run()
    m = {x["label"]: x["value"] for x in r["headline_metrics"]}
    assert 0 < m["Staffed beds released"] < 50  # < 10% of a 500-bed hospital
    assert m["Admission-time delay model AUC"] > 0.55
    assert m["Days freed by playbook / yr"] < m["Excess days / yr"]
    assert abs(sum(x["value_yr"] for x in r["table"]) - r["annual_value_usd"]) / r["annual_value_usd"] < 0.01
