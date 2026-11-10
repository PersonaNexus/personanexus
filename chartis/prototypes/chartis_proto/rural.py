"""Rural hospital financial vulnerability & service-line scenario planner.

Method
------
1. Generate ~120 synthetic rural hospitals with realistic-looking attributes
   (beds, payer mix, operating margin, days cash on hand, births, ED visits,
   distance to the next hospital, Critical Access Hospital flag).
2. Score each with the **Transparent Rural Vulnerability Score** (0-100,
   higher = more vulnerable). It is a simple weighted sum of normalized
   drivers whose weights are published in ``WEIGHTS``. It is NOT, and does not
   attempt to replicate, any proprietary index (including Chartis' INDEX).
3. Apply policy / strategy scenarios (Medicaid revenue cut, 340B / site-neutral
   change, OB closure, Rural Emergency Hospital conversion), recompute margin
   and score, and report hospitals that cross the "at risk" threshold.

ALL DATA IS SYNTHETIC.
"""
from __future__ import annotations

from .common import clamp, metric, result, rng, usd

STATES = ["KS", "TX", "GA", "MS", "OK", "TN", "MO", "NE", "IA", "AL", "MN", "MT"]
AT_RISK = 60.0  # score threshold for "at risk"

# Weights for the Transparent Rural Vulnerability Score (sum = 1.0).
WEIGHTS = {
    "negative_margin": 0.30,   # operating margin, -10% -> 1.0, +5% -> 0.0
    "low_cash": 0.25,          # days cash on hand, 0 -> 1.0, 150+ -> 0.0
    "medicaid_uninsured": 0.15,  # Medicaid + self-pay share, 10% -> 0, 45% -> 1
    "low_volume": 0.15,        # average daily census, 2 -> 1.0, 25+ -> 0.0
    "isolation": 0.15,         # distance to next hospital: closure = access loss
}

ASSUMPTIONS = [
    "All 120 hospitals are synthetic; distributions loosely shaped to published rural hospital data (median margin near break-even, many with <60 days cash).",
    "Transparent Rural Vulnerability Score is an illustrative weighted model (weights published in code); it is not Chartis' proprietary INDEX.",
    "Medicaid revenue shock = % reduction applied to Medicaid share of net patient revenue (proxy for 2025 federal Medicaid changes).",
    "340B / site-neutral shock = 2% of net patient revenue for hospitals with outpatient-heavy mix.",
    "OB closure saves ~$1.2M/yr direct cost for units < 200 births but loses ~25% of OB-linked downstream revenue; flagged as access loss if next hospital > 30 miles.",
    "Rural Emergency Hospital (REH) conversion: eligible if <= 50 beds and ADC < 5; adds ~$3.3M/yr facility payment (2025 approx.) + 5% OPPS uplift and drops inpatient revenue/cost.",
    "Reference client = system/association with 20 rural hospitals; recommended strategies capture 35% of modeled scenario losses (assumption, to validate in pilot).",
]


def _hospital(r, i: int) -> dict:
    cah = r.random() < 0.6
    beds = r.randint(10, 25) if cah else r.randint(26, 120)
    adc = clamp(r.gauss(beds * 0.35, beds * 0.12), 0.5, beds * 0.9)
    npr = (beds * 0.55e6 + adc * 0.9e6) * r.uniform(0.8, 1.25)  # net patient revenue
    medicaid = clamp(r.gauss(0.20, 0.07), 0.05, 0.45)
    selfpay = clamp(r.gauss(0.08, 0.03), 0.01, 0.2)
    margin = r.gauss(-0.01, 0.07)
    births = 0 if r.random() < 0.45 else int(r.uniform(40, 600))
    return {
        "id": f"RH-{i:03d}",
        "state": r.choice(STATES),
        "beds": beds,
        "adc": round(adc, 1),
        "cah": cah,
        "npr": npr,
        "medicaid_pct": medicaid,
        "selfpay_pct": selfpay,
        "op_margin": margin,
        "days_cash": max(0.0, r.gauss(90, 60)),
        "births": births,
        "ed_visits": int(r.uniform(2500, 18000)),
        "miles_to_next": round(r.uniform(8, 85), 1),
        "outpatient_heavy": r.random() < 0.5,
    }


def _norm(x: float, worst: float, best: float) -> float:
    return clamp((x - best) / (worst - best))


def drivers(h: dict) -> dict:
    return {
        "negative_margin": _norm(h["op_margin"], -0.10, 0.05),
        "low_cash": _norm(h["days_cash"], 0, 150),
        "medicaid_uninsured": _norm(h["medicaid_pct"] + h["selfpay_pct"], 0.45, 0.10),
        "low_volume": _norm(h["adc"], 2, 25),
        "isolation": _norm(h["miles_to_next"], 60, 10),
    }


def score(h: dict) -> float:
    d = drivers(h)
    return round(100 * sum(WEIGHTS[k] * d[k] for k in WEIGHTS), 1)


def reh_eligible(h: dict) -> bool:
    return h["beds"] <= 50 and h["adc"] < 5


def apply_scenario(h: dict, medicaid_cut: float = 0.0, site_neutral: bool = False,
                   close_ob: bool = False, convert_reh: bool = False) -> dict:
    """Return a copy of hospital ``h`` with margin/cash recomputed under shocks."""
    s = dict(h)
    npr = h["npr"]
    expenses = npr * (1 - h["op_margin"])
    revenue = npr
    revenue -= npr * h["medicaid_pct"] * medicaid_cut
    if site_neutral and h["outpatient_heavy"]:
        revenue -= npr * 0.02
    if close_ob and 0 < h["births"] < 200:
        expenses -= 1.2e6
        revenue -= min(npr * 0.25 * 0.08, 1.0e6)  # lost OB-linked downstream revenue
        s["ob_access_loss"] = h["miles_to_next"] > 30
    if convert_reh and reh_eligible(h):
        inpatient_rev = npr * 0.35
        revenue += -inpatient_rev + 3.3e6 + (npr - inpatient_rev) * 0.05
        expenses -= inpatient_rev * 0.9
        s["adc"] = 0.5
    s["op_margin"] = (revenue - expenses) / revenue
    s["npr"] = revenue
    s["annual_delta_usd"] = (revenue - expenses) - npr * h["op_margin"]
    # cash erodes by one year of incremental loss, expressed in days of expense
    s["days_cash"] = max(0.0, h["days_cash"] + s["annual_delta_usd"] / (expenses / 365))
    return s


def run(seed: int = 42) -> dict:
    r = rng(seed)
    hospitals = [_hospital(r, i) for i in range(1, 121)]
    for h in hospitals:
        h["score"] = score(h)

    # Policy shock: 10% Medicaid revenue cut + site-neutral change.
    shocked = [apply_scenario(h, medicaid_cut=0.10, site_neutral=True) for h in hospitals]
    for s in shocked:
        s["score"] = score(s)
    newly_at_risk = [s for h, s in zip(hospitals, shocked) if h["score"] < AT_RISK <= s["score"]]
    shock_loss = -sum(min(0.0, s["annual_delta_usd"]) for s in shocked)

    # Strategy options for at-risk hospitals under the shock.
    strategies = []
    for s in shocked:
        if s["score"] < AT_RISK:
            continue
        options = {
            "Close OB (low volume)": apply_scenario(s, close_ob=True),
            "Convert to REH": apply_scenario(s, convert_reh=True),
        }
        best_name, best = max(options.items(), key=lambda kv: kv[1]["annual_delta_usd"])
        if best["annual_delta_usd"] > 50_000:
            strategies.append((s, best_name, best))

    at_risk_now = [h for h in hospitals if h["score"] >= AT_RISK]
    top = sorted(shocked, key=lambda s: -s["score"])[:15]
    strat_by_id = {s["id"]: (name, b) for s, name, b in strategies}
    table = []
    for s in top:
        d = drivers(s)
        main = sorted(d, key=lambda k: -WEIGHTS[k] * d[k])[:2]
        name, b = strat_by_id.get(s["id"], ("Operational improvement", None))
        table.append({
            "hospital": s["id"], "state": s["state"], "beds": s["beds"],
            "cah": "Y" if s["cah"] else "N",
            "score_base": next(h["score"] for h in hospitals if h["id"] == s["id"]),
            "score_shock": s["score"],
            "op_margin_shock": f"{s['op_margin'] * 100:.1f}%",
            "days_cash_shock": round(s["days_cash"]),
            "top_drivers": ", ".join(main),
            "suggested_option": name,
            "option_value": usd(b["annual_delta_usd"]) if b else "-",
        })

    # Reference client: 20 rural hospitals => scale per-hospital loss.
    per_hosp_loss = shock_loss / len(hospitals)
    capture = 0.35
    annual_value = per_hosp_loss * 20 * capture
    strategy_gain = sum(b["annual_delta_usd"] for _, _, b in strategies)

    return result(
        key="rural",
        problem="Rural hospital financial distress, closures & service-line loss",
        question="Which rural hospitals tip into distress under policy shocks, and which strategic option (OB consolidation, REH conversion, ops) protects access?",
        headline_metrics=[
            metric("Hospitals modeled", len(hospitals)),
            metric("At risk today (score >= 60)", len(at_risk_now)),
            metric("Newly at risk after shock", len(newly_at_risk)),
            metric("Annual shock loss (portfolio)", shock_loss, "usd"),
            metric("Hospitals with a margin-positive option", len(strategies)),
            metric("Modeled strategy gain", strategy_gain, "usd"),
        ],
        annual_value_usd=annual_value,
        value_basis=(f"Average modeled shock loss {usd(per_hosp_loss)}/hospital x 20 hospitals "
                     f"x {capture:.0%} avoided via recommended strategies (assumption)."),
        assumptions=ASSUMPTIONS,
        table_title="Top 15 most vulnerable hospitals after 10% Medicaid cut + site-neutral shock",
        table=table,
        details={
            "weights": WEIGHTS,
            "at_risk_threshold": AT_RISK,
            "scenario": {"medicaid_cut": 0.10, "site_neutral": True},
            "newly_at_risk_ids": [s["id"] for s in newly_at_risk],
            "reh_eligible_count": sum(reh_eligible(h) for h in hospitals),
            "ob_units": sum(1 for h in hospitals if h["births"] > 0),
        },
    )
