"""Uncertainty for every prototype: seed ranges and one-at-a-time sensitivity.

Two questions a CFO asks of any point estimate:

1. *How much does it move with the data?*  ``seed_range`` reruns a module on
   many synthetic datasets (seeds) and reports P10 / P50 / P90 of hard and
   soft value.
2. *Which assumption matters most?*  ``tornado`` swings each assumption in the
   module's ``SENSITIVITY`` list by +/-30% (one at a time, same seed) and
   records the change in hard value. Shares/probabilities are capped at 0.99.

Neither replaces calibration on client data; they show how fragile or robust
the illustrative numbers are.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from contextlib import contextmanager
from types import ModuleType

from . import MODULES

DEFAULT_SEEDS = range(1, 31)
SWING = 0.30


def _pct(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already sorted list."""
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def summarize(values: Iterable[float]) -> dict:
    v = sorted(values)
    return {"p10": round(_pct(v, 0.1)), "p50": round(_pct(v, 0.5)), "p90": round(_pct(v, 0.9))}


def seed_range(mod: ModuleType, seeds: Iterable[int] = DEFAULT_SEEDS) -> dict:
    runs = [mod.run(seed=s) for s in seeds]
    return {
        "n_seeds": len(runs),
        "hard": summarize(r["annual_value_usd"] for r in runs),
        "soft": summarize(r["soft_value_usd"] for r in runs),
    }


def _scaled(base, factor: float):
    if isinstance(base, dict):
        return {k: _scaled(v, factor) for k, v in base.items()}
    new = base * factor
    if 0 < base <= 1:  # share or probability
        new = min(0.99, new)
    return type(base)(new) if isinstance(base, int) else new


@contextmanager
def patched(mod: ModuleType, attr: str, factor: float):
    """Temporarily scale a module-level assumption (float, int or dict of them)."""
    base = getattr(mod, attr)
    setattr(mod, attr, _scaled(base, factor))
    try:
        yield
    finally:
        setattr(mod, attr, base)


def tornado(mod: ModuleType, seed: int = 42, swing: float = SWING) -> list[dict]:
    """One-at-a-time +/-swing on each listed assumption; sorted by impact."""
    base = mod.run(seed=seed)
    rows = []
    for label, attr in getattr(mod, "SENSITIVITY", []):
        with patched(mod, attr, 1 - swing):
            low = mod.run(seed=seed)
        with patched(mod, attr, 1 + swing):
            high = mod.run(seed=seed)
        rows.append(
            {
                "assumption": label,
                "attr": attr,
                "low": round(low["annual_value_usd"]),  # hard value, assumption at -swing
                "high": round(high["annual_value_usd"]),  # hard value, assumption at +swing
                "base": round(base["annual_value_usd"]),
                "spread": round(abs(high["annual_value_usd"] - low["annual_value_usd"])),
                "soft_low": round(low["soft_value_usd"]),
                "soft_high": round(high["soft_value_usd"]),
            }
        )
    rows.sort(key=lambda x: x["spread"], reverse=True)
    return rows


def analyze(name: str, seed: int = 42, seeds: Iterable[int] = DEFAULT_SEEDS) -> dict:
    mod = importlib.import_module(f"chartis_proto.{name}")
    return {"range": seed_range(mod, seeds), "tornado": tornado(mod, seed), "swing": SWING}


def analyze_all(seed: int = 42, seeds: Iterable[int] = DEFAULT_SEEDS) -> dict[str, dict]:
    return {n: analyze(n, seed, seeds) for n in MODULES}
