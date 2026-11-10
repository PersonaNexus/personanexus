import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chartis_proto import denials  # noqa: E402


def _m(r, label):
    return next(m["value"] for m in r["headline_metrics"] if m["label"] == label)


def test_contract():
    r = denials.run()
    assert r["key"] == "denials" and r["synthetic_data"] is True
    assert len(r["table"]) == 20 and r["assumptions"] == denials.ASSUMPTIONS


def test_deterministic():
    assert denials.run(3) == denials.run(3)


def test_ranges():
    r = denials.run()
    assert 6 <= _m(r, "Initial denial rate") <= 16
    assert _m(r, "Model AUC") > 0.6
    assert 0 < r["annual_value_usd"] < 5e7  # < 5% of a $1B system
    d = r["details"]["denial_rate_by_payer_pct"]
    assert d["Medicare Advantage"] > d["Traditional Medicare"]


def test_auc_helper():
    assert denials.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == 1.0
    assert denials.auc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) == 0.0
    assert denials.auc([0.5, 0.5], [0, 1]) == 0.5


def test_missing_auth_raises_risk():
    base = {"payer": "Commercial", "auth_required": True, "auth_obtained": True,
            "eligibility_verified": True, "doc_completeness": 1.0, "coding_complexity": 1,
            "days_to_submit": 3}
    assert denials.predict({**base, "auth_obtained": False}) > denials.predict(base)
