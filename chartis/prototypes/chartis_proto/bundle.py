"""One reference client, one value ledger.

Each prototype sizes its value on its own reference client, so the five
headline numbers cannot be compared or added. This module rescales all five
to a single illustrative client and removes value that two modules both
claim, giving one defensible bundle number and the fee it can support.

Method
------
1. Run each module, then rescale its output linearly to ``CLIENT`` using the
   driver documented in ``SCALING`` (beds, RN headcount, NPR, rural hospitals).
   Linear scaling is a first-order approximation.
2. Attribute overlapping value once: funded AI use cases that another module
   already claims (``overlaps_module`` in the AI portfolio) are removed from
   the AI line when that module is in the bundle.
3. Apply the client-ROI rule: supportable annual fees = hard value / 5.

Hard and soft value are never added together.
"""

from __future__ import annotations

from collections.abc import Iterable

from . import ai_portfolio, denials, patient_flow, rural, workforce
from .sensitivity import DEFAULT_SEEDS, summarize

CLIENT = {
    "name": "Illustrative regional health system",
    "net_patient_revenue": 2.0e9,
    "staffed_beds": 800,  # flagship 500 + community 300
    "capacity_constrained_beds": 500,  # beds in hospitals running >= 85% occupancy
    "rn_headcount": 2_400,
    "affiliated_rural_hospitals": 8,
}
ROI_RULE = 5.0  # client hard value : annual fees
WORKFORCE_MODEL_BEDS = 298  # beds in workforce.UNITS
WORKFORCE_MODEL_RNS = 1_100
PATIENT_FLOW_MODEL_BEDS = patient_flow.STAFFED_BEDS
AI_MODEL_NPR = 3.0e9
PARTNER_COST_VARIABLE_SHARE = 0.5  # half of the denials partner cost scales with NPR

LABELS = {
    "workforce": "Workforce",
    "patient_flow": "Patient flow",
    "rural": "Rural sustainability",
    "denials": "Denials & prior auth",
    "ai_portfolio": "AI value",
}
SCALING = {
    "workforce": "Labor savings x staffed beds / 298; retention value x RN headcount / 1,100",
    "patient_flow": "x capacity-constrained beds / 500",
    "rural": "x affiliated rural hospitals / 20 (assumes affiliates resemble the most vulnerable set)",
    "denials": "Gross value x NPR / $1B; partner cost half fixed, half scaling with NPR",
    "ai_portfolio": "x NPR / $3B (budget scales too); minus funded use cases claimed by another module",
}
ASSUMPTIONS = [
    "One illustrative client: $2.0B net patient revenue, 800 staffed beds (500 capacity-constrained), 2,400 RNs, 8 affiliated rural hospitals.",
    "Module outputs scale linearly with their driver (first-order approximation; calibrate on client data).",
    "Overlap: funded AI use cases tagged to another module are counted in that module only.",
    f"Client-ROI rule: annual fees are supportable up to hard value / {ROI_RULE:.0f}.",
    "Soft value (capacity, clinician time, access) is shown separately and never added to hard value.",
]


def _metric(res: dict, label: str) -> float:
    return next(m["value"] for m in res["headline_metrics"] if m["label"] == label)


def ledger(seed: int = 42, client: dict | None = None) -> dict:
    c = client or CLIENT
    lines = []

    w = workforce.run(seed)
    w_hard = _metric(w, "Labor cost savings / yr") * c["staffed_beds"] / WORKFORCE_MODEL_BEDS
    w_hard += _metric(w, "Net retention value / yr") * c["rn_headcount"] / WORKFORCE_MODEL_RNS
    lines.append(("workforce", w_hard, 0.0))

    p = patient_flow.run(seed)
    k = c["capacity_constrained_beds"] / PATIENT_FLOW_MODEL_BEDS
    lines.append(("patient_flow", p["annual_value_usd"] * k, p["soft_value_usd"] * k))

    r = rural.run(seed)
    k = c["affiliated_rural_hospitals"] / rural.TOP_N_CLIENT
    lines.append(("rural", r["annual_value_usd"] * k, r["soft_value_usd"] * k))

    d = denials.run(seed)
    k = c["net_patient_revenue"] / denials.REF_NPR
    partner = denials.PARTNER_COST * (1 + PARTNER_COST_VARIABLE_SHARE * (k - 1))
    lines.append(("denials", d["details"]["gross_value_before_partner_cost"] * k - partner, 0.0))

    a = ai_portfolio.run(seed)
    k = c["net_patient_revenue"] / AI_MODEL_NPR
    in_bundle = {key for key, _, _ in lines}
    overlap = sum(
        max(0.0, v) * k
        for m, v in a["details"]["overlap_net_hard_by_module"].items()
        if m in in_bundle
    )
    lines.append(("ai_portfolio", a["annual_value_usd"] * k - overlap, a["soft_value_usd"] * k))

    hard_total = sum(h for _, h, _ in lines)
    soft_total = sum(s for _, _, s in lines)
    return {
        "client": c,
        "lines": [
            {
                "key": key,
                "module": LABELS[key],
                "hard_value_usd": round(h),
                "soft_value_usd": round(s),
                "scaling": SCALING[key],
            }
            for key, h, s in lines
        ],
        "overlap_removed_usd": round(overlap),
        "hard_total_usd": round(hard_total),
        "soft_total_usd": round(soft_total),
        "supportable_annual_fees_usd": round(max(0.0, hard_total) / ROI_RULE),
        "roi_rule": ROI_RULE,
        "assumptions": ASSUMPTIONS,
        "synthetic_data": True,
    }


def ledger_with_range(seed: int = 42, seeds: Iterable[int] = DEFAULT_SEEDS) -> dict:
    """Ledger at ``seed`` plus P10/P50/P90 of totals and lines across seeds."""
    out = ledger(seed)
    runs = [ledger(s) for s in seeds]
    out["range"] = {
        "n_seeds": len(runs),
        "hard_total": summarize(x["hard_total_usd"] for x in runs),
        "soft_total": summarize(x["soft_total_usd"] for x in runs),
        "lines": {
            line["key"]: summarize(x["lines"][i]["hard_value_usd"] for x in runs)
            for i, line in enumerate(out["lines"])
        },
        "soft_lines": {
            line["key"]: summarize(x["lines"][i]["soft_value_usd"] for x in runs)
            for i, line in enumerate(out["lines"])
        },
    }
    out["supportable_annual_fees_range_usd"] = {
        k: round(max(0, v) / ROI_RULE) for k, v in out["range"]["hard_total"].items()
    }
    return out
