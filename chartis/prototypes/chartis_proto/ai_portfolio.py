"""AI value realization & governance portfolio (synthetic).

Question: which AI use cases should a reference 1,000-bed / $3B health system
fund, pilot, or hold -- and is the funded portfolio actually delivering?

Method
1. Catalog ~25 use cases. Benefits are split into HARD value (revenue lift +
   cost avoided, i.e. P&L) and SOFT value (hours saved x loaded rate, i.e.
   capacity returned to clinicians/staff, not guaranteed cash).
2. Risk-adjust both by evidence, data readiness and adoption risk. Stacked
   revenue-cycle use cases (coding, CDI, charge capture, appeals, prior auth)
   claim pieces of the same coded revenue, so their hard value takes an
   OVERLAP_HAIRCUT.
3. Decision value = hard + SOFT_DECISION_WEIGHT x soft. 3-year monthly NPV of
   decision value: benefits start after time-to-value and ramp linearly over
   RAMP_MONTHS; one-time cost at t0; license + internal integration/change
   cost (INTERNAL_COST_SHARE x license) billed monthly.
4. Governance gate, evaluated in this order:
   a. data readiness <= MIN_READINESS            -> Hold (data not ready)
   b. high clinical risk and evidence <= 2       -> Hold
   c. pilot candidate (high risk + evidence 3, or medium risk + evidence <= 2)
      -> Pilot if steady-state decision value exceeds annual run cost,
         otherwise Hold. Pilots buy evidence, so they need positive upside
         but are not required to reach NPV > 0 inside 3 years.
   d. NPV <= 0                                   -> Hold
   e. otherwise                                  -> Fund
5. Pilots are funded first from PILOT_RESERVE (PILOT_COST_SHARE of one-time
   cost each), ranked by risk-adjusted upside per pilot dollar; then greedy
   Fund selection by NPV per year-1 dollar under the remaining year-1 budget.
   Items that pass the gate but don't fit are "Defer (budget)".
6. Value tracking: simulate realized adoption for funded items vs. promise and
   flag value leakage below LEAKAGE_THRESHOLD.
7. Headline (annual_value_usd) = REALIZED hard value of funded items, net of
   license, internal cost, and one-time + pilot spend amortized over 3 years.
   Soft value is reported separately (soft_value_usd) and never added.
"""
from __future__ import annotations

from .common import metric, result, rng

DISCOUNT_RATE = 0.08
HORIZON_MONTHS = 36
RAMP_MONTHS = 6
YEAR1_BUDGET = 12_000_000
PILOT_COST_SHARE = 0.25
PILOT_RESERVE = 1_500_000  # carved out of the year-1 budget for monitored pilots
LEAKAGE_THRESHOLD = 0.75
INTERNAL_COST_SHARE = 0.50  # integration, change management, monitoring vs license
AMORTIZE_YEARS = 3
OVERLAP_HAIRCUT = 0.40  # on hard value of stacked revenue-cycle use cases
SOFT_DECISION_WEIGHT = 0.5  # share of capacity value counted when ranking (not headline)
MIN_READINESS = 2  # readiness at or below this -> Hold
LICENSE_DISCOUNT = 0.30  # negotiated enterprise discount off catalog (list) license
LOADED_RATE = {"physician": 160.0, "nurse": 75.0, "admin": 45.0, "none": 0.0}

# Use cases that claim the same coded revenue -> overlap haircut on hard value.
REV_CYCLE_STACK = {
    "Prior-auth automation", "Coding assist (CAC+LLM)", "Denial appeal letter generation",
    "Revenue integrity / charge capture", "Clinical documentation integrity (CDI) AI",
}
# Use cases whose value overlaps another prototype module (attribute once per client).
OVERLAPS_MODULE = {
    "Prior-auth automation": "denials", "Coding assist (CAC+LLM)": "denials",
    "Denial appeal letter generation": "denials", "Revenue integrity / charge capture": "denials",
    "Clinical documentation integrity (CDI) AI": "denials",
    "Capacity / discharge prediction": "patient_flow", "Readmission risk + transitions": "patient_flow",
    "Nurse scheduling optimization": "workforce", "HR recruiting screening": "workforce",
    "Ambient clinical documentation": "workforce",
}

ASSUMPTIONS = [
    "Reference client: 1,000 staffed beds, ~$3B net patient revenue, ~1,200 employed physicians.",
    "Loaded hourly rates: physician $160, nurse $75, admin/revenue-cycle $45.",
    "HARD value = revenue lift + cost avoided; SOFT value = hours saved x loaded rate (capacity, not cash). "
    "Headline is hard only; soft is reported separately.",
    "Ambient documentation: 60K physician hrs/yr (~50 hrs/physician at partial adoption; halved from v1 as RCTs show "
    "modest time savings). Its visit-volume revenue lift is NOT counted, because it would spend the same hours; "
    "only transcription/scribe cost avoided is hard value.",
    "Discount rate 8%; 3-year horizon; benefits ramp linearly over 6 months after time-to-value.",
    "Risk adjustment = evidence (0.5+0.1*E) x data readiness (0.6+0.08*R) x (1 - adoption risk).",
    f"Internal integration/change/monitoring cost = {INTERNAL_COST_SHARE:.0%} of license; one-time and pilot spend "
    f"amortized over {AMORTIZE_YEARS} years in the headline.",
    f"Stacked revenue-cycle use cases (coding, CDI, charge capture, appeals, prior auth) take a "
    f"{OVERLAP_HAIRCUT:.0%} overlap haircut on hard value. Use cases tagged overlaps_module also overlap the "
    "denials / patient_flow / workforce prototypes: a client value ledger must attribute each dollar once.",
    f"Headline uses REALIZED value (simulated adoption) not promised value; ranking counts soft value at "
    f"{SOFT_DECISION_WEIGHT:.0%}.",
    f"Year-1 AI budget ${YEAR1_BUDGET/1e6:.0f}M covers one-time + license + internal cost; pilots cost "
    f"{PILOT_COST_SHARE:.0%} of one-time from a ${PILOT_RESERVE/1e6:.1f}M reserve.",
    f"Catalog licenses are list prices; a {LICENSE_DISCOUNT:.0%} negotiated enterprise discount is applied.",
    f"Data readiness <= {MIN_READINESS} (of 5) -> Hold until data foundations are fixed.",
    "Governance gate is illustrative; real gate should follow the client's AI governance policy (e.g. CHAI/NIST AI RMF aligned).",
    "Realized-adoption simulation is random (seeded) and stands in for post-go-live telemetry.",
    "All catalog figures are synthetic order-of-magnitude estimates, not vendor quotes.",
]

# name, domain, hours/yr, rate class, revenue lift, cost avoided, one-time, annual license,
# ttv months, data readiness 1-5, clinical risk, regulatory exposure, evidence 1-5, adoption risk 0-1
CATALOG = [
    ("Ambient clinical documentation", "Clinical ops", 60_000, "physician", 0, 1_000_000, 900_000, 3_600_000, 4, 4, "low", "Privacy/consent", 4, 0.30),
    ("Inbox message drafting", "Clinical ops", 45_000, "physician", 0, 300_000, 250_000, 600_000, 3, 4, "medium", "Patient safety/privacy", 3, 0.35),
    ("Prior-auth automation", "Revenue cycle", 60_000, "admin", 1_800_000, 400_000, 700_000, 900_000, 6, 3, "low", "Payer rules", 3, 0.25),
    ("Coding assist (CAC+LLM)", "Revenue cycle", 40_000, "admin", 4_500_000, 0, 600_000, 1_100_000, 5, 4, "low", "Compliance/upcoding", 4, 0.20),
    ("Denial appeal letter generation", "Revenue cycle", 25_000, "admin", 3_200_000, 0, 300_000, 400_000, 3, 4, "low", "Compliance", 3, 0.20),
    ("Sepsis early warning", "Clinical quality", 0, "none", 0, 3_500_000, 800_000, 500_000, 9, 3, "high", "FDA SaMD/bias", 2, 0.40),
    ("Readmission risk + transitions", "Clinical quality", 8_000, "nurse", 0, 2_200_000, 400_000, 300_000, 6, 4, "medium", "Bias", 3, 0.35),
    ("Imaging triage (stroke/PE)", "Clinical quality", 3_000, "physician", 900_000, 1_500_000, 500_000, 700_000, 6, 4, "high", "FDA-cleared SaMD", 4, 0.20),
    ("Patient access chatbot/scheduling", "Access", 50_000, "admin", 2_000_000, 0, 500_000, 600_000, 4, 3, "low", "Privacy", 3, 0.35),
    ("Nurse scheduling optimization", "Workforce", 20_000, "nurse", 0, 3_000_000, 600_000, 500_000, 6, 3, "low", "Labor relations", 3, 0.30),
    ("Supply chain demand forecasting", "Operations", 6_000, "admin", 0, 2_400_000, 500_000, 350_000, 6, 3, "low", "None material", 3, 0.20),
    ("Capacity / discharge prediction", "Operations", 15_000, "nurse", 1_500_000, 2_000_000, 700_000, 600_000, 6, 3, "medium", "Bias", 3, 0.35),
    ("OR block utilization optimizer", "Operations", 4_000, "admin", 3_000_000, 0, 400_000, 400_000, 6, 4, "low", "None material", 3, 0.30),
    ("Clinical trial matching", "Research", 5_000, "nurse", 600_000, 0, 300_000, 250_000, 9, 2, "low", "Privacy/IRB", 2, 0.40),
    ("Radiology report summarization", "Clinical ops", 10_000, "physician", 0, 0, 300_000, 400_000, 6, 3, "medium", "Patient safety", 2, 0.35),
    ("Pathology slide AI", "Clinical quality", 6_000, "physician", 0, 400_000, 1_500_000, 600_000, 12, 2, "high", "FDA SaMD", 3, 0.40),
    ("Deterioration index (med-surg)", "Clinical quality", 0, "none", 0, 1_800_000, 300_000, 200_000, 6, 4, "high", "Bias/alert fatigue", 2, 0.45),
    ("Patient-facing symptom triage LLM", "Access", 15_000, "nurse", 500_000, 0, 400_000, 500_000, 6, 3, "high", "Patient safety/liability", 1, 0.50),
    ("Revenue integrity / charge capture", "Revenue cycle", 8_000, "admin", 3_800_000, 0, 500_000, 600_000, 6, 4, "low", "Compliance", 3, 0.20),
    ("IT service desk copilot", "Corporate", 30_000, "admin", 0, 200_000, 150_000, 300_000, 3, 4, "low", "None material", 4, 0.20),
    ("HR recruiting screening", "Workforce", 12_000, "admin", 0, 600_000, 200_000, 250_000, 4, 3, "low", "Employment bias law", 2, 0.30),
    ("Care-gap closure outreach (VBC)", "Value-based care", 10_000, "nurse", 2_600_000, 0, 400_000, 500_000, 9, 3, "low", "Privacy", 3, 0.35),
    ("Clinical documentation integrity (CDI) AI", "Revenue cycle", 15_000, "nurse", 5_000_000, 0, 600_000, 900_000, 6, 4, "low", "Compliance", 4, 0.25),
    ("Medication reconciliation assist", "Clinical quality", 20_000, "nurse", 0, 700_000, 400_000, 350_000, 9, 3, "medium", "Patient safety", 2, 0.40),
    ("Contract/payer analytics LLM", "Finance", 5_000, "admin", 2_000_000, 0, 300_000, 300_000, 6, 3, "low", "None material", 2, 0.30),
]

FIELDS = ["name", "domain", "hours", "rate", "revenue", "avoided", "one_time", "license",
          "ttv", "readiness", "risk", "regulatory", "evidence", "adoption_risk"]


def _npv(annual_benefit: float, one_time: float, license_: float, ttv: int) -> tuple[float, float | None]:
    """Monthly discounted cash flow; returns (NPV, payback month or None)."""
    r = (1 + DISCOUNT_RATE) ** (1 / 12) - 1
    npv, cum, payback = -one_time, -one_time, None
    for m in range(1, HORIZON_MONTHS + 1):
        ramp = 0.0 if m <= ttv else min(1.0, (m - ttv) / RAMP_MONTHS)
        cf = annual_benefit / 12 * ramp - license_ / 12
        npv += cf / (1 + r) ** m
        cum += cf
        if payback is None and cum >= 0:
            payback = m
    return npv, payback


def _gate(u: dict) -> tuple[str, str]:
    """Governance gate -> (eligible decision, reason). Order documented in module docstring."""
    if u["readiness"] <= MIN_READINESS:
        return "Hold", "Data not ready"
    if u["risk"] == "high" and u["evidence"] <= 2:
        return "Hold", "High clinical risk, weak evidence"
    pilot_candidate = (u["risk"] == "high" and u["evidence"] == 3) or (
        u["risk"] == "medium" and u["evidence"] <= 2
    )
    if pilot_candidate:
        if u["decision_value"] > u["run_cost"]:
            return "Pilot", "Elevated risk / thin evidence: monitored pilot first"
        return "Hold", "Pilot upside does not cover run cost"
    if u["npv"] <= 0:
        return "Hold", "Negative risk-adjusted NPV"
    return "Fund", "Passes gate"


def evaluate(seed: int = 42) -> list[dict]:
    r = rng(seed)
    out = []
    for row in CATALOG:
        u = dict(zip(FIELDS, row))
        noise = r.uniform(0.9, 1.1)
        factor = (0.5 + 0.1 * u["evidence"]) * (0.6 + 0.08 * u["readiness"]) * (1 - u["adoption_risk"])
        hard = (u["revenue"] + u["avoided"]) * noise
        soft = u["hours"] * LOADED_RATE[u["rate"]] * noise
        if u["name"] in REV_CYCLE_STACK:
            hard *= 1 - OVERLAP_HAIRCUT
        u["gross_benefit"] = hard + soft
        u["hard_benefit"] = hard * factor
        u["soft_benefit"] = soft * factor
        u["decision_value"] = u["hard_benefit"] + SOFT_DECISION_WEIGHT * u["soft_benefit"]
        u["license"] *= 1 - LICENSE_DISCOUNT
        u["run_cost"] = u["license"] * (1 + INTERNAL_COST_SHARE)
        u["npv"], u["payback"] = _npv(u["decision_value"], u["one_time"], u["run_cost"], u["ttv"])
        u["year1_cost"] = u["one_time"] + u["run_cost"]
        u["overlaps_module"] = OVERLAPS_MODULE.get(u["name"], "")
        u["gate"], u["reason"] = _gate(u)
        out.append(u)
    return out


def select(cases: list[dict], budget: float = YEAR1_BUDGET, seed: int = 42) -> tuple[list[dict], float]:
    """Greedy portfolio under budget; sets decision + spend. Returns (cases, spend)."""
    ranked = sorted(cases, key=lambda u: u["npv"] / u["year1_cost"], reverse=True)
    for u in ranked:
        u["decision"], u["spend"] = ("Hold", 0.0) if u["gate"] == "Hold" else (None, 0.0)
    # Pilots first, from a reserved slice, ranked by risk-adjusted upside per pilot dollar.
    pilot_spend = 0.0
    for u in sorted((u for u in ranked if u["gate"] == "Pilot"),
                    key=lambda u: u["decision_value"] / u["one_time"], reverse=True):
        cost = PILOT_COST_SHARE * u["one_time"]
        if pilot_spend + cost <= min(PILOT_RESERVE, budget):
            u["decision"], u["spend"] = "Pilot", cost
            pilot_spend += cost
        else:
            u["decision"] = "Defer (budget)"
    spend = pilot_spend
    for u in ranked:
        if u["gate"] != "Fund":
            continue
        if spend + u["year1_cost"] <= budget:
            u["decision"], u["spend"] = "Fund", u["year1_cost"]
            spend += u["year1_cost"]
        else:
            u["decision"] = "Defer (budget)"
    r = rng(seed + 1)
    for u in cases:  # value tracking for funded items
        u["realized_share"] = r.uniform(0.55, 1.05) if u["decision"] == "Fund" else None
        u["leakage"] = u["realized_share"] is not None and u["realized_share"] < LEAKAGE_THRESHOLD
    return ranked, spend


def run(seed: int = 42) -> dict:
    cases, spend = select(evaluate(seed), seed=seed)
    funded = [u for u in cases if u["decision"] == "Fund"]
    pilots = [u for u in cases if u["decision"] == "Pilot"]
    promised_hard = sum(u["hard_benefit"] for u in funded)
    realized_hard = sum(u["hard_benefit"] * u["realized_share"] for u in funded)
    realized_soft = sum(u["soft_benefit"] * u["realized_share"] for u in funded)
    run_costs = sum(u["run_cost"] for u in funded)
    amortized = (sum(u["one_time"] for u in funded) + sum(u["spend"] for u in pilots)) / AMORTIZE_YEARS
    hard_net = realized_hard - run_costs - amortized
    promised = sum(u["hard_benefit"] + u["soft_benefit"] for u in funded)
    realized = realized_hard + realized_soft
    leaks = [u["name"] for u in funded if u["leakage"]]
    table = [{
        "use_case": u["name"], "domain": u["domain"], "risk": u["risk"], "evidence": u["evidence"],
        "decision": u["decision"], "reason": u["reason"],
        "hard_benefit_yr": round(u["hard_benefit"]), "soft_benefit_yr": round(u["soft_benefit"]),
        "risk_adj_npv_3yr": round(u["npv"]), "payback_months": u["payback"],
        "year1_spend": round(u["spend"]),
        "realized_vs_promised": None if u["realized_share"] is None else round(u["realized_share"], 2),
        "overlaps_module": u["overlaps_module"],
    } for u in cases]
    return result(
        key="ai_portfolio",
        problem="AI/digital investment without measurable value",
        question="Which AI use cases should we fund, pilot or hold -- and are funded ones delivering?",
        headline_metrics=[
            metric("Use cases evaluated", len(cases)),
            metric("Funded / piloted", len(funded), fmt=",.0f") | {"display": f"{len(funded)} / {len(pilots)}"},
            metric("Year-1 spend vs budget", spend, "usd") | {"display": f"${spend/1e6:.1f}M / ${YEAR1_BUDGET/1e6:.0f}M"},
            metric("Portfolio 3-yr risk-adj NPV (decision basis)", sum(u["npv"] for u in funded), "usd"),
            metric("Realized vs promised benefit", 100 * realized / promised if promised else 0, "%"),
            metric("Use cases flagged for value leakage", len(leaks)),
            metric("Soft value (capacity, not cash) / yr", realized_soft, "usd"),
        ],
        annual_value_usd=hard_net,
        soft_value_usd=realized_soft,
        value_basis="Realized hard value (revenue lift + cost avoided, after 40% revenue-cycle overlap haircut) of "
                    "funded use cases, minus license, internal cost, and one-time + pilot spend amortized over 3 years. "
                    "Clinician/staff hours are soft value, reported separately.",
        assumptions=ASSUMPTIONS,
        table_title="AI use-case portfolio (ranked by risk-adjusted NPV per year-1 $)",
        table=table,
        details={"budget": YEAR1_BUDGET, "spend": round(spend), "value_leakage": leaks,
                 "promised_hard_annual": round(promised_hard), "realized_hard_annual": round(realized_hard),
                 "realized_soft_annual": round(realized_soft), "run_costs_annual": round(run_costs),
                 "amortized_one_time_annual": round(amortized)},
    )
