import pytest

from chartis_proto import denials

from conftest import CONTRACT_KEYS


def _m(r, label):
    return next(m["value"] for m in r["headline_metrics"] if m["label"] == label)


def test_contract():
    r = denials.run()
    assert set(r) == CONTRACT_KEYS
    assert r["key"] == "denials" and r["synthetic_data"] is True
    assert len(r["table"]) == 20 and r["assumptions"] == denials.ASSUMPTIONS
    assert r["soft_value_usd"] == 0.0


def test_deterministic():
    assert denials.run(3) == denials.run(3)


def test_ranges():
    r = denials.run()
    assert 6 <= _m(r, "Initial denial rate") <= 16
    assert _m(r, "Model AUC") > 0.6
    d = r["details"]["denial_rate_by_payer_pct"]
    assert d["Medicare Advantage"] > d["Traditional Medicare"]


@pytest.mark.parametrize("seed", range(1, 11))
def test_seed_sweep_value_share_of_npr(seed):
    r = denials.run(seed)
    pct = r["details"]["value_pct_of_npr"]
    assert 0.25 <= pct <= 0.8  # target band ~0.4-0.7% of NPR
    assert r["annual_value_usd"] == pytest.approx(
        r["details"]["gross_value_before_partner_cost"] - denials.PARTNER_COST, abs=1
    )
    assert _m(r, "Model AUC") > 0.6


def test_documented_constants():
    assert denials.WRITE_OFF_SHARE == 0.22
    assert denials.FIX_SUCCESS["Authorization / precert"] == 0.30
    assert denials.FIX_SUCCESS["Coding"] == 0.65
    assert denials.FIX_SUCCESS["Medical necessity / documentation"] == 0.65
    assert denials.FIX_SUCCESS["Eligibility / registration"] == 0.75
    assert set(denials.FIX_SUCCESS) == set(denials.ROOT_CAUSE_LABEL.values())
    assert denials.BACKEND_REWORK_MULTIPLIER == 2.0 and denials.PARTNER_COST == 750_000
    text = " ".join(denials.ASSUMPTIONS)
    assert "22%" in text and "2x" in text and "$750K" in text


def test_auc_helper():
    assert denials.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == 1.0
    assert denials.auc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) == 0.0
    assert denials.auc([0.5, 0.5], [0, 1]) == 0.5


def test_missing_auth_raises_risk():
    base = {
        "payer": "Commercial",
        "auth_required": True,
        "auth_obtained": True,
        "eligibility_verified": True,
        "doc_completeness": 1.0,
        "coding_complexity": 1,
        "days_to_submit": 3,
    }
    assert denials.predict({**base, "auth_obtained": False}) > denials.predict(base)
