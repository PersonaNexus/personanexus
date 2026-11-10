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

# --- Named scenario / strategy constants (all assumptions; see ASSUMPTIONS) ---
MEDICAID_CUT = 0.10            # share of Medicaid revenue lost, fully phased in
SITE_NEUTRAL_SHARE = 0.02      # share of NPR lost for outpatient-heavy hospitals
OB_DIRECT_COST_SAVED = 1.2e6   # direct annual cost of a low-volume OB unit
OB_LOW_VOLUME_BIRTHS = 200     # units below this are candidates for consolidation
OB_LINKED_REVENUE_SHARE = 0.08  # share of NPR linked to OB (deliveries, peds, GYN)
OB_LINKED_REVENUE_LOST = 0.25  # share of OB-linked revenue lost when OB closes
OB_LINKED_REVENUE_CAP = 1.0e6  # cap on that annual loss
ACCESS_MILES = 30.0            # closing a service beyond this distance = access loss
REH_FACILITY_PAYMENT = 3.4e6   # annual REH facility payment (approx. 2025-26)
REH_OPPS_UPLIFT = 0.05         # +5% on Medicare OPPS-paid outpatient services
MEDICARE_OP_SHARE = 0.40       # Medicare share of outpatient revenue
CAH_COST_BASED_LOSS = 0.10     # CAH loses cost-based (101% of cost) Medicare OP pay
IP_COST_INTENSITY = 1.10       # inpatient share of cost vs its share of revenue
IP_COST_AVOIDABLE = 0.40       # share of inpatient cost actually removed (rest fixed)
REH_ADDED_COST = 0.75e6        # transfer agreements, 24/7 ED staffing, transport
REH_LOST_OTHER_REVENUE = 0.06  # swing-bed and 340B revenue lost on conversion (share of NPR)
REH_MARGIN_CEILING = 0.10      # sanity bound on post-conversion margin
REH_MAX_ADC = 5.0              # eligibility proxy: average daily census below this
OPS_IMPROVEMENT = 0.015        # expense reduction from operational improvement
REALIZATION = 0.15             # share of modeled option value actually realized
TOP_N_CLIENT = 20              # reference client: 20 most vulnerable hospitals

ASSUMPTIONS = [
    "All 120 hospitals are synthetic; distributions loosely shaped to published rural hospital data (median margin near break-even, many with <60 days cash).",
    "Transparent Rural Vulnerability Score is an illustrative weighted model (weights published in code); it is not Chartis' proprietary INDEX.",
    "Medicaid revenue shock = 10% reduction of Medicaid share of net patient revenue, a proxy for 2025 federal Medicaid changes (OBBBA); these phase in mostly over 2027-28, so treat the shock as a steady state 2-3 years out, not an immediate loss.",
    "340B / site-neutral shock = 2% of net patient revenue for hospitals with an outpatient-heavy mix.",
    "OB closure (units < 200 births) saves ~$1.2M/yr direct cost; OB-linked revenue = 8% of NPR, of which 25% is lost, capped at $1M/yr. Closure is flagged as an access loss, and not recommended, if the next hospital is > 30 miles away.",
    "REH eligibility here is a PROXY (CAH or <= 50 beds, average daily census < 5), not the statutory test (CAH or rural hospital <= 50 beds as of Dec 27 2020, plus state licensure).",
    "REH conversion: inpatient revenue removed; inpatient cost = expenses x inpatient revenue share x 1.1, of which only 50% is avoidable (the rest is fixed); adds ~$3.4M/yr facility payment and +5% on the Medicare OPPS share (40%) of outpatient revenue; CAHs lose ~10% on that Medicare outpatient revenue when cost-based payment ends; swing-bed and 340B revenue (~6% of NPR) lost; +$0.75M/yr for transfer and 24/7 ED requirements. Only loss-making hospitals are considered, and post-conversion margin is bounded at 10% as a sanity check.",
    "Operational improvement option = 1.5% expense reduction (shared services, revenue cycle, staffing). Always available; access-neutral.",
    "Reference client = system/association with the 20 most vulnerable hospitals; annual value = 15% realization x sum of the best access-protecting option per hospital (assumption, to validate in pilot).",
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
    """Eligibility proxy (not the statutory test): CAH or <= 50 beds, low census,
    and currently losing money (healthy hospitals are not conversion candidates)."""
    return (h["cah"] or h["beds"] <= 50) and h["adc"] < REH_MAX_ADC and h["op_margin"] < 0


def _ip_revenue_share(h: dict) -> float:
    """Inpatient share of revenue rises with occupancy (illustrative)."""
    return clamp(0.15 + 0.5 * h["adc"] / h["beds"], 0.15, 0.45)


def apply_scenario(h: dict, medicaid_cut: float = 0.0, site_neutral: bool = False,
                   close_ob: bool = False, convert_reh: bool = False,
                   ops_improvement: bool = False) -> dict:
    """Return a copy of hospital ``h`` with margin/cash recomputed under shocks."""
    s = dict(h)
    npr = h["npr"]
    expenses = npr * (1 - h["op_margin"])
    revenue = npr
    revenue -= npr * h["medicaid_pct"] * medicaid_cut
    if site_neutral and h["outpatient_heavy"]:
        revenue -= npr * SITE_NEUTRAL_SHARE
    s["access_loss"] = False
    if close_ob and 0 < h["births"] < OB_LOW_VOLUME_BIRTHS:
        expenses -= OB_DIRECT_COST_SAVED
        revenue -= min(npr * OB_LINKED_REVENUE_SHARE * OB_LINKED_REVENUE_LOST, OB_LINKED_REVENUE_CAP)
        s["access_loss"] = h["miles_to_next"] > ACCESS_MILES
    if convert_reh and reh_eligible(h):
        ip_share = _ip_revenue_share(h)
        ip_rev = npr * ip_share
        op_rev = npr - ip_rev
        medicare_op = op_rev * MEDICARE_OP_SHARE
        op_change = medicare_op * REH_OPPS_UPLIFT
        if h["cah"]:
            op_change -= medicare_op * CAH_COST_BASED_LOSS
        revenue += -ip_rev + REH_FACILITY_PAYMENT + op_change - npr * REH_LOST_OTHER_REVENUE
        ip_cost = expenses * ip_share * IP_COST_INTENSITY
        expenses += -ip_cost * IP_COST_AVOIDABLE + REH_ADDED_COST
        # Sanity bound: excess over the ceiling assumed absorbed by REH staffing rules.
        expenses = max(expenses, revenue * (1 - REH_MARGIN_CEILING))
        s["adc"] = 0.5
    if ops_improvement:
        expenses *= 1 - OPS_IMPROVEMENT
    s["op_margin"] = (revenue - expenses) / revenue
    s["npr"] = revenue
    s["annual_delta_usd"] = (revenue - expenses) - npr * h["op_margin"]
    # cash erodes by one year of incremental loss, expressed in days of expense
    s["days_cash"] = max(0.0, h["days_cash"] + s["annual_delta_usd"] / (expenses / 365))
    return s


def strategy_options(s: dict) -> dict:
    """Candidate strategies for one (already shocked) hospital."""
    opts = {"Operational improvement": apply_scenario(s, ops_improvement=True)}
    if 0 < s["births"] < OB_LOW_VOLUME_BIRTHS:
        opts["Consolidate OB (low volume)"] = apply_scenario(s, close_ob=True)
    if reh_eligible(s):
        opts["Convert to REH"] = apply_scenario(s, convert_reh=True)
    return opts


def best_option(s: dict) -> tuple[str, dict, list[str]]:
    """Best access-protecting option by annual delta; lists rejected access-loss options."""
    opts = strategy_options(s)
    rejected = [k for k, v in opts.items() if v["access_loss"]]
    safe = {k: v for k, v in opts.items() if not v["access_loss"]}
    name, b = max(safe.items(), key=lambda kv: kv[1]["annual_delta_usd"])
    return name, b, rejected


def run(seed: int = 42) -> dict:
    r = rng(seed)
    hospitals = [_hospital(r, i) for i in range(1, 121)]
    for h in hospitals:
        h["score"] = score(h)

    # Policy shock: Medicaid revenue cut + site-neutral change.
    shocked = [apply_scenario(h, medicaid_cut=MEDICAID_CUT, site_neutral=True) for h in hospitals]
    for s in shocked:
        s["score"] = score(s)
    newly_at_risk = [s for h, s in zip(hospitals, shocked) if h["score"] < AT_RISK <= s["score"]]
    shock_loss = -sum(min(0.0, s["annual_delta_usd"]) for s in shocked)
    base_score = {h["id"]: h["score"] for h in hospitals}

    ranked = sorted(shocked, key=lambda s: -s["score"])
    plans = {s["id"]: best_option(s) for s in ranked}
    at_risk_shock = [s for s in shocked if s["score"] >= AT_RISK]
    strategies = [s for s in at_risk_shock if plans[s["id"]][1]["annual_delta_usd"] > 50_000]
    rejected_count = sum(1 for s in at_risk_shock if plans[s["id"]][2])

    table = []
    for s in ranked[:15]:
        d = drivers(s)
        main = sorted(d, key=lambda k: -WEIGHTS[k] * d[k])[:2]
        name, b, rejected = plans[s["id"]]
        table.append({
            "hospital": s["id"], "state": s["state"], "beds": s["beds"],
            "cah": "Y" if s["cah"] else "N",
            "score_base": base_score[s["id"]],
            "score_shock": s["score"],
            "op_margin_shock": f"{s['op_margin'] * 100:.1f}%",
            "days_cash_shock": round(s["days_cash"]),
            "top_drivers": ", ".join(main),
            "suggested_option": name,
            "option_value": usd(b["annual_delta_usd"]),
            "margin_after_option": f"{b['op_margin'] * 100:.1f}%",
            "protects_access": "Yes" if not b["access_loss"] else "No",
            "access_risk": ("Rejected: " + ", ".join(rejected) + f" (next hospital > {ACCESS_MILES:.0f} mi)")
            if rejected else ("Inpatient beds lost; ED retained" if name == "Convert to REH" else "Low"),
        })

    client = ranked[:TOP_N_CLIENT]
    option_value = sum(max(0.0, plans[s["id"]][1]["annual_delta_usd"]) for s in client)
    annual_value = option_value * REALIZATION
    strategy_gain = sum(plans[s["id"]][1]["annual_delta_usd"] for s in strategies)
    at_risk_now = [h for h in hospitals if h["score"] >= AT_RISK]

    return result(
        key="rural",
        problem="Rural hospital financial distress, closures & service-line loss",
        question="Which rural hospitals tip into distress under policy shocks, and which strategic option (OB consolidation, REH conversion, ops) protects access?",
        headline_metrics=[
            metric("Hospitals modeled", len(hospitals)),
            metric("At risk today (score >= 60)", len(at_risk_now)),
            metric("Newly at risk after shock", len(newly_at_risk)),
            metric("Annual shock loss (portfolio)", shock_loss, "usd"),
            metric("At-risk hospitals with an access-safe option > $50K", len(strategies)),
            metric("Modeled strategy gain (at-risk set)", strategy_gain, "usd"),
            metric("Access-loss options rejected", rejected_count),
        ],
        annual_value_usd=annual_value,
        soft_value_usd=0.0,
        value_basis=(f"Best access-protecting option per hospital for the {TOP_N_CLIENT} most vulnerable "
                     f"(sum {usd(option_value)}/yr) x {REALIZATION:.0%} realization (assumption). "
                     "Access preserved is reported as counts, not dollars."),
        assumptions=ASSUMPTIONS,
        table_title="Top 15 most vulnerable hospitals after Medicaid cut + site-neutral shock, with access-safe option",
        table=table,
        details={
            "weights": WEIGHTS,
            "at_risk_threshold": AT_RISK,
            "scenario": {"medicaid_cut": MEDICAID_CUT, "site_neutral": True},
            "newly_at_risk_ids": [s["id"] for s in newly_at_risk],
            "reh_eligible_count": sum(reh_eligible(h) for h in hospitals),
            "client_option_value_full": round(option_value),
            "ob_units": sum(1 for h in hospitals if h["births"] > 0),
        },
    )
