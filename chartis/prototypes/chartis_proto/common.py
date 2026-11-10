"""Shared helpers: deterministic synthetic data + the result contract.

ALL DATA IS SYNTHETIC. Benchmarks are illustrative assumptions, documented in
each module's ``ASSUMPTIONS`` list and in docs/business_case.md.
"""
from __future__ import annotations

import math
import random
from typing import Any


def rng(seed: int) -> random.Random:
    return random.Random(seed)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def usd(x: float) -> str:
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e9:
        return f"{sign}${x / 1e9:.2f}B"
    if x >= 1e6:
        return f"{sign}${x / 1e6:.1f}M"
    if x >= 1e3:
        return f"{sign}${x / 1e3:.0f}K"
    return f"{sign}${x:,.0f}"


def metric(label: str, value: float, unit: str = "", fmt: str = "") -> dict:
    if unit == "usd":
        display = usd(value)
    elif unit == "%":
        display = f"{value:.1f}%"
    else:
        display = f"{value:{fmt or ',.0f'}}{(' ' + unit) if unit else ''}"
    return {"label": label, "value": round(value, 4), "unit": unit, "display": display}


def result(
    *,
    key: str,
    problem: str,
    question: str,
    headline_metrics: list[dict],
    annual_value_usd: float,
    value_basis: str,
    assumptions: list[str],
    table_title: str,
    table: list[dict[str, Any]],
    details: dict[str, Any] | None = None,
) -> dict:
    """The contract every prototype returns (consumed by CLI + dashboard)."""
    return {
        "key": key,
        "problem": problem,
        "question": question,
        "headline_metrics": headline_metrics,
        "annual_value_usd": round(annual_value_usd, 2),
        "value_basis": value_basis,
        "assumptions": assumptions,
        "table_title": table_title,
        "table": table,
        "details": details or {},
        "synthetic_data": True,
    }
