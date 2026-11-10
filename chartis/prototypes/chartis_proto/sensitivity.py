"""Uncertainty for every prototype: seed ranges and one-at-a-time sensitivity.

Two questions a CFO asks of any point estimate:

1. *How much does it move with the data?*  ``seed_range`` reruns a module on
   many synthetic datasets (seeds) and reports P10 / P50 / P90 of hard and
   soft value.
2. *Which assumption matters most?*  ``tornado`` moves each assumption in the
   module's ``SENSITIVITY`` list one at a time (same seed) and records the
   change in hard value. The move is +/-30%, or sourced low/high values where
   the module supplies them. Shares/probabilities are capped at 0.99.

Seed ranges capture sampling noise only, and their width depends on sample
size. Assumption risk is larger; ``top_drivers`` gives a combined low/high
case for the one-client ledger.

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
    """Scale a float, int or dict of them. Shares (0 < base < 1) are capped at 0.99."""
    if isinstance(base, dict):
        return {k: _scaled(v, factor) for k, v in base.items()}
    new = base * factor
    if 0 < base < 1:  # share or probability
        new = min(0.99, new)
    return type(base)(new) if isinstance(base, int) else new


@contextmanager
def patched_value(mod: ModuleType, attr: str, value):
    """Temporarily set a module-level assumption to ``value``."""
    base = getattr(mod, attr)
    setattr(mod, attr, value)
    try:
        yield
    finally:
        setattr(mod, attr, base)


@contextmanager
def patched(mod: ModuleType, attr: str, factor: float):
    """Temporarily scale a module-level assumption (float, int or dict of them)."""
    with patched_value(mod, attr, _scaled(getattr(mod, attr), factor)):
        yield


def specs(mod: ModuleType, swing: float = SWING) -> list[dict]:
    """Normalize a module's SENSITIVITY list.

    ``(label, attr)`` swings the assumption by +/-swing. ``(label, attr, low, high)``
    uses sourced absolute values instead, which is more honest than a uniform
    percentage when the plausible range is known.
    """
    out = []
    for spec in getattr(mod, "SENSITIVITY", []):
        label, attr = spec[0], spec[1]
        base = getattr(mod, attr)
        if len(spec) == 4:
            low_v, high_v = spec[2], spec[3]
            low_at, high_at = f"{low_v:g}", f"{high_v:g}"
        else:
            low_v, high_v = _scaled(base, 1 - swing), _scaled(base, 1 + swing)
            low_at, high_at = f"-{swing:.0%}", f"+{swing:.0%}"
        out.append(
            {
                "assumption": label,
                "attr": attr,
                "low_value": low_v,
                "high_value": high_v,
                "low_at": low_at,
                "high_at": high_at,
            }
        )
    return out


def tornado(mod: ModuleType, seed: int = 42, swing: float = SWING) -> list[dict]:
    """One-at-a-time swing on each listed assumption; sorted by impact on hard value."""
    base = mod.run(seed=seed)
    rows = []
    for sp in specs(mod, swing):
        with patched_value(mod, sp["attr"], sp["low_value"]):
            low = mod.run(seed=seed)
        with patched_value(mod, sp["attr"], sp["high_value"]):
            high = mod.run(seed=seed)
        rows.append(
            sp
            | {
                "low": round(low["annual_value_usd"]),  # hard value, assumption at its low
                "high": round(high["annual_value_usd"]),  # hard value, assumption at its high
                "base": round(base["annual_value_usd"]),
                "spread": round(abs(high["annual_value_usd"] - low["annual_value_usd"])),
                "soft_low": round(low["soft_value_usd"]),
                "soft_high": round(high["soft_value_usd"]),
            }
        )
    rows.sort(key=lambda x: x["spread"], reverse=True)
    return rows


@contextmanager
def top_drivers(case: str, seed: int = 42):
    """Set every module's most sensitive assumption to its worst or best value.

    ``case`` is "low" (the value that gives less hard value) or "high". Used for
    the assumption range of the one-client ledger.
    """
    undo = []
    try:
        for name in MODULES:
            mod = importlib.import_module(f"chartis_proto.{name}")
            top = tornado(mod, seed)[0]
            worse_is_low = top["low"] <= top["high"]
            pick_low = worse_is_low if case == "low" else not worse_is_low
            undo.append((mod, top["attr"], getattr(mod, top["attr"])))
            setattr(mod, top["attr"], top["low_value"] if pick_low else top["high_value"])
        yield
    finally:
        for mod, attr, base in reversed(undo):
            setattr(mod, attr, base)


def analyze(name: str, seed: int = 42, seeds: Iterable[int] = DEFAULT_SEEDS) -> dict:
    mod = importlib.import_module(f"chartis_proto.{name}")
    return {"range": seed_range(mod, seeds), "tornado": tornado(mod, seed), "swing": SWING}


def analyze_all(seed: int = 42, seeds: Iterable[int] = DEFAULT_SEEDS) -> dict[str, dict]:
    return {n: analyze(n, seed, seeds) for n in MODULES}
