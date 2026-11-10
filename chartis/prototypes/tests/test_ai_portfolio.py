import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chartis_proto import ai_portfolio  # noqa: E402

KEYS = {"key", "problem", "question", "headline_metrics", "annual_value_usd", "value_basis",
        "assumptions", "table_title", "table", "details", "synthetic_data"}


def test_contract():
    res = ai_portfolio.run()
    assert KEYS <= res.keys()
    assert res["key"] == "ai_portfolio"
    assert len(res["table"]) >= 20
    assert res["annual_value_usd"] > 0


def test_deterministic():
    assert ai_portfolio.run(7) == ai_portfolio.run(7)


def test_budget_respected():
    for seed in range(5):
        res = ai_portfolio.run(seed)
        assert sum(r["year1_spend"] for r in res["table"]) <= ai_portfolio.YEAR1_BUDGET + 1


def test_high_risk_weak_evidence_never_funded():
    for seed in range(5):
        for r in ai_portfolio.run(seed)["table"]:
            if r["risk"] == "high" and r["evidence"] <= 3:
                assert r["decision"] != "Fund"
