"""Workforce: nurse demand forecasting, premium-labor reduction, retention risk.

Method
------
1. Synthesize two years of daily census for 10 inpatient units (~300 staffed
   beds of a reference ~500-bed hospital) with weekday/seasonal patterns.
2. Rolling-origin back-test over all 13 four-week windows of year 2: for each
   window, forecast census from data available before it (same-weekday mean
   blended with the trailing 4-week level) and convert to RN demand per shift
   using unit nurse:patient ratios. Summing 13 windows = one full year, so no
   seasonal annualization bias.
3. Baseline ("budget grid"): core RNs fixed for the year at 95% of prior-year
   mean demand; gaps covered 30% by overtime (1.5x) and 70% by agency.
   Forecast-driven: core flexed each window to the newsvendor-optimal quantile of forecast demand (1 - staff rate / blended gap rate); a
   SALARIED float pool (paid for idle time, ~80% utilized) covers up to 70% of
   residual gaps; the rest is overtime/agency as in the baseline.
4. Score each RN for 12-month turnover risk with an interpretable logistic
   model whose intercept is calibrated so mean risk = 16.4% (NSI 2025), and size
   the net value of retention outreach to the top-risk decile. Risk scores are
   for unit-level retention planning, not individual employment decisions.

Everything is synthetic; benchmark rates are listed in ASSUMPTIONS.
"""

from __future__ import annotations

import math
import statistics

from .common import metric, result, rng, sigmoid

ASSUMPTIONS = [
    "Reference client: 10 inpatient units, ~300 staffed beds of a ~500-bed hospital; ~1,100 RN headcount hospital-wide (synthetic).",
    "Staff RN fully loaded cost $80/hr; overtime 1.5x ($120/hr); salaried float pool $90/hr paid at ~80% utilization; agency/travel/per-diem blended $105/hr (~31% premium). The 2025 travel RN bill rate is $90.54/hr (SIA/NATHO); loaded staff cost is disputed ($80/hr per a vendor estimate, $94/hr per NATHO), so the premium is the key assumption to calibrate with client timekeeping data.",
    "Baseline: core fixed at 95% of prior-year mean demand; gaps filled 30% overtime / 70% agency.",
    "Forecast-driven: core flexed per 4-week window to the newsvendor-optimal quantile of forecast demand (critical ratio = 1 - staff rate / blended gap-coverage rate) (self-scheduling, flex/per-diem core); float pool covers up to 70% of residual gaps.",
    "RN turnover calibrated to 16.4%/yr (NSI 2025). Replacement cost $40K per RN, i.e. NSI's $61K net of the vacancy premium-labor cover already counted in labor savings.",
    "Targeted retention outreach (stay interviews, schedule fixes) prevents ~25% of predicted departures in the top-risk decile, costing $1,500 per RN contacted.",
    "Each shift = 12 hours, 2 shifts/day; census-to-RN conversion uses unit ratios (ICU 1:2, step-down 1:3, med-surg 1:5).",
    "Individual risk scores raise NLRA/union and disparate-impact considerations (e.g. commute as a proxy); production use should be unit-level and governed.",
]

STAFF_RATE, FLOAT_RATE, AGENCY_RATE = 80.0, 90.0, 105.0
OT_MULTIPLIER = 1.5
OT_SHARE = 0.30
FLOAT_UTILIZATION = 0.80
FLOAT_COVER = 0.70
TARGET_TURNOVER = 0.164
# (label, attribute) swings +/-30%; (label, attribute, low, high) uses sourced values.
SENSITIVITY = [
    ("Agency hourly rate ($90.54 sourced bill rate to $120)", "AGENCY_RATE", 90.54, 120.0),
    ("Staff RN loaded rate ($80 vendor estimate to $94 NATHO)", "STAFF_RATE", 80.0, 94.0),
    ("Float pool utilization (65% to 90%)", "FLOAT_UTILIZATION", 0.65, 0.90),
    ("Share of gaps covered by overtime", "OT_SHARE"),
    ("RN replacement cost", "REPLACEMENT_COST"),
    ("Retention outreach effect", "OUTREACH_EFFECT"),
    ("Baseline RN turnover", "TARGET_TURNOVER"),
]


def gap_rate() -> float:
    """Blended hourly cost of covering one RN-hour of gap above core."""
    return FLOAT_COVER * FLOAT_RATE / FLOAT_UTILIZATION + (1 - FLOAT_COVER) * (
        OT_SHARE * STAFF_RATE * OT_MULTIPLIER + (1 - OT_SHARE) * AGENCY_RATE
    )


def core_quantile() -> float:
    """Newsvendor critical ratio: staff core up to the demand quantile where an
    extra core RN-hour (always paid) costs the same as expected gap coverage."""
    return min(0.95, max(0.05, 1 - STAFF_RATE / gap_rate()))


SHIFT_HOURS = 12
REPLACEMENT_COST = 40_000
OUTREACH_COST = 1_500
OUTREACH_EFFECT = 0.25

UNITS = [
    ("MICU", "ICU", 24, 2),
    ("SICU", "ICU", 20, 2),
    ("CVICU", "ICU", 16, 2),
    ("4 Step-Down", "Step-down", 32, 3),
    ("5 Telemetry", "Step-down", 36, 3),
    ("6 Med-Surg", "Med-surg", 40, 5),
    ("7 Med-Surg", "Med-surg", 40, 5),
    ("8 Ortho", "Med-surg", 30, 5),
    ("9 Oncology", "Med-surg", 32, 5),
    ("10 Observation", "Med-surg", 28, 5),
]


def _census_series(r, beds: int, days: int = 728) -> list[float]:
    """Daily census: base occupancy + weekday effect + winter season + noise."""
    base = beds * r.uniform(0.72, 0.86)
    out = []
    for d in range(days):
        weekday = d % 7
        week_eff = {0: 1.04, 1: 1.05, 2: 1.03, 3: 1.01, 4: 0.98, 5: 0.94, 6: 0.95}[weekday]
        season = 1 + 0.08 * math.cos(2 * math.pi * (d - 20) / 364)  # winter peak
        val = base * week_eff * season + r.gauss(0, beds * 0.05)
        out.append(max(0.0, min(beds, val)))
    return out


def _forecast(hist: list[float], horizon: int = 28) -> list[float]:
    """Seasonal-naive by weekday blended with trailing-4-week level (no trend)."""
    level = statistics.mean(hist[-28:])
    preds = []
    for h in range(horizon):
        t = len(hist) + h
        same_wd = [hist[i] for i in range(t % 7, len(hist), 7)][-4:]
        preds.append(0.6 * statistics.mean(same_wd) + 0.4 * level)
    return preds


def _rn_needed(census: float, ratio: int) -> int:
    return math.ceil(census / ratio)


def _staffing_cost(demand: list[int], core: int, float_cover: float) -> dict:
    """Cost of covering per-shift RN demand given a core level.

    Core is paid whether needed or not. Float-pool hours used are grossed up
    by 1/FLOAT_UTILIZATION because a salaried pool is also paid when idle.
    Remaining gaps: OT_SHARE overtime, the rest agency.
    """
    staff_h = float_h = ot_h = agency_h = 0.0
    for need in demand:
        staff_h += core * SHIFT_HOURS
        gap = max(0, need - core) * SHIFT_HOURS
        f = gap * float_cover
        float_h += f
        rest = gap - f
        ot_h += rest * OT_SHARE
        agency_h += rest * (1 - OT_SHARE)
    cost = (
        staff_h * STAFF_RATE
        + float_h / FLOAT_UTILIZATION * FLOAT_RATE
        + ot_h * STAFF_RATE * OT_MULTIPLIER
        + agency_h * AGENCY_RATE
    )
    return {"cost": cost, "agency_hours": agency_h, "float_hours": float_h, "ot_hours": ot_h}


def _turnover_model(r, n: int = 1100) -> list[dict]:
    nurses = []
    for i in range(n):
        tenure = max(0.1, r.expovariate(1 / 5.0))
        ot = max(0.0, r.gauss(6, 5))  # overtime hrs / 2wk
        changes = r.randint(0, 8)  # last-minute schedule changes / qtr
        vacancy = r.uniform(0.02, 0.22)  # unit vacancy rate
        commute = max(5, r.gauss(25, 12))  # minutes
        z = (
            0.9 * (tenure < 2)
            + 0.06 * ot
            + 0.12 * changes
            + 4.0 * vacancy
            + 0.012 * (commute - 25)
            - 0.04 * min(tenure, 15)
        )
        nurses.append(
            {
                "rn_id": f"RN{i:04d}",
                "tenure_yrs": round(tenure, 1),
                "overtime_hrs_2wk": round(ot, 1),
                "sched_changes_qtr": changes,
                "unit_vacancy": round(vacancy, 3),
                "_z": z,
            }
        )
    # calibrate intercept by bisection so mean risk == TARGET_TURNOVER
    lo, hi = -10.0, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if statistics.mean(sigmoid(nn["_z"] + mid) for nn in nurses) > TARGET_TURNOVER:
            hi = mid
        else:
            lo = mid
    for nn in nurses:
        nn["risk"] = sigmoid(nn.pop("_z") + lo)
        nn["left"] = r.random() < nn["risk"]
    return nurses


def run(seed: int = 42) -> dict:
    r = rng(seed)
    horizon, year = 28, 364
    q = core_quantile()
    unit_rows, totals = [], {"base": 0.0, "fcst": 0.0, "agency_b": 0.0, "agency_f": 0.0}
    abs_err, actual_sum = 0.0, 0.0
    for name, kind, beds, ratio in UNITS:
        series = _census_series(r, beds)
        base_core = math.floor(0.95 * statistics.mean(_rn_needed(c, ratio) for c in series[:year]))
        u_base = u_fcst = 0.0
        f_cores = []
        for w in range(year // horizon):  # 13 rolling-origin windows in year 2
            start = year + w * horizon
            preds = _forecast(series[:start], horizon)
            actual = series[start : start + horizon]
            abs_err += sum(abs(a - p) for a, p in zip(actual, preds))
            actual_sum += sum(actual)
            demand = [_rn_needed(c, ratio) for c in actual for _ in range(2)]
            f_demand = sorted(_rn_needed(c, ratio) for c in preds)
            f_core = f_demand[int(q * (len(f_demand) - 1))]
            f_cores.append(f_core)
            b_ = _staffing_cost(demand, base_core, float_cover=0.0)
            f_ = _staffing_cost(demand, f_core, float_cover=FLOAT_COVER)
            u_base += b_["cost"]
            u_fcst += f_["cost"]
            totals["agency_b"] += b_["agency_hours"]
            totals["agency_f"] += f_["agency_hours"]
        totals["base"] += u_base
        totals["fcst"] += u_fcst
        unit_rows.append(
            {
                "unit": name,
                "type": kind,
                "beds": beds,
                "ratio": f"1:{ratio}",
                "baseline_core_rn": base_core,
                "forecast_core_rn_range": f"{min(f_cores)}-{max(f_cores)}",
                "annual_cost_baseline": round(u_base),
                "annual_cost_forecast": round(u_fcst),
                "annual_savings": round(u_base - u_fcst),
            }
        )
    mape = 100 * abs_err / actual_sum
    labor_savings = totals["base"] - totals["fcst"]

    nurses = _turnover_model(r)
    nurses.sort(key=lambda x: x["risk"], reverse=True)
    decile = nurses[: len(nurses) // 10]
    base_rate = sum(n["left"] for n in nurses) / len(nurses)
    top_rate = sum(n["left"] for n in decile) / len(decile)
    prevented = sum(n["risk"] for n in decile) * OUTREACH_EFFECT
    retention_value = prevented * REPLACEMENT_COST - len(decile) * OUTREACH_COST

    unit_rows.sort(key=lambda x: x["annual_savings"], reverse=True)
    return result(
        key="workforce",
        problem="Clinical workforce shortage, burnout & premium labor cost",
        question="How much premium (agency/overtime) labor and turnover cost can a forecast-driven staffing and targeted retention program remove?",
        headline_metrics=[
            metric("Census forecast error (MAPE, 13 rolling 4-wk windows)", mape, "%"),
            metric("Agency hours avoided / yr", totals["agency_b"] - totals["agency_f"], "hrs"),
            metric("Labor cost savings / yr", labor_savings, "usd"),
            metric(
                "Turnover: top-risk decile vs overall",
                top_rate / base_rate if base_rate else 0,
                "x",
                ".1f",
            ),
            metric("Net retention value / yr", retention_value, "usd"),
        ],
        annual_value_usd=labor_savings + retention_value,
        value_basis="Full-year rolling back-test (13 x 4-week windows) of budget-grid vs forecast-driven staffing across 10 units, plus net value of retention outreach to the top-risk RN decile (replacement cost net of premium cover).",
        assumptions=ASSUMPTIONS,
        table_title="Unit staffing: budget grid vs forecast-driven (full-year back-test)",
        table=unit_rows,
        details={
            "overall_turnover_rate": round(base_rate, 3),
            "top_decile_turnover_rate": round(top_rate, 3),
            "departures_prevented": round(prevented, 1),
            "top_risk_nurses": [
                {k: v for k, v in n.items() if k != "left"} | {"risk": round(n["risk"], 3)}
                for n in decile[:10]
            ],
        },
    )
