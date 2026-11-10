"""AI value realization & governance portfolio (synthetic).

Question: which AI use cases should a reference 1,000-bed / $3B health system
fund, pilot, or hold -- and is the funded portfolio actually delivering?

Method
1. Catalog ~25 use cases with benefit drivers (hours saved x loaded rate,
   revenue lift, cost avoided), costs (one-time + annual license),
   time-to-value, data readiness, clinical risk tier, regulatory exposure,
   evidence strength and adoption risk.
2. Risk-adjust gross benefit by evidence, data readiness and adoption risk.
3. 3-year monthly NPV: benefits start after time-to-value and ramp linearly
   over RAMP_MONTHS; one-time cost at t0; license billed monthly.
4. Governance gate: high clinical risk + weak evidence -> Hold; high risk with
   moderate evidence, or medium risk with weak evidence -> Pilot (with
   monitoring); poor data readiness or NPV <= 0 -> Hold.
5. Pilots are funded first from PILOT_RESERVE (PILOT_COST_SHARE of one-time
   cost each); then greedy Fund selection by risk-adjusted NPV per year-1
   dollar under the remaining year-1 budget. Items that pass
   the gate but don't fit are "Defer (budget)".
6. Value tracking: simulate realized adoption for funded items vs. promise and
   flag value leakage below LEAKAGE_THRESHOLD.
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
LOADED_RATE = {"physician": 160.0, "nurse": 75.0, "admin": 45.0, "none": 0.0}

ASSUMPTIONS = [
    "Reference client: 1,000 staffed beds, ~$3B net patient revenue, ~1,200 employed physicians.",
    "Loaded hourly rates: physician $160, nurse $75, admin/revenue-cycle $45.",
    "Discount rate 8%; 3-year horizon; benefits ramp linearly over 6 months after time-to-value.",
    "Risk adjustment = evidence (0.5+0.1*E) x data readiness (0.6+0.08*R) x (1 - adoption risk).",
    "Hours saved are only partly convertible to cash; values represent capacity/value, not guaranteed P&L savings.",
    f"Year-1 AI budget ${YEAR1_BUDGET/1e6:.0f}M (one-time + license); pilots cost {PILOT_COST_SHARE:.0%} of one-time.",
    "Governance gate is illustrative; real gate should follow the client's AI governance policy (e.g. CHAI/NIST AI RMF aligned).",
    "Realized-adoption simulation is random (seeded) and stands in for post-go-live telemetry.",
    "All catalog figures are synthetic order-of-magnitude estimates, not vendor quotes.",
]

# name, domain, hours/yr, rate class, revenue lift, cost avoided, one-time, annual license,
# ttv months, data readiness 1-5, clinical risk, regulatory exposure, evidence 1-5, adoption risk 0-1
CATALOG = [
    ("Ambient clinical documentation", "Clinical ops", 120_000, "physician", 2_500_000, 1_000_000, 900_000, 3_600_000, 4, 4, "low", "Privacy/consent", 4, 0.30),
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
    ("Medication reconciliation assist", "Clinical quality", 20_000, "nurse", 0, 700_000, 400_000, 350_000, 9, 2, "medium", "Patient safety", 2, 0.40),
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
    """Governance gate -> (eligible decision, reason)."""
    if u["readiness"] <= 1:
        return "Hold", "Data not ready"
    if u["risk"] == "high" and u["evidence"] <= 2:
        return "Hold", "High clinical risk, weak evidence"
    if u["risk"] == "high" and u["evidence"] == 3:
        return "Pilot", "High risk: monitored pilot first"
    if u["risk"] == "medium" and u["evidence"] <= 2:
        return "Pilot", "Medium risk, weak evidence"
    if u["npv"] <= 0:
        return "Hold", "Negative risk-adjusted NPV"
    return "Fund", "Passes gate"


def evaluate(seed: int = 42) -> list[dict]:
    r = rng(seed)
    out = []
    for row in CATALOG:
        u = dict(zip(FIELDS, row))
        noise = r.uniform(0.9, 1.1)
        gross = (u["hours"] * LOADED_RATE[u["rate"]] + u["revenue"] + u["avoided"]) * noise
        factor = (0.5 + 0.1 * u["evidence"]) * (0.6 + 0.08 * u["readiness"]) * (1 - u["adoption_risk"])
        u["gross_benefit"] = gross
        u["risk_adj_benefit"] = gross * factor
        u["npv"], u["payback"] = _npv(u["risk_adj_benefit"], u["one_time"], u["license"], u["ttv"])
        u["year1_cost"] = u["one_time"] + u["license"]
        u["gate"], u["reason"] = _gate(u)
        out.append(u)
    return out


def select(cases: list[dict], budget: float = YEAR1_BUDGET, seed: int = 42) -> tuple[list[dict], float]:
    """Greedy portfolio under budget; sets decision + spend. Returns (cases, spend)."""
    ranked = sorted(cases, key=lambda u: u["npv"] / u["year1_cost"], reverse=True)
    pilot_spend = 0.0
    for u in ranked:  # pilots first, from a reserved slice (ranked by gross upside)
        u["decision"], u["spend"] = ("Hold", 0.0) if u["gate"] == "Hold" else (None, 0.0)
    for u in sorted((u for u in ranked if u["gate"] == "Pilot"),
                    key=lambda u: u["gross_benefit"] / u["one_time"], reverse=True):
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
    annual = sum(u["risk_adj_benefit"] - u["license"] for u in funded)
    promised = sum(u["risk_adj_benefit"] for u in funded)
    realized = sum(u["risk_adj_benefit"] * u["realized_share"] for u in funded)
    leaks = [u["name"] for u in funded if u["leakage"]]
    table = [{
        "use_case": u["name"], "domain": u["domain"], "risk": u["risk"], "evidence": u["evidence"],
        "decision": u["decision"], "reason": u["reason"],
        "risk_adj_npv_3yr": round(u["npv"]), "payback_months": u["payback"],
        "year1_spend": round(u["spend"]),
        "realized_vs_promised": None if u["realized_share"] is None else round(u["realized_share"], 2),
    } for u in cases]
    return result(
        key="ai_portfolio",
        problem="AI/digital investment without measurable value",
        question="Which AI use cases should we fund, pilot or hold -- and are funded ones delivering?",
        headline_metrics=[
            metric("Use cases evaluated", len(cases)),
            metric("Funded / piloted", len(funded), fmt=",.0f") | {"display": f"{len(funded)} / {len(pilots)}"},
            metric("Year-1 spend vs budget", spend, "usd") | {"display": f"${spend/1e6:.1f}M / ${YEAR1_BUDGET/1e6:.0f}M"},
            metric("Portfolio 3-yr risk-adj NPV", sum(u["npv"] for u in funded), "usd"),
            metric("Realized vs promised benefit", 100 * realized / promised if promised else 0, "%"),
            metric("Use cases flagged for value leakage", len(leaks)),
        ],
        annual_value_usd=annual,
        value_basis="Steady-state annual risk-adjusted benefit minus license cost of funded use cases.",
        assumptions=ASSUMPTIONS,
        table_title="AI use-case portfolio (ranked by risk-adjusted NPV per year-1 $)",
        table=table,
        details={"budget": YEAR1_BUDGET, "spend": round(spend), "value_leakage": leaks,
                 "promised_annual": round(promised), "realized_annual": round(realized)},
    )
