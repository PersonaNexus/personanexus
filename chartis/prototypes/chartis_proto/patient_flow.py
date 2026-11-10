"""Patient flow: avoidable inpatient days, discharge barriers, ED boarding.

Method
------
1. Synthesize ~6,000 inpatient encounters for a reference ~500-bed hospital
   with DRG-like expected length of stay (GMLOS), payer, discharge
   disposition, and barrier flags (post-acute placement pending, insurance
   auth for SNF, awaiting imaging/consult, no ride/caregiver, guardianship).
2. Excess days = max(0, actual LOS - GMLOS). Attribute excess days to the
   barrier(s) present, weighted by each barrier's typical delay.
3. Barrier playbook: each barrier has an intervention (e.g. early SNF
   referral at day 1, payer auth escalation, weekend imaging, discharge
   lounge + transport) with an assumed % of excess days removed.
   Only barrier-caused delay is attributed: min(excess, barrier delay); the
   rest of the excess is random variation and stays "unexplained".
4. Translate freed bed-days into value. A freed day is either refilled by a
   new admission (capacity value: contribution margin, reported as SOFT value
   because it depends on demand) or left empty (HARD value: variable cost of a
   low-intensity tail day avoided). The two never apply to the same day.
   Capacity value and ED boarding relief only apply when occupancy is >= 85%.
   A readmission offset is subtracted from hard value.
5. Predict on admission which patients are likely to exceed GMLOS by >2
   days (interpretable logistic score) so case managers start early.
"""

from __future__ import annotations

from collections import defaultdict

from .common import clamp, metric, result, rng, sigmoid

ASSUMPTIONS = [
    "Reference client: ~500 staffed beds, ~6,000 sampled discharges scaled to ~37,000 annual discharges (~88% occupancy; reported as a metric).",
    "Variable cost of an avoidable tail day: ~$450 (~15% of ~$3,000 full cost/day; final days of a stay are low-intensity).",
    "Capacity value (SOFT): 50% of freed days are refilled by extra admissions at ~$2,500 contribution margin per case; only if occupancy >= 85%.",
    "Hard value applies only to the 50% of freed days NOT refilled (no double counting of cost and capacity).",
    "Readmission offset: earlier discharge adds 0.5 pt readmission risk for patients whose stay is shortened, at ~$15,000 per readmission.",
    "ED boarding: each staffed bed freed reduces boarding by ~1,200 hours/yr, only if occupancy >= 85%.",
    "Intervention effect sizes (share of barrier-attributed excess days removed): post-acute placement 35%, payer auth 40%, diagnostics 50%, transport/caregiver 60%, guardianship/legal 15%.",
    "Excess day = actual LOS above geometric mean LOS for the DRG-like group (GMLOS).",
]

ANNUAL_DISCHARGES = 37_000
STAFFED_BEDS = 500
CAPACITY_OCC_THRESHOLD = 0.85
VAR_COST_PER_DAY = 450
READMIT_RISK_ADD = 0.005
READMIT_COST = 15_000
MARGIN_PER_CASE = 2_500
MONETIZE_SHARE = 0.5
BOARDING_HRS_PER_BED = 1_200

DRGS = [  # name, GMLOS, share
    ("Sepsis", 4.8, 0.12),
    ("Heart failure", 3.9, 0.09),
    ("Pneumonia", 3.6, 0.08),
    ("COPD", 3.2, 0.06),
    ("Hip/knee replacement", 2.1, 0.07),
    ("Stroke", 3.7, 0.05),
    ("GI bleed", 3.3, 0.05),
    ("Kidney/UTI", 3.4, 0.07),
    ("Cellulitis", 3.5, 0.05),
    ("Chest pain", 1.8, 0.08),
    ("Psych/medical", 5.5, 0.04),
    ("Other medical", 3.8, 0.24),
]

BARRIERS = {
    # key: (label, prevalence driver, typical delay days, intervention, effect)
    "post_acute": (
        "Post-acute (SNF/rehab) placement pending",
        2.6,
        "Day-1 post-acute referral + preferred SNF network",
        0.35,
    ),
    "payer_auth": (
        "Payer authorization for post-acute care",
        1.8,
        "Payer escalation desk / auto-submission",
        0.40,
    ),
    "diagnostics": (
        "Awaiting imaging / consult / procedure",
        1.1,
        "Weekend imaging + consult SLAs",
        0.50,
    ),
    "transport": (
        "No transport / caregiver at discharge",
        0.6,
        "Discharge lounge + ride program",
        0.60,
    ),
    "guardianship": (
        "Guardianship / legal / complex social",
        6.0,
        "Complex-discharge rounds + legal partner",
        0.15,
    ),
}


def _encounters(r, n: int = 6_000) -> list[dict]:
    names = [d[0] for d in DRGS]
    weights = [d[2] for d in DRGS]
    gm = {d[0]: d[1] for d in DRGS}
    out = []
    for i in range(n):
        drg = r.choices(names, weights)[0]
        age = int(clamp(r.gauss(66, 16), 18, 100))
        payer = r.choices(
            ["Medicare", "Medicare Advantage", "Medicaid", "Commercial", "Self-pay"],
            [0.30, 0.22, 0.20, 0.24, 0.04],
        )[0]
        lives_alone = r.random() < (0.35 if age > 75 else 0.18)
        weekend_admit = r.random() < 2 / 7
        p_post = clamp(
            0.04
            + 0.006 * max(0, age - 60)
            + (0.15 if drg in ("Hip/knee replacement", "Stroke") else 0)
        )
        flags = {
            "post_acute": r.random() < p_post,
            "diagnostics": r.random() < (0.22 if weekend_admit else 0.12),
            "transport": r.random() < (0.12 if lives_alone else 0.04),
            "guardianship": r.random() < (0.05 if drg == "Psych/medical" else 0.008),
        }
        flags["payer_auth"] = flags["post_acute"] and r.random() < (
            0.65 if payer == "Medicare Advantage" else 0.25
        )
        delay = sum(BARRIERS[k][1] * r.uniform(0.5, 1.6) for k, v in flags.items() if v)
        los = max(1.0, r.lognormvariate(0, 0.22) * gm[drg] + delay)
        out.append(
            {
                "id": f"E{i:05d}",
                "drg": drg,
                "age": age,
                "payer": payer,
                "lives_alone": lives_alone,
                "weekend_admit": weekend_admit,
                "gmlos": gm[drg],
                "los": round(los, 1),
                "barrier_delay": delay,
                **flags,
            }
        )
    return out


def _risk_score(e: dict) -> float:
    """Admission-time probability of LOS > GMLOS + 2 (no barrier hindsight)."""
    z = (
        -3.2
        + 0.06 * max(0, e["age"] - 60)
        + 0.9 * e["lives_alone"]
        + 0.5 * e["weekend_admit"]
        + 0.6 * (e["payer"] == "Medicare Advantage")
        + 1.2 * (e["drg"] in ("Stroke", "Hip/knee replacement", "Psych/medical"))
    )
    return sigmoid(z)


def _auc(scores: list[float], labels: list[bool]) -> float:
    pairs = sorted(zip(scores, labels))
    pos = sum(labels)
    neg = len(labels) - pos
    rank_sum, i = 0.0, 0
    while i < len(pairs):  # average ranks for ties
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        avg = (i + j + 1) / 2
        rank_sum += avg * sum(1 for k in range(i, j) if pairs[k][1])
        i = j
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg) if pos and neg else 0.5


def run(seed: int = 42) -> dict:
    r = rng(seed)
    enc = _encounters(r)
    scale = ANNUAL_DISCHARGES / len(enc)

    excess_by_barrier: dict[str, float] = defaultdict(float)
    total_excess = unexplained = 0.0
    for e in enc:
        excess = max(0.0, e["los"] - e["gmlos"])
        total_excess += excess
        present = [k for k in BARRIERS if e[k]]
        if not present:
            unexplained += excess
            continue
        attributable = min(excess, e["barrier_delay"])
        unexplained += excess - attributable
        wsum = sum(BARRIERS[k][1] for k in present)
        for k in present:
            excess_by_barrier[k] += attributable * BARRIERS[k][1] / wsum

    rows, days_freed = [], 0.0
    for k, (label, _, action, effect) in BARRIERS.items():
        annual_days = excess_by_barrier[k] * scale
        freed = annual_days * effect
        days_freed += freed
        rows.append(
            {
                "barrier": label,
                "patients_affected_yr": round(sum(e[k] for e in enc) * scale),
                "excess_days_yr": round(annual_days),
                "intervention": action,
                "assumed_effect": f"{effect:.0%}",
                "days_freed_yr": round(freed),
                "value_yr": 0,  # filled below once capacity value is known
            }
        )
    beds_freed = days_freed / 365
    avg_los = sum(e["los"] for e in enc) / len(enc)
    occupancy = ANNUAL_DISCHARGES * avg_los / 365 / STAFFED_BEDS
    constrained = occupancy >= CAPACITY_OCC_THRESHOLD
    refill = MONETIZE_SHARE if constrained else 0.0
    extra_cases = days_freed / avg_los * refill
    patients_shortened = sum(
        r_["patients_affected_yr"] * float(r_["assumed_effect"].rstrip("%")) / 100 for r_ in rows
    )
    readmit_offset = patients_shortened * READMIT_RISK_ADD * READMIT_COST
    cost_value = days_freed * (1 - refill) * VAR_COST_PER_DAY - readmit_offset
    capacity_value = extra_cases * MARGIN_PER_CASE
    boarding_hours = beds_freed * BOARDING_HRS_PER_BED if constrained else 0.0
    for row in rows:  # hard value per barrier, net of its share of readmission offset
        share = row["days_freed_yr"] / days_freed if days_freed else 0
        row["hard_value_yr"] = round(share * cost_value)
        row["soft_capacity_value_yr"] = round(share * capacity_value)
        del row["value_yr"]
    rows.sort(key=lambda x: x["hard_value_yr"] + x["soft_capacity_value_yr"], reverse=True)

    scores = [_risk_score(e) for e in enc]
    labels = [e["los"] > e["gmlos"] + 2 for e in enc]
    auc = _auc(scores, labels)
    flagged = sorted(zip(scores, enc), key=lambda t: t[0], reverse=True)[: len(enc) // 5]
    capture = sum(e["los"] > e["gmlos"] + 2 for _, e in flagged) / max(1, sum(labels))

    return result(
        key="patient_flow",
        problem="Hospital capacity & patient flow (ED boarding, avoidable days, discharge delays)",
        question="Which discharge barriers drive avoidable inpatient days, and what capacity and cost does a targeted barrier playbook release?",
        headline_metrics=[
            metric("Occupancy (modeled)", 100 * occupancy, "%"),
            metric(
                "Avg LOS vs GMLOS", avg_los - sum(e["gmlos"] for e in enc) / len(enc), "days", ".2f"
            ),
            metric("Excess days / yr", total_excess * scale, "days"),
            metric("Days freed by playbook / yr", days_freed, "days"),
            metric("Staffed beds released", beds_freed, "beds", ".1f"),
            metric("ED boarding hours avoided / yr", boarding_hours, "hrs"),
            metric("Admission-time delay model AUC", auc, "", ".2f"),
        ],
        annual_value_usd=cost_value,
        soft_value_usd=capacity_value,
        value_basis="Hard: variable tail-day cost avoided on freed days that are not refilled, minus a readmission offset. Soft: contribution margin of extra admissions on refilled days (only at >=85% occupancy).",
        assumptions=ASSUMPTIONS,
        table_title="Discharge barrier playbook (annualized)",
        table=rows,
        details={
            "unexplained_excess_days_yr": round(unexplained * scale),
            "top_quintile_capture_of_long_stays": round(capture, 3),
            "hard_cost_value": round(cost_value),
            "soft_capacity_value": round(capacity_value),
            "readmission_offset": round(readmit_offset),
            "extra_admissions_absorbed": round(extra_cases),
        },
    )
