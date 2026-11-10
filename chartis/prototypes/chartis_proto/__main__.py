"""CLI: python -m chartis_proto [all|<module>] [--seed N] [--json PATH] [--dashboard PATH]

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


def summarize(results: list[dict]) -> str:
    lines = []
    for r in results:
        lines.append(f"\n== {r['problem']} ==")
        lines.append(f"Q: {r['question']}")
        for m in r["headline_metrics"]:
            lines.append(f"  - {m['label']}: {m['display']}")
        lines.append(f"  => Hard annual value (reference client): {usd(r['annual_value_usd'])}")
        lines.append(f"  => Soft / capacity value (reported separately): {usd(r['soft_value_usd'])}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chartis_proto")
    ap.add_argument("module", nargs="?", default="all", choices=["all", *MODULES])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--dashboard", type=Path)
    a = ap.parse_args(argv)
    names = MODULES if a.module == "all" else [a.module]
    results = run_all(names, a.seed)
    print(summarize(results))
    payload = json.dumps({"seed": a.seed, "results": results}, indent=1, default=str)
    if a.json:
        a.json.write_text(payload)
        print(f"\nwrote {a.json}")
    if a.dashboard:
        html = DASH_TEMPLATE.read_text().replace("/*__DATA__*/null", payload.replace("</", "<\\/").replace("<!--", "<\\!--"))
        a.dashboard.write_text(html)
        print(f"wrote {a.dashboard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
