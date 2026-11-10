import pytest
from conftest import CONTRACT_KEYS

from chartis_proto import ai_portfolio

SEEDS = range(1, 11)


def test_contract():
    res = ai_portfolio.run()
    assert set(res) == CONTRACT_KEYS
    assert res["key"] == "ai_portfolio"
    assert len(res["table"]) >= 20
    assert res["soft_value_usd"] > 0


def test_deterministic():
    assert ai_portfolio.run(7) == ai_portfolio.run(7)


@pytest.mark.parametrize("seed", SEEDS)
def test_budget_respected(seed):
    res = ai_portfolio.run(seed)
    assert sum(r["year1_spend"] for r in res["table"]) <= ai_portfolio.YEAR1_BUDGET + 1


@pytest.mark.parametrize("seed", SEEDS)
def test_hard_value_positive_and_below_budget(seed):
    res = ai_portfolio.run(seed)
    assert 0 < res["annual_value_usd"] < ai_portfolio.YEAR1_BUDGET


@pytest.mark.parametrize("seed", SEEDS)
def test_gate_invariants(seed):
    cases, _ = ai_portfolio.select(ai_portfolio.evaluate(seed), seed=seed)
    for u in cases:
        if u["risk"] == "high" and u["evidence"] <= 2:
            assert u["decision"] == "Hold"
        if u["risk"] == "high" and u["evidence"] <= 3:
            assert u["decision"] != "Fund"
        if u["readiness"] <= ai_portfolio.MIN_READINESS:
            assert u["decision"] == "Hold"
        if u["decision"] == "Fund":
            assert u["npv"] > 0
        if u["decision"] == "Pilot":
            assert u["gross_benefit"] > 0
            assert u["decision_value"] > u["run_cost"]


def test_readiness_rule_reachable():
    reasons = {r["reason"] for r in ai_portfolio.run()["table"]}
    assert "Data not ready" in reasons


def test_ambient_counts_hours_not_revenue_lift():
    ambient = next(u for u in ai_portfolio.evaluate() if u["name"].startswith("Ambient"))
    assert ambient["revenue"] == 0
    assert ambient["soft_benefit"] > ambient["hard_benefit"]


def test_overlap_tags_present():
    table = ai_portfolio.run()["table"]
    assert {"denials", "patient_flow", "workforce"} <= {r["overlaps_module"] for r in table}
