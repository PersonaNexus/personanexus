"""CLI: python -m chartis_proto [all|<module>] [--seed N] [--fast] [--json PATH] [--dashboard PATH]

Runs the prototypes, prints a text summary, and optionally writes the JSON
results and/or a self-contained dashboard HTML (data inlined).
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from . import MODULES
from .common import usd

DASH_TEMPLATE = Path(__file__).resolve().parents[2] / "dashboard" / "template.html"


def run_all(names: list[str], seed: int) -> list[dict]:
    out = []
    for n in names:
        try:
            mod = importlib.import_module(f"chartis_proto.{n}")
        except ModuleNotFoundError as exc:  # allow partial builds, but only for the module itself
            if exc.name != f"chartis_proto.{n}":
                raise
            print(f"[skip] {n}: not built yet")
            continue
        out.append(mod.run(seed=seed))
    return out


def summarize(results: list[dict], bundle: dict | None = None) -> str:
    lines = []
    for r in results:
        lines.append(f"\n== {r['problem']} ==")
        lines.append(f"Q: {r['question']}")
        for m in r["headline_metrics"]:
            lines.append(f"  - {m['label']}: {m['display']}")
        lines.append(f"  => Hard annual value (reference client): {usd(r['annual_value_usd'])}")
        lines.append(
            f"  => Soft / capacity value (reported separately): {usd(r['soft_value_usd'])}"
        )
        if "range" in r:
            h = r["range"]["hard"]
            lines.append(
                f"  => Hard value range over {r['range']['n_seeds']} datasets: "
                f"P10 {usd(h['p10'])} / P50 {usd(h['p50'])} / P90 {usd(h['p90'])}"
            )
            top = r["tornado"][0]
            lines.append(
                f"  => Most sensitive assumption: {top['assumption']} "
                f"({top['low_at']}: {usd(top['low'])}, {top['high_at']}: {usd(top['high'])})"
            )
    if bundle:
        lines.append(f"\n== One-client value ledger: {bundle['client']['name']} ==")
        for ln in bundle["lines"]:
            lines.append(
                f"  - {ln['module']}: hard {usd(ln['hard_value_usd'])}, soft {usd(ln['soft_value_usd'])}"
            )
        h = bundle["range"]["hard_total"]
        lines.append(f"  (overlap removed from AI line: {usd(bundle['overlap_removed_usd'])})")
        lines.append(
            f"  => Bundle hard value, seed range: P10 {usd(h['p10'])} / P50 {usd(h['p50'])} / P90 {usd(h['p90'])}"
        )
        ar = bundle["assumption_range"]
        lines.append(
            "  => Bundle hard value, assumption range (each module's top driver at worst / best): "
            f"{usd(ar['low']['hard_total_usd'])} to {usd(ar['high']['hard_total_usd'])}"
        )
        f = bundle["supportable_annual_fees_range_usd"]
        lines.append(
            f"  => Supportable annual fees at {bundle['roi_rule']:.0f}:1: {usd(f['p50'])} "
            f"(assumption range {usd(ar['low']['supportable_annual_fees_usd'])} to "
            f"{usd(ar['high']['supportable_annual_fees_usd'])})"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chartis_proto")
    ap.add_argument("module", nargs="?", default="all", choices=["all", *MODULES])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fast", action="store_true", help="skip ranges, sensitivity and the bundle")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--dashboard", type=Path)
    a = ap.parse_args(argv)
    names = MODULES if a.module == "all" else [a.module]
    results = run_all(names, a.seed)
    bundle_ledger = None
    if not a.fast:
        from . import bundle, sensitivity

        for r in results:
            r.update(sensitivity.analyze(r["key"], a.seed))
        if a.module == "all" and len(results) == len(MODULES):
            bundle_ledger = bundle.ledger_with_range(a.seed)
    print(summarize(results, bundle_ledger))
    payload = json.dumps(
        {"seed": a.seed, "results": results, "bundle": bundle_ledger}, indent=1, default=str
    )
    if a.json:
        a.json.write_text(payload)
        print(f"\nwrote {a.json}")
    if a.dashboard:
        html = DASH_TEMPLATE.read_text().replace(
            "/*__DATA__*/null", payload.replace("</", "<\\/").replace("<!--", "<\\!--")
        )
        a.dashboard.write_text(html)
        print(f"wrote {a.dashboard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
