"""Drift detection runtime for PersonaNexus identity files.

Compares two identity snapshots (YAML files) and produces a structured
drift report showing where an agent's configuration has changed from its
declared identity.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Maximum file size to read (10 MB)
_MAX_FILE_SIZE = 10_000_000


# ---------------------------------------------------------------------------
# Drift report data structures
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class TraitDrift:
    """A single personality trait that has drifted."""

    trait: str
    old_value: float
    new_value: float
    delta: float

    @property
    def abs_delta(self) -> float:
        return abs(self.delta)


@dataclasses.dataclass
class GuardrailDrift:
    """A guardrail that was added, removed, or modified."""

    id: str
    change_type: str  # "added" | "removed" | "modified"
    old_rule: str | None = None
    new_rule: str | None = None
    details: str | None = None


@dataclasses.dataclass
class PrincipleDrift:
    """A principle that was added, removed, reordered, or reworded."""

    id: str
    change_type: str  # "added" | "removed" | "reordered" | "reworded"
    old_value: str | None = None
    new_value: str | None = None
    details: str | None = None


@dataclasses.dataclass
class ScopeDrift:
    """A scope change (primary, secondary, or out_of_scope)."""

    scope_type: str  # "primary" | "secondary" | "out_of_scope"
    change_type: str  # "added" | "removed"
    item: str


@dataclasses.dataclass
class DriftReport:
    """Structured report of all detected drift between two identity snapshots."""

    drift_detected: bool
    trait_drifts: list[TraitDrift] = dataclasses.field(default_factory=list)
    guardrail_drifts: list[GuardrailDrift] = dataclasses.field(default_factory=list)
    principle_drifts: list[PrincipleDrift] = dataclasses.field(default_factory=list)
    scope_drifts: list[ScopeDrift] = dataclasses.field(default_factory=list)
    severity: str = "none"  # "none" | "minor" | "major" | "critical"
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary suitable for JSON output."""
        return {
            "drift_detected": self.drift_detected,
            "trait_drifts": [dataclasses.asdict(t) for t in self.trait_drifts],
            "guardrail_drifts": [dataclasses.asdict(g) for g in self.guardrail_drifts],
            "principle_drifts": [dataclasses.asdict(p) for p in self.principle_drifts],
            "scope_drifts": [dataclasses.asdict(s) for s in self.scope_drifts],
            "severity": self.severity,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def _load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dictionary."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    file_size = path.stat().st_size
    if file_size > _MAX_FILE_SIZE:
        raise ValueError(
            f"File {path} is too large ({file_size:,} bytes, max {_MAX_FILE_SIZE:,})"
        )
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at the top level in {path}")
    return data


# ---------------------------------------------------------------------------
# Trait drift detection
# ---------------------------------------------------------------------------


def _extract_traits(data: dict[str, Any]) -> dict[str, float]:
    """Extract personality trait values from an identity dictionary.

    Pulls both explicit traits from ``personality.traits`` and framework
    profile traits (OCEAN, DISC, Jungian) so that drift across any
    personality representation is detected.
    """
    traits: dict[str, float] = {}

    personality = data.get("personality")
    if not isinstance(personality, dict):
        return traits

    # Explicit custom traits
    raw_traits = personality.get("traits")
    if isinstance(raw_traits, dict):
        for k, v in raw_traits.items():
            if isinstance(v, (int, float)):
                traits[k] = float(v)

    # OCEAN profile traits
    profile = personality.get("profile")
    if isinstance(profile, dict):
        ocean = profile.get("ocean")
        if isinstance(ocean, dict):
            for dim in ("openness", "conscientiousness", "extraversion",
                        "agreeableness", "neuroticism"):
                if dim in ocean and isinstance(ocean[dim], (int, float)):
                    traits[f"ocean.{dim}"] = float(ocean[dim])

        disc = profile.get("disc")
        if isinstance(disc, dict):
            for dim in ("dominance", "influence", "steadiness", "conscientiousness"):
                if dim in disc and isinstance(disc[dim], (int, float)):
                    traits[f"disc.{dim}"] = float(disc[dim])

        jungian = profile.get("jungian")
        if isinstance(jungian, dict):
            for dim in ("ei", "sn", "tf", "jp"):
                if dim in jungian and isinstance(jungian[dim], (int, float)):
                    traits[f"jungian.{dim}"] = float(jungian[dim])

    return traits


def check_trait_drift(
    baseline: dict[str, Any],
    current: dict[str, Any],
    threshold: float = 0.1,
) -> list[TraitDrift]:
    """Compare personality trait values between two identity snapshots.

    Returns a list of :class:`TraitDrift` for each trait whose absolute
    change exceeds *threshold*.
    """
    old_traits = _extract_traits(baseline)
    new_traits = _extract_traits(current)

    drifts: list[TraitDrift] = []
    all_keys = sorted(set(old_traits) | set(new_traits))

    for key in all_keys:
        if key in old_traits and key in new_traits:
            delta = new_traits[key] - old_traits[key]
            if abs(delta) > threshold:
                drifts.append(TraitDrift(
                    trait=key,
                    old_value=old_traits[key],
                    new_value=new_traits[key],
                    delta=round(delta, 4),
                ))
        elif key in old_traits:
            # Trait removed
            drifts.append(TraitDrift(
                trait=key,
                old_value=old_traits[key],
                new_value=0.0,
                delta=round(-old_traits[key], 4),
            ))
        else:
            # Trait added
            drifts.append(TraitDrift(
                trait=key,
                old_value=0.0,
                new_value=new_traits[key],
                delta=round(new_traits[key], 4),
            ))

    return drifts


# ---------------------------------------------------------------------------
# Guardrail drift detection
# ---------------------------------------------------------------------------


def _extract_guardrails(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract guardrails keyed by id from an identity dictionary."""
    guardrails_section = data.get("guardrails")
    if not isinstance(guardrails_section, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}

    for category in ("hard", "soft"):
        items = guardrails_section.get(category)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and "id" in item:
                gid = item["id"]
                result[gid] = {**item, "_category": category}

    return result


def check_guardrail_drift(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[GuardrailDrift]:
    """Detect added, removed, or modified guardrails between two snapshots."""
    old_guardrails = _extract_guardrails(baseline)
    new_guardrails = _extract_guardrails(current)

    old_ids = set(old_guardrails)
    new_ids = set(new_guardrails)

    drifts: list[GuardrailDrift] = []

    # Removed guardrails
    for gid in sorted(old_ids - new_ids):
        drifts.append(GuardrailDrift(
            id=gid,
            change_type="removed",
            old_rule=old_guardrails[gid].get("rule"),
            details=f"Guardrail '{gid}' was removed",
        ))

    # Added guardrails
    for gid in sorted(new_ids - old_ids):
        drifts.append(GuardrailDrift(
            id=gid,
            change_type="added",
            new_rule=new_guardrails[gid].get("rule"),
            details=f"Guardrail '{gid}' was added",
        ))

    # Modified guardrails
    for gid in sorted(old_ids & new_ids):
        old_g = old_guardrails[gid]
        new_g = new_guardrails[gid]
        changes: list[str] = []

        if old_g.get("rule") != new_g.get("rule"):
            changes.append("rule changed")
        if old_g.get("enforcement") != new_g.get("enforcement"):
            changes.append("enforcement changed")
        if old_g.get("severity") != new_g.get("severity"):
            changes.append("severity changed")
        if old_g.get("override_level") != new_g.get("override_level"):
            changes.append("override_level changed")
        if old_g.get("_category") != new_g.get("_category"):
            changes.append(
                f"category changed from {old_g.get('_category')} to {new_g.get('_category')}"
            )

        if changes:
            drifts.append(GuardrailDrift(
                id=gid,
                change_type="modified",
                old_rule=old_g.get("rule"),
                new_rule=new_g.get("rule"),
                details="; ".join(changes),
            ))

    return drifts


# ---------------------------------------------------------------------------
# Principle drift detection
# ---------------------------------------------------------------------------


def _extract_principles(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract principles keyed by id from an identity dictionary."""
    principles = data.get("principles")
    if not isinstance(principles, list):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for idx, p in enumerate(principles):
        if isinstance(p, dict) and "id" in p:
            result[p["id"]] = {**p, "_order": idx}

    return result


def check_principle_drift(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[PrincipleDrift]:
    """Detect changes to principles: additions, removals, reordering, rewording."""
    old_principles = _extract_principles(baseline)
    new_principles = _extract_principles(current)

    old_ids = set(old_principles)
    new_ids = set(new_principles)

    drifts: list[PrincipleDrift] = []

    # Removed principles
    for pid in sorted(old_ids - new_ids):
        drifts.append(PrincipleDrift(
            id=pid,
            change_type="removed",
            old_value=old_principles[pid].get("statement"),
            details=f"Principle '{pid}' was removed",
        ))

    # Added principles
    for pid in sorted(new_ids - old_ids):
        drifts.append(PrincipleDrift(
            id=pid,
            change_type="added",
            new_value=new_principles[pid].get("statement"),
            details=f"Principle '{pid}' was added",
        ))

    # Modified / reordered principles
    for pid in sorted(old_ids & new_ids):
        old_p = old_principles[pid]
        new_p = new_principles[pid]

        old_statement = old_p.get("statement", "")
        new_statement = new_p.get("statement", "")

        if old_statement != new_statement:
            drifts.append(PrincipleDrift(
                id=pid,
                change_type="reworded",
                old_value=old_statement,
                new_value=new_statement,
                details=f"Principle '{pid}' statement was reworded",
            ))

        old_priority = old_p.get("priority")
        new_priority = new_p.get("priority")
        if old_priority != new_priority:
            drifts.append(PrincipleDrift(
                id=pid,
                change_type="reordered",
                old_value=str(old_priority),
                new_value=str(new_priority),
                details=(
                    f"Principle '{pid}' priority changed "
                    f"from {old_priority} to {new_priority}"
                ),
            ))

    return drifts


# ---------------------------------------------------------------------------
# Scope drift detection
# ---------------------------------------------------------------------------


def _extract_scope(data: dict[str, Any]) -> dict[str, list[str]]:
    """Extract role scope lists from an identity dictionary."""
    role = data.get("role")
    if not isinstance(role, dict):
        return {"primary": [], "secondary": [], "out_of_scope": []}

    scope = role.get("scope")
    if not isinstance(scope, dict):
        return {"primary": [], "secondary": [], "out_of_scope": []}

    return {
        "primary": scope.get("primary", []) or [],
        "secondary": scope.get("secondary", []) or [],
        "out_of_scope": scope.get("out_of_scope", []) or [],
    }


def check_scope_drift(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[ScopeDrift]:
    """Detect changes to role scope: added or removed scope items."""
    old_scope = _extract_scope(baseline)
    new_scope = _extract_scope(current)

    drifts: list[ScopeDrift] = []

    for scope_type in ("primary", "secondary", "out_of_scope"):
        old_items = set(old_scope.get(scope_type, []))
        new_items = set(new_scope.get(scope_type, []))

        for item in sorted(old_items - new_items):
            drifts.append(ScopeDrift(
                scope_type=scope_type,
                change_type="removed",
                item=item,
            ))

        for item in sorted(new_items - old_items):
            drifts.append(ScopeDrift(
                scope_type=scope_type,
                change_type="added",
                item=item,
            ))

    return drifts


# ---------------------------------------------------------------------------
# Severity calculation
# ---------------------------------------------------------------------------


def _calculate_severity(report: DriftReport) -> str:
    """Determine the overall severity of drift.

    Severity levels:
        - ``none``: no drift detected
        - ``minor``: small trait shifts or cosmetic guardrail/principle tweaks
        - ``major``: significant trait changes, guardrail removals, or principle removals
        - ``critical``: hard guardrail removal or multiple major drifts
    """
    if not report.drift_detected:
        return "none"

    # Check for critical conditions
    hard_guardrail_removed = any(
        g.change_type == "removed"
        for g in report.guardrail_drifts
    )
    if hard_guardrail_removed:
        return "critical"

    major_indicators = 0

    # Large trait drifts (> 0.3) are major
    large_trait_drifts = sum(1 for t in report.trait_drifts if t.abs_delta > 0.3)
    major_indicators += large_trait_drifts

    # Principle removals are major
    principle_removals = sum(
        1 for p in report.principle_drifts if p.change_type == "removed"
    )
    major_indicators += principle_removals

    # Primary scope changes are major
    primary_scope_changes = sum(
        1 for s in report.scope_drifts if s.scope_type == "primary"
    )
    major_indicators += primary_scope_changes

    # Guardrail modifications are somewhat major
    guardrail_modifications = sum(
        1 for g in report.guardrail_drifts if g.change_type == "modified"
    )
    major_indicators += guardrail_modifications

    if major_indicators >= 3:
        return "critical"
    if major_indicators >= 1:
        return "major"

    return "minor"


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------


def _generate_summary(report: DriftReport) -> str:
    """Generate a human-readable summary of the drift report."""
    if not report.drift_detected:
        return "No drift detected between the two identity snapshots."

    parts: list[str] = []

    if report.trait_drifts:
        count = len(report.trait_drifts)
        names = ", ".join(t.trait for t in report.trait_drifts[:3])
        suffix = f" and {count - 3} more" if count > 3 else ""
        parts.append(f"{count} trait(s) drifted ({names}{suffix})")

    if report.guardrail_drifts:
        added = sum(1 for g in report.guardrail_drifts if g.change_type == "added")
        removed = sum(1 for g in report.guardrail_drifts if g.change_type == "removed")
        modified = sum(1 for g in report.guardrail_drifts if g.change_type == "modified")
        guardrail_parts: list[str] = []
        if added:
            guardrail_parts.append(f"{added} added")
        if removed:
            guardrail_parts.append(f"{removed} removed")
        if modified:
            guardrail_parts.append(f"{modified} modified")
        parts.append(f"Guardrail changes: {', '.join(guardrail_parts)}")

    if report.principle_drifts:
        count = len(report.principle_drifts)
        types = {p.change_type for p in report.principle_drifts}
        parts.append(f"{count} principle change(s) ({', '.join(sorted(types))})")

    if report.scope_drifts:
        count = len(report.scope_drifts)
        parts.append(f"{count} scope change(s)")

    return f"Drift detected ({report.severity}): {'; '.join(parts)}."


# ---------------------------------------------------------------------------
# Main drift detection entry point
# ---------------------------------------------------------------------------


def detect_drift(
    baseline: dict[str, Any],
    current: dict[str, Any],
    threshold: float = 0.1,
) -> DriftReport:
    """Compare two identity snapshots and produce a drift report.

    Args:
        baseline: The reference identity dictionary (parsed YAML).
        current: The current identity dictionary (parsed YAML).
        threshold: Minimum trait value change to flag as drift (default 0.1).

    Returns:
        A :class:`DriftReport` with all detected drifts.
    """
    trait_drifts = check_trait_drift(baseline, current, threshold=threshold)
    guardrail_drifts = check_guardrail_drift(baseline, current)
    principle_drifts = check_principle_drift(baseline, current)
    scope_drifts = check_scope_drift(baseline, current)

    drift_detected = bool(
        trait_drifts or guardrail_drifts or principle_drifts or scope_drifts
    )

    report = DriftReport(
        drift_detected=drift_detected,
        trait_drifts=trait_drifts,
        guardrail_drifts=guardrail_drifts,
        principle_drifts=principle_drifts,
        scope_drifts=scope_drifts,
    )

    report.severity = _calculate_severity(report)
    report.summary = _generate_summary(report)

    return report


def detect_drift_from_files(
    baseline_path: str | Path,
    current_path: str | Path,
    threshold: float = 0.1,
) -> DriftReport:
    """Load two YAML files and detect drift between them.

    This is the primary file-based entry point for drift detection.

    Args:
        baseline_path: Path to the reference/baseline identity YAML file.
        current_path: Path to the current identity YAML file.
        threshold: Minimum trait value change to flag as drift (default 0.1).

    Returns:
        A :class:`DriftReport` with all detected drifts.
    """
    baseline = _load_yaml(baseline_path)
    current = _load_yaml(current_path)
    return detect_drift(baseline, current, threshold=threshold)


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def format_drift_report(report: DriftReport, fmt: str = "text") -> str:
    """Format a drift report as text or JSON.

    Args:
        report: The drift report to format.
        fmt: Output format — ``"text"`` or ``"json"``.

    Returns:
        Formatted string.
    """
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2)
    return _format_text(report)


def _format_text(report: DriftReport) -> str:
    """Format a drift report as human-readable text."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("DRIFT DETECTION REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Drift detected: {report.drift_detected}")
    lines.append(f"Severity: {report.severity}")
    lines.append("")

    # Trait drifts
    lines.append("-" * 40)
    lines.append("TRAIT DRIFTS:")
    if report.trait_drifts:
        for t in report.trait_drifts:
            direction = "+" if t.delta > 0 else ""
            lines.append(f"  {t.trait}: {t.old_value} -> {t.new_value} ({direction}{t.delta})")
    else:
        lines.append("  (none)")
    lines.append("")

    # Guardrail drifts
    lines.append("-" * 40)
    lines.append("GUARDRAIL DRIFTS:")
    if report.guardrail_drifts:
        for g in report.guardrail_drifts:
            lines.append(f"  [{g.change_type.upper()}] {g.id}")
            if g.details:
                lines.append(f"    {g.details}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Principle drifts
    lines.append("-" * 40)
    lines.append("PRINCIPLE DRIFTS:")
    if report.principle_drifts:
        for p in report.principle_drifts:
            lines.append(f"  [{p.change_type.upper()}] {p.id}")
            if p.details:
                lines.append(f"    {p.details}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Scope drifts
    lines.append("-" * 40)
    lines.append("SCOPE DRIFTS:")
    if report.scope_drifts:
        for s in report.scope_drifts:
            lines.append(f"  [{s.change_type.upper()}] {s.scope_type}: {s.item}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("-" * 40)
    lines.append(f"Summary: {report.summary}")
    lines.append("=" * 60)

    return "\n".join(lines)
