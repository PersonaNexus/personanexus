"""Workforce: nurse demand forecasting, premium-labor reduction, retention risk.

Method
------
1. Synthesize 52 weeks of daily census for ~10 inpatient units of a reference
   ~500-bed hospital (weekday/seasonal patterns + noise).
2. Forecast next-period census per unit with a seasonal-naive + trend blend
   (same weekday, trailing 4-week mean), and convert to required RN FTEs using
   unit-specific nurse:patient ratios.
3. Compare the *reactive* staffing pattern (core staff sized to average census,
   gaps filled with agency/travel at a premium) against a *forecast-driven*
   pattern (core sized to the ~P60 of forecast demand, shared internal float
   pool at a smaller premium, agency only for residual gaps).
4. Score each RN for 12-month turnover risk with an interpretable logistic
   model (tenure, overtime, schedule changes, unit vacancy, commute) and size
   the value of targeted retention outreach.

Everything is synthetic; benchmark rates are listed in ASSUMPTIONS.
"""
from __future__ import annotations

import math
import statistics

from .common import metric, result, rng, sigmoid

ASSUMPTIONS = [
    "Reference client: ~500 staffed beds, ~1,100 RN headcount (synthetic).",
    "Staff RN fully loaded cost $80/hr; internal float pool $90/hr; agency/travel/per-diem blended $105/hr (~31% premium). 2025 travel bill rates are ~13% over loaded staff cost (SIA/NATHO), but short-notice agency, incentive and overtime shifts run higher; the blend is an assumption to calibrate with client timekeeping data.",
    "RN turnover baseline ~16% (NSI 2025: 16.4%); replacement cost per RN ~$61K (NSI 2025: $61,110).",
    "Targeted retention outreach (stay interviews, schedule fixes) prevents ~25% of predicted departures among the top-risk decile it reaches, costing $1,500 per RN contacted.",
    "Forecast-driven model: core staffing sized to ~P60 of forecast demand; float pool covers up to 70% of residual gaps.",
    "Each FTE shift = 12 hours; census-to-RN conversion uses unit nurse:patient ratios (ICU 1:2, step-down 1:3, med-surg 1:5).",
]

STAFF_RATE, FLOAT_RATE, AGENCY_RATE = 80.0, 90.0, 105.0
SHIFT_HOURS = 12
REPLACEMENT_COST = 61_000
OUTREACH_COST = 1_500
OUTREACH_EFFECT = 0.25

UNITS = [
    ("MICU", "ICU", 24, 2), ("SICU", "ICU", 20, 2), ("CVICU", "ICU", 16, 2),
    ("4 Step-Down", "Step-down", 32, 3), ("5 Telemetry", "Step-down", 36, 3),
    ("6 Med-Surg", "Med-surg", 40, 5), ("7 Med-Surg", "Med-surg", 40, 5),
    ("8 Ortho", "Med-surg", 30, 5), ("9 Oncology", "Med-surg", 32, 5),
    ("10 Observation", "Med-surg", 28, 5),
]


def _census_series(r, beds: int, days: int = 364) -> list[float]:
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


def _forecast(series: list[float], horizon: int = 28) -> list[float]:
    """Seasonal-naive by weekday blended with trailing-4-week level."""
    hist = series[:-horizon]
    level = statistics.mean(hist[-28:])
    preds = []
    for h in range(horizon):
        t = len(hist) + h
        same_wd = [hist[i] for i in range(t % 7, len(hist), 7)][-4:]
        preds.append(0.6 * statistics.mean(same_wd) + 0.4 * level)
    return preds


def _rn_needed(census: float, ratio: int) -> int:
    return math.ceil(census / ratio)


def _staffing_cost(demand: list[int], core: int, float_share: float) -> dict:
    """Cost of covering per-shift RN demand given a core level."""
    staff_h = float_h = agency_h = 0.0
    for need in demand:
        staff_h += core * SHIFT_HOURS  # core paid whether needed or not
        gap = max(0, need - core)
        f = gap * float_share
        float_h += f * SHIFT_HOURS
        agency_h += (gap - f) * SHIFT_HOURS
    cost = staff_h * STAFF_RATE + float_h * FLOAT_RATE + agency_h * AGENCY_RATE
    return {"cost": cost, "agency_hours": agency_h, "float_hours": float_h, "staff_hours": staff_h}


def _turnover_model(r, n: int = 1100) -> list[dict]:
    nurses = []
    for i in range(n):
        tenure = max(0.1, r.expovariate(1 / 5.0))
        ot = max(0.0, r.gauss(6, 5))          # overtime hrs / 2wk
        changes = r.randint(0, 8)              # last-minute schedule changes / qtr
        vacancy = r.uniform(0.02, 0.22)        # unit vacancy rate
        commute = max(5, r.gauss(25, 12))      # minutes
        z = (-2.4 + 0.9 * (tenure < 2) + 0.06 * ot + 0.12 * changes
             + 4.0 * vacancy + 0.012 * (commute - 25) - 0.04 * min(tenure, 15))
        p = sigmoid(z)
        nurses.append({
            "rn_id": f"RN{i:04d}", "tenure_yrs": round(tenure, 1), "overtime_hrs_2wk": round(ot, 1),
            "sched_changes_qtr": changes, "unit_vacancy": round(vacancy, 3),
            "risk": p, "left": r.random() < p,
        })
    return nurses


def run(seed: int = 42) -> dict:
    r = rng(seed)
    horizon = 28
    unit_rows, totals = [], {"reactive": 0.0, "forecast": 0.0, "agency_r": 0.0, "agency_f": 0.0}
    abs_err, actual_sum = 0.0, 0.0
    for name, kind, beds, ratio in UNITS:
        series = _census_series(r, beds)
        preds = _forecast(series, horizon)
        actual = series[-horizon:]
        abs_err += sum(abs(a - p) for a, p in zip(actual, preds))
        actual_sum += sum(actual)
        # 2 shifts/day demand (day + night, night ~ same census)
        demand = [_rn_needed(c, ratio) for c in actual for _ in range(2)]
        f_demand = sorted(_rn_needed(c, ratio) for c in preds)
        reactive_core = math.floor(statistics.mean(_rn_needed(c, ratio) for c in series[:-horizon]) * 0.92)
        forecast_core = f_demand[int(0.6 * (len(f_demand) - 1))]
        react = _staffing_cost(demand, reactive_core, float_share=0.0)
        fcst = _staffing_cost(demand, forecast_core, float_share=0.7)
        scale = 364 / horizon  # annualize the 4-week test window
        totals["reactive"] += react["cost"] * scale
        totals["forecast"] += fcst["cost"] * scale
        totals["agency_r"] += react["agency_hours"] * scale
        totals["agency_f"] += fcst["agency_hours"] * scale
        unit_rows.append({
            "unit": name, "type": kind, "beds": beds, "ratio": f"1:{ratio}",
            "reactive_core_rn": reactive_core, "forecast_core_rn": forecast_core,
            "annual_cost_reactive": round(react["cost"] * scale),
            "annual_cost_forecast": round(fcst["cost"] * scale),
            "annual_savings": round((react["cost"] - fcst["cost"]) * scale),
        })
    mape = 100 * abs_err / actual_sum
    labor_savings = totals["reactive"] - totals["forecast"]

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
            metric("Census forecast error (MAPE, 4-wk)", mape, "%"),
            metric("Agency hours avoided / yr", totals["agency_r"] - totals["agency_f"], "hrs"),
            metric("Labor cost savings / yr", labor_savings, "usd"),
            metric("Turnover: top-risk decile vs overall", top_rate / base_rate if base_rate else 0, "x", ".1f"),
            metric("Net retention value / yr", retention_value, "usd"),
        ],
        annual_value_usd=labor_savings + retention_value,
        value_basis="Annualized 4-week back-test of reactive vs forecast-driven staffing across 10 units, plus net value of retention outreach to the top-risk RN decile.",
        assumptions=ASSUMPTIONS,
        table_title="Unit staffing: reactive vs forecast-driven (annualized)",
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
