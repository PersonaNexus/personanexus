"""Denial prevention & recovery worklist.

Method
------
1. Generate ~5,000 synthetic claims with drivers known to correlate with
   initial denials: payer type (Medicare Advantage vs traditional Medicare vs
   commercial vs Medicaid), prior authorization required/obtained, eligibility
   verification, documentation completeness, coding complexity, days to submit.
2. Score each claim with an interpretable logistic model whose coefficients are
   hand-set and published in ``COEF`` (log-odds). A "true" outcome is simulated
   from a noisier version of the same process so the model is imperfect and the
   AUC is meaningful.
3. Rank a pre-bill worklist by expected value of intervening:
       EV = P(denial) * expected net payment * P(fix succeeds) - rework cost
4. Attribute each simulated denial to its dominant root cause.

ALL DATA IS SYNTHETIC. Coefficients are illustrative, not fitted to real data.
"""

from __future__ import annotations

import math
from collections import Counter

from .common import clamp, metric, result, rng, sigmoid, usd

N_CLAIMS = 5000
REWORK_COST = 57.0  # $ per touched claim (assumed mid-range of $25-$118)
# P(pre-bill fix prevents the denial), by root cause. Missing prior auth often
# cannot be obtained retroactively, so it is much harder to fix than coding.
FIX_SUCCESS = {
    "Authorization / precert": 0.30,
    "Eligibility / registration": 0.75,
    "Medical necessity / documentation": 0.65,
    "Coding": 0.65,
    "Timely filing": 0.65,
    "Payer behavior (other)": 0.30,
}
WRITE_OFF_SHARE = 0.22  # share of denied $ never recovered without intervention
BACKEND_REWORK_MULTIPLIER = 2.0  # back-end appeal/rework costs ~2x a pre-bill touch
PARTNER_COST = 750_000.0  # annual partner / technology cost to run the program
REF_NPR = 1.0e9  # reference health system net patient revenue
WORKLIST_CAPACITY = 0.10  # share of claims pre-bill staff can touch (assumption)

SENSITIVITY = [
    ("Write-off share of denied dollars", "WRITE_OFF_SHARE"),
    ("Pre-bill fix success rates", "FIX_SUCCESS"),
    ("Pre-bill worklist capacity", "WORKLIST_CAPACITY"),
    ("Rework cost per claim", "REWORK_COST"),
    ("Partner / technology cost", "PARTNER_COST"),
]

PAYERS = {  # name: (share of claims, net-to-charge ratio, log-odds offset)
    "Medicare Advantage": (0.25, 0.30, 0.55),
    "Traditional Medicare": (0.22, 0.28, -0.40),
    "Commercial": (0.33, 0.45, 0.20),
    "Medicaid": (0.20, 0.22, 0.35),
}
SERVICE_LINES = {  # name: (mean charge $, prior-auth likelihood)
    "Imaging": (3_500, 0.7),
    "Surgery": (42_000, 0.8),
    "Cardiology": (28_000, 0.6),
    "Oncology": (18_000, 0.75),
    "Emergency": (4_500, 0.05),
    "Behavioral Health": (6_000, 0.4),
    "Inpatient Medicine": (25_000, 0.3),
}

# Interpretable model, log-odds contributions.
INTERCEPT = -3.65
COEF = {
    "missing_prior_auth": 2.2,  # auth required but not obtained
    "eligibility_unverified": 1.3,
    "documentation_gap": 1.6,  # per unit of (1 - completeness)
    "high_coding_complexity": 0.7,
    "late_submission": 0.9,  # submitted > 30 days after service
}
ROOT_CAUSE_LABEL = {
    "missing_prior_auth": "Authorization / precert",
    "eligibility_unverified": "Eligibility / registration",
    "documentation_gap": "Medical necessity / documentation",
    "high_coding_complexity": "Coding",
    "late_submission": "Timely filing",
    "payer": "Payer behavior (other)",
}

ASSUMPTIONS = [
    "5,000 claims are synthetic; payer mix and service-line charges are illustrative.",
    "Model coefficients are hand-set log-odds (see COEF), not trained on real data; MA carries a higher denial offset than traditional Medicare, consistent with industry reports.",
    "Target initial denial rate ~10-12% of claims, in line with published industry surveys.",
    f"Rework cost ${REWORK_COST:.0f}/claim (industry estimates range ~$25-$118).",
    f"Pre-bill team capacity = top {WORKLIST_CAPACITY:.0%} of claims by expected value.",
    "Pre-bill fix success by root cause: authorization 30%, eligibility 75%, coding/documentation/timely filing 65%, other payer behavior 30% (see FIX_SUCCESS).",
    f"Without intervention ~{WRITE_OFF_SHARE:.0%} of denied dollars are ultimately written off; with a ~11% denied-dollar share this implies ~2-2.5% of NPR at risk, near the ~1-2% peer write-off benchmark plus the 2.7% median final-denial rate (Kodiak 2026).",
    f"Back-end rework (appeal after denial) costs {BACKEND_REWORK_MULTIPLIER:.0f}x a pre-bill touch (${REWORK_COST * BACKEND_REWORK_MULTIPLIER:.0f}/claim, within the $25-$118 range).",
    f"Partner / technology cost ${PARTNER_COST / 1e3:,.0f}K per year is subtracted from value (business case recommends delivering with an RCM partner).",
    "Staff productivity is not counted separately (rework cost avoided is already hard value), so soft value = 0.",
    f"Annual value is scaled from the sample to a reference ${REF_NPR / 1e9:.0f}B net-patient-revenue system.",
]


def _features(c: dict) -> dict:
    return {
        "missing_prior_auth": 1.0 if c["auth_required"] and not c["auth_obtained"] else 0.0,
        "eligibility_unverified": 0.0 if c["eligibility_verified"] else 1.0,
        "documentation_gap": 1.0 - c["doc_completeness"],
        "high_coding_complexity": 1.0 if c["coding_complexity"] >= 4 else 0.0,
        "late_submission": 1.0 if c["days_to_submit"] > 30 else 0.0,
    }


def predict(c: dict) -> float:
    f = _features(c)
    z = INTERCEPT + PAYERS[c["payer"]][2] + sum(COEF[k] * v for k, v in f.items())
    return sigmoid(z)


def root_cause(c: dict) -> str:
    f = _features(c)
    contrib = {k: COEF[k] * v for k, v in f.items()}
    k, v = max(contrib.items(), key=lambda kv: kv[1])
    return ROOT_CAUSE_LABEL[k] if v > 0.3 else ROOT_CAUSE_LABEL["payer"]


def _claim(r, i: int) -> dict:
    payer = r.choices(list(PAYERS), weights=[p[0] for p in PAYERS.values()])[0]
    line = r.choice(list(SERVICE_LINES))
    mean_charge, auth_p = SERVICE_LINES[line]
    auth_required = r.random() < auth_p * (1.2 if payer == "Medicare Advantage" else 1.0)
    charge = mean_charge * r.lognormvariate(0, 0.5)
    return {
        "claim_id": f"CL-{i:05d}",
        "payer": payer,
        "service_line": line,
        "charge": round(charge, 2),
        "expected_payment": round(charge * PAYERS[payer][1], 2),
        "auth_required": auth_required,
        "auth_obtained": (not auth_required) or r.random() < 0.88,
        "eligibility_verified": r.random() < 0.93,
        "doc_completeness": round(clamp(r.betavariate(8, 1.5)), 2),
        "coding_complexity": r.randint(1, 5),
        "days_to_submit": int(r.expovariate(1 / 9)),
    }


def auc(scores: list[float], labels: list[int]) -> float:
    """Rank-based AUC (Mann-Whitney U), ties averaged."""
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return 0.5
    rank_sum = sum(rk for rk, y in zip(ranks, labels) if y)
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def run(seed: int = 42) -> dict:
    r = rng(seed)
    claims = [_claim(r, i) for i in range(1, N_CLAIMS + 1)]
    for c in claims:
        c["p_denial"] = predict(c)
        # "Truth" = model log-odds + unobserved noise, so the model is imperfect.
        z = math.log(c["p_denial"] / (1 - c["p_denial"])) + r.gauss(0, 0.9)
        c["denied"] = 1 if r.random() < sigmoid(z) else 0
        c["root_cause"] = root_cause(c)
        c["fix_success"] = FIX_SUCCESS[c["root_cause"]]
        c["ev"] = (
            c["p_denial"] * c["expected_payment"] * WRITE_OFF_SHARE * c["fix_success"] - REWORK_COST
        )

    n_denied = sum(c["denied"] for c in claims)
    denial_rate = n_denied / len(claims)
    model_auc = auc([c["p_denial"] for c in claims], [c["denied"] for c in claims])
    denied_dollars = sum(c["expected_payment"] for c in claims if c["denied"])
    total_expected = sum(c["expected_payment"] for c in claims)
    causes = Counter(c["root_cause"] for c in claims if c["denied"])
    by_payer = {
        p: round(
            100
            * sum(c["denied"] for c in claims if c["payer"] == p)
            / max(1, sum(1 for c in claims if c["payer"] == p)),
            1,
        )
        for p in PAYERS
    }

    ranked = sorted((c for c in claims if c["ev"] > 0), key=lambda c: -c["ev"])
    worklist = ranked[: int(WORKLIST_CAPACITY * len(claims))]
    touched = worklist
    prevented = sum(c["expected_payment"] * c["fix_success"] for c in touched if c["denied"])
    rework = REWORK_COST * len(touched)
    # Value = write-offs avoided on prevented denials + avoided back-end rework.
    avoided_backend_rework = (
        sum(c["fix_success"] for c in touched if c["denied"])
        * REWORK_COST
        * BACKEND_REWORK_MULTIPLIER
    )
    sample_value = prevented * WRITE_OFF_SHARE + avoided_backend_rework - rework
    scale = REF_NPR / total_expected
    gross_value = sample_value * scale
    annual_value = gross_value - PARTNER_COST

    table = [
        {
            "claim": c["claim_id"],
            "payer": c["payer"],
            "service_line": c["service_line"],
            "expected_payment": usd(c["expected_payment"]),
            "p_denial": f"{c['p_denial'] * 100:.0f}%",
            "root_cause": c["root_cause"],
            "fix_success": f"{c['fix_success']:.0%}",
            "expected_value": usd(c["ev"]),
        }
        for c in worklist[:20]
    ]

    return result(
        key="denials",
        problem="Revenue cycle leakage: payer denials & prior-authorization friction",
        question="Which claims should be fixed before billing, and which root causes drive denials by payer?",
        headline_metrics=[
            metric("Claims scored", len(claims)),
            metric("Initial denial rate", denial_rate * 100, "%"),
            metric(
                "Denied $ share of expected payment", 100 * denied_dollars / total_expected, "%"
            ),
            metric("Model AUC", model_auc, "", ".2f"),
            metric("Claims on pre-bill worklist", len(worklist)),
            metric("Medicare Advantage denial rate", by_payer["Medicare Advantage"], "%"),
        ],
        annual_value_usd=annual_value,
        soft_value_usd=0.0,
        value_basis=(
            f"Sample net value {usd(sample_value)} ({WRITE_OFF_SHARE:.0%} write-off avoided on "
            "prevented denials, fix success by root cause, + avoided back-end rework - pre-bill "
            f"rework at ${REWORK_COST:.0f}/claim), scaled x{scale:,.0f} to a "
            f"${REF_NPR / 1e9:.0f}B NPR system ({usd(gross_value)}), minus "
            f"{usd(PARTNER_COST)} partner/technology cost."
        ),
        assumptions=ASSUMPTIONS,
        table_title="Top 20 pre-bill worklist claims (ranked by expected value of intervening)",
        table=table,
        details={
            "intercept": INTERCEPT,
            "coefficients": COEF,
            "payer_offsets": {p: v[2] for p, v in PAYERS.items()},
            "denial_rate_by_payer_pct": by_payer,
            "root_causes": dict(causes.most_common()),
            "worklist_size": len(worklist),
            "gross_value_before_partner_cost": round(gross_value),
            "value_pct_of_npr": round(100 * annual_value / REF_NPR, 3),
            "worklist_share_of_claims_pct": round(100 * len(worklist) / len(claims), 1),
            "worklist_capture_of_denials_pct": round(
                100 * sum(c["denied"] for c in worklist) / max(1, n_denied), 1
            ),
        },
    )
