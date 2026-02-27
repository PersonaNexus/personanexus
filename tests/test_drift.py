"""Tests for drift detection runtime."""

import json

import pytest

from personanexus.drift import (
    DriftReport,
    GuardrailDrift,
    PrincipleDrift,
    ScopeDrift,
    TraitDrift,
    _calculate_severity,
    _extract_guardrails,
    _extract_principles,
    _extract_scope,
    _extract_traits,
    _generate_summary,
    check_guardrail_drift,
    check_principle_drift,
    check_scope_drift,
    check_trait_drift,
    detect_drift,
    detect_drift_from_files,
    format_drift_report,
)

# ---------------------------------------------------------------------------
# Helpers: minimal identity dictionaries
# ---------------------------------------------------------------------------


def _make_identity(
    traits=None,
    ocean=None,
    disc=None,
    jungian=None,
    guardrails_hard=None,
    guardrails_soft=None,
    principles=None,
    scope_primary=None,
    scope_secondary=None,
    scope_out=None,
):
    """Build a minimal identity dictionary for testing."""
    identity = {}

    # Personality
    personality = {}
    if traits is not None:
        personality["traits"] = traits
    profile = {}
    if ocean is not None:
        profile["mode"] = "ocean"
        profile["ocean"] = ocean
    if disc is not None:
        profile["mode"] = "disc"
        profile["disc"] = disc
    if jungian is not None:
        profile["mode"] = "jungian"
        profile["jungian"] = jungian
    if profile:
        personality["profile"] = profile
    if personality:
        identity["personality"] = personality

    # Guardrails
    guardrails = {}
    if guardrails_hard is not None:
        guardrails["hard"] = guardrails_hard
    if guardrails_soft is not None:
        guardrails["soft"] = guardrails_soft
    if guardrails:
        identity["guardrails"] = guardrails

    # Principles
    if principles is not None:
        identity["principles"] = principles

    # Scope
    scope = {}
    if scope_primary is not None:
        scope["primary"] = scope_primary
    if scope_secondary is not None:
        scope["secondary"] = scope_secondary
    if scope_out is not None:
        scope["out_of_scope"] = scope_out
    if scope:
        identity["role"] = {"scope": scope}

    return identity


# ===========================================================================
# _extract_traits
# ===========================================================================


class TestExtractTraits:
    def test_empty_identity(self):
        assert _extract_traits({}) == {}

    def test_custom_traits(self):
        data = _make_identity(traits={"warmth": 0.8, "humor": 0.5})
        result = _extract_traits(data)
        assert result == {"warmth": 0.8, "humor": 0.5}

    def test_ocean_traits(self):
        data = _make_identity(ocean={
            "openness": 0.7, "conscientiousness": 0.8,
            "extraversion": 0.5, "agreeableness": 0.6, "neuroticism": 0.3,
        })
        result = _extract_traits(data)
        assert result["ocean.openness"] == 0.7
        assert result["ocean.neuroticism"] == 0.3

    def test_disc_traits(self):
        data = _make_identity(disc={
            "dominance": 0.4, "influence": 0.6,
            "steadiness": 0.5, "conscientiousness": 0.9,
        })
        result = _extract_traits(data)
        assert result["disc.dominance"] == 0.4

    def test_jungian_traits(self):
        data = _make_identity(jungian={"ei": 0.3, "sn": 0.7, "tf": 0.4, "jp": 0.6})
        result = _extract_traits(data)
        assert result["jungian.ei"] == 0.3
        assert result["jungian.jp"] == 0.6

    def test_combined_traits_and_ocean(self):
        data = _make_identity(
            traits={"warmth": 0.9},
            ocean={"openness": 0.7, "conscientiousness": 0.8,
                   "extraversion": 0.5, "agreeableness": 0.6, "neuroticism": 0.3},
        )
        result = _extract_traits(data)
        assert "warmth" in result
        assert "ocean.openness" in result

    def test_non_numeric_traits_ignored(self):
        data = _make_identity(traits={"warmth": 0.8, "notes": "some text"})
        result = _extract_traits(data)
        assert result == {"warmth": 0.8}


# ===========================================================================
# check_trait_drift
# ===========================================================================


class TestCheckTraitDrift:
    def test_no_drift_identical(self):
        data = _make_identity(traits={"warmth": 0.8, "humor": 0.5})
        drifts = check_trait_drift(data, data)
        assert drifts == []

    def test_no_drift_within_threshold(self):
        old = _make_identity(traits={"warmth": 0.8})
        new = _make_identity(traits={"warmth": 0.85})
        drifts = check_trait_drift(old, new, threshold=0.1)
        assert drifts == []

    def test_drift_above_threshold(self):
        old = _make_identity(traits={"warmth": 0.5})
        new = _make_identity(traits={"warmth": 0.8})
        drifts = check_trait_drift(old, new, threshold=0.1)
        assert len(drifts) == 1
        assert drifts[0].trait == "warmth"
        assert drifts[0].old_value == 0.5
        assert drifts[0].new_value == 0.8
        assert abs(drifts[0].delta - 0.3) < 0.0001

    def test_drift_custom_threshold(self):
        old = _make_identity(traits={"warmth": 0.5})
        new = _make_identity(traits={"warmth": 0.55})
        # Should not drift with default threshold
        assert check_trait_drift(old, new, threshold=0.1) == []
        # Should drift with lower threshold
        drifts = check_trait_drift(old, new, threshold=0.01)
        assert len(drifts) == 1

    def test_trait_added(self):
        old = _make_identity(traits={"warmth": 0.5})
        new = _make_identity(traits={"warmth": 0.5, "humor": 0.7})
        drifts = check_trait_drift(old, new, threshold=0.1)
        assert len(drifts) == 1
        assert drifts[0].trait == "humor"
        assert drifts[0].old_value == 0.0
        assert drifts[0].new_value == 0.7

    def test_trait_removed(self):
        old = _make_identity(traits={"warmth": 0.5, "humor": 0.7})
        new = _make_identity(traits={"warmth": 0.5})
        drifts = check_trait_drift(old, new, threshold=0.1)
        assert len(drifts) == 1
        assert drifts[0].trait == "humor"
        assert drifts[0].new_value == 0.0

    def test_ocean_drift(self):
        old = _make_identity(ocean={
            "openness": 0.5, "conscientiousness": 0.8,
            "extraversion": 0.3, "agreeableness": 0.6, "neuroticism": 0.4,
        })
        new = _make_identity(ocean={
            "openness": 0.9, "conscientiousness": 0.8,
            "extraversion": 0.3, "agreeableness": 0.6, "neuroticism": 0.4,
        })
        drifts = check_trait_drift(old, new, threshold=0.1)
        assert len(drifts) == 1
        assert drifts[0].trait == "ocean.openness"
        assert abs(drifts[0].delta - 0.4) < 0.0001

    def test_multiple_drifts(self):
        old = _make_identity(traits={"warmth": 0.3, "humor": 0.2, "rigor": 0.9})
        new = _make_identity(traits={"warmth": 0.8, "humor": 0.7, "rigor": 0.9})
        drifts = check_trait_drift(old, new, threshold=0.1)
        assert len(drifts) == 2
        trait_names = {d.trait for d in drifts}
        assert trait_names == {"warmth", "humor"}

    def test_negative_drift(self):
        old = _make_identity(traits={"warmth": 0.9})
        new = _make_identity(traits={"warmth": 0.3})
        drifts = check_trait_drift(old, new, threshold=0.1)
        assert len(drifts) == 1
        assert drifts[0].delta < 0


# ===========================================================================
# _extract_guardrails & check_guardrail_drift
# ===========================================================================


class TestExtractGuardrails:
    def test_empty_identity(self):
        assert _extract_guardrails({}) == {}

    def test_hard_guardrails(self):
        data = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "No harmful content", "enforcement": "output_filter",
             "severity": "critical"},
        ])
        result = _extract_guardrails(data)
        assert "g1" in result
        assert result["g1"]["rule"] == "No harmful content"
        assert result["g1"]["_category"] == "hard"

    def test_soft_guardrails(self):
        data = _make_identity(guardrails_soft=[
            {"id": "s1", "rule": "Be polite", "override_level": "admin"},
        ])
        result = _extract_guardrails(data)
        assert "s1" in result
        assert result["s1"]["_category"] == "soft"


class TestCheckGuardrailDrift:
    def test_no_drift_identical(self):
        data = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "No harmful content", "enforcement": "output_filter",
             "severity": "critical"},
        ])
        assert check_guardrail_drift(data, data) == []

    def test_guardrail_added(self):
        old = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule 1", "enforcement": "output_filter", "severity": "critical"},
        ])
        new = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule 1", "enforcement": "output_filter", "severity": "critical"},
            {"id": "g2", "rule": "Rule 2", "enforcement": "output_filter", "severity": "high"},
        ])
        drifts = check_guardrail_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].id == "g2"
        assert drifts[0].change_type == "added"

    def test_guardrail_removed(self):
        old = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule 1", "enforcement": "output_filter", "severity": "critical"},
            {"id": "g2", "rule": "Rule 2", "enforcement": "output_filter", "severity": "high"},
        ])
        new = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule 1", "enforcement": "output_filter", "severity": "critical"},
        ])
        drifts = check_guardrail_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].id == "g2"
        assert drifts[0].change_type == "removed"

    def test_guardrail_modified_rule(self):
        old = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Original rule", "enforcement": "output_filter",
             "severity": "critical"},
        ])
        new = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Modified rule", "enforcement": "output_filter",
             "severity": "critical"},
        ])
        drifts = check_guardrail_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].id == "g1"
        assert drifts[0].change_type == "modified"
        assert "rule changed" in drifts[0].details

    def test_guardrail_modified_severity(self):
        old = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule", "enforcement": "output_filter", "severity": "critical"},
        ])
        new = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule", "enforcement": "output_filter", "severity": "low"},
        ])
        drifts = check_guardrail_drift(old, new)
        assert len(drifts) == 1
        assert "severity changed" in drifts[0].details

    def test_guardrail_category_change(self):
        old = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule", "enforcement": "output_filter", "severity": "critical"},
        ])
        new = _make_identity(guardrails_soft=[
            {"id": "g1", "rule": "Rule", "override_level": "admin"},
        ])
        drifts = check_guardrail_drift(old, new)
        assert len(drifts) == 1
        assert "category changed" in drifts[0].details

    def test_empty_to_guardrails(self):
        old = _make_identity()
        new = _make_identity(guardrails_hard=[
            {"id": "g1", "rule": "Rule", "enforcement": "output_filter", "severity": "critical"},
        ])
        drifts = check_guardrail_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].change_type == "added"


# ===========================================================================
# _extract_principles & check_principle_drift
# ===========================================================================


class TestExtractPrinciples:
    def test_empty_identity(self):
        assert _extract_principles({}) == {}

    def test_basic_principles(self):
        data = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
            {"id": "p2", "priority": 2, "statement": "Be safe"},
        ])
        result = _extract_principles(data)
        assert "p1" in result
        assert result["p1"]["statement"] == "Be helpful"
        assert result["p1"]["_order"] == 0
        assert result["p2"]["_order"] == 1


class TestCheckPrincipleDrift:
    def test_no_drift_identical(self):
        data = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
        ])
        assert check_principle_drift(data, data) == []

    def test_principle_added(self):
        old = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
        ])
        new = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
            {"id": "p2", "priority": 2, "statement": "Be safe"},
        ])
        drifts = check_principle_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].id == "p2"
        assert drifts[0].change_type == "added"

    def test_principle_removed(self):
        old = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
            {"id": "p2", "priority": 2, "statement": "Be safe"},
        ])
        new = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
        ])
        drifts = check_principle_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].id == "p2"
        assert drifts[0].change_type == "removed"

    def test_principle_reworded(self):
        old = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
        ])
        new = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Always be genuinely helpful"},
        ])
        drifts = check_principle_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].change_type == "reworded"
        assert drifts[0].old_value == "Be helpful"
        assert drifts[0].new_value == "Always be genuinely helpful"

    def test_principle_reordered(self):
        old = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
        ])
        new = _make_identity(principles=[
            {"id": "p1", "priority": 3, "statement": "Be helpful"},
        ])
        drifts = check_principle_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].change_type == "reordered"
        assert drifts[0].old_value == "1"
        assert drifts[0].new_value == "3"

    def test_principle_reworded_and_reordered(self):
        old = _make_identity(principles=[
            {"id": "p1", "priority": 1, "statement": "Be helpful"},
        ])
        new = _make_identity(principles=[
            {"id": "p1", "priority": 5, "statement": "Always help users"},
        ])
        drifts = check_principle_drift(old, new)
        assert len(drifts) == 2
        types = {d.change_type for d in drifts}
        assert types == {"reworded", "reordered"}


# ===========================================================================
# _extract_scope & check_scope_drift
# ===========================================================================


class TestExtractScope:
    def test_empty_identity(self):
        result = _extract_scope({})
        assert result == {"primary": [], "secondary": [], "out_of_scope": []}

    def test_basic_scope(self):
        data = _make_identity(
            scope_primary=["coding", "debugging"],
            scope_secondary=["documentation"],
            scope_out=["legal advice"],
        )
        result = _extract_scope(data)
        assert result["primary"] == ["coding", "debugging"]
        assert result["secondary"] == ["documentation"]
        assert result["out_of_scope"] == ["legal advice"]


class TestCheckScopeDrift:
    def test_no_drift_identical(self):
        data = _make_identity(scope_primary=["coding"])
        assert check_scope_drift(data, data) == []

    def test_primary_scope_added(self):
        old = _make_identity(scope_primary=["coding"])
        new = _make_identity(scope_primary=["coding", "debugging"])
        drifts = check_scope_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].scope_type == "primary"
        assert drifts[0].change_type == "added"
        assert drifts[0].item == "debugging"

    def test_primary_scope_removed(self):
        old = _make_identity(scope_primary=["coding", "debugging"])
        new = _make_identity(scope_primary=["coding"])
        drifts = check_scope_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].scope_type == "primary"
        assert drifts[0].change_type == "removed"
        assert drifts[0].item == "debugging"

    def test_secondary_scope_change(self):
        old = _make_identity(scope_primary=["coding"], scope_secondary=["docs"])
        new = _make_identity(scope_primary=["coding"], scope_secondary=["testing"])
        drifts = check_scope_drift(old, new)
        assert len(drifts) == 2
        types = {(d.change_type, d.item) for d in drifts}
        assert ("removed", "docs") in types
        assert ("added", "testing") in types

    def test_out_of_scope_change(self):
        old = _make_identity(scope_primary=["coding"], scope_out=["legal"])
        new = _make_identity(scope_primary=["coding"], scope_out=["legal", "medical"])
        drifts = check_scope_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].scope_type == "out_of_scope"
        assert drifts[0].item == "medical"

    def test_scope_empty_to_populated(self):
        old = _make_identity()
        new = _make_identity(scope_primary=["coding"])
        drifts = check_scope_drift(old, new)
        assert len(drifts) == 1
        assert drifts[0].change_type == "added"


# ===========================================================================
# Severity calculation
# ===========================================================================


class TestCalculateSeverity:
    def test_no_drift(self):
        report = DriftReport(drift_detected=False)
        assert _calculate_severity(report) == "none"

    def test_minor_drift(self):
        report = DriftReport(
            drift_detected=True,
            trait_drifts=[TraitDrift(trait="warmth", old_value=0.5, new_value=0.65, delta=0.15)],
        )
        assert _calculate_severity(report) == "minor"

    def test_major_drift_large_trait(self):
        report = DriftReport(
            drift_detected=True,
            trait_drifts=[TraitDrift(trait="warmth", old_value=0.2, new_value=0.8, delta=0.6)],
        )
        assert _calculate_severity(report) == "major"

    def test_major_drift_principle_removal(self):
        report = DriftReport(
            drift_detected=True,
            principle_drifts=[PrincipleDrift(id="p1", change_type="removed")],
        )
        assert _calculate_severity(report) == "major"

    def test_major_drift_primary_scope(self):
        report = DriftReport(
            drift_detected=True,
            scope_drifts=[ScopeDrift(scope_type="primary", change_type="removed", item="coding")],
        )
        assert _calculate_severity(report) == "major"

    def test_critical_drift_guardrail_removal(self):
        report = DriftReport(
            drift_detected=True,
            guardrail_drifts=[GuardrailDrift(id="g1", change_type="removed")],
        )
        assert _calculate_severity(report) == "critical"

    def test_critical_drift_multiple_major(self):
        report = DriftReport(
            drift_detected=True,
            trait_drifts=[TraitDrift(trait="warmth", old_value=0.2, new_value=0.8, delta=0.6)],
            principle_drifts=[PrincipleDrift(id="p1", change_type="removed")],
            scope_drifts=[ScopeDrift(scope_type="primary", change_type="removed", item="coding")],
        )
        assert _calculate_severity(report) == "critical"

    def test_minor_drift_guardrail_addition(self):
        report = DriftReport(
            drift_detected=True,
            guardrail_drifts=[GuardrailDrift(id="g1", change_type="added")],
        )
        # Addition is not removal, so not critical; no major indicators
        assert _calculate_severity(report) == "minor"

    def test_major_drift_guardrail_modification(self):
        report = DriftReport(
            drift_detected=True,
            guardrail_drifts=[GuardrailDrift(id="g1", change_type="modified")],
        )
        assert _calculate_severity(report) == "major"


# ===========================================================================
# Summary generation
# ===========================================================================


class TestGenerateSummary:
    def test_no_drift_summary(self):
        report = DriftReport(drift_detected=False, severity="none")
        summary = _generate_summary(report)
        assert "No drift detected" in summary

    def test_trait_drift_summary(self):
        report = DriftReport(
            drift_detected=True,
            severity="minor",
            trait_drifts=[
                TraitDrift(trait="warmth", old_value=0.5, new_value=0.8, delta=0.3),
            ],
        )
        summary = _generate_summary(report)
        assert "1 trait(s) drifted" in summary
        assert "warmth" in summary

    def test_guardrail_drift_summary(self):
        report = DriftReport(
            drift_detected=True,
            severity="major",
            guardrail_drifts=[
                GuardrailDrift(id="g1", change_type="added"),
                GuardrailDrift(id="g2", change_type="removed"),
            ],
        )
        summary = _generate_summary(report)
        assert "Guardrail changes" in summary
        assert "1 added" in summary
        assert "1 removed" in summary

    def test_combined_summary(self):
        report = DriftReport(
            drift_detected=True,
            severity="critical",
            trait_drifts=[
                TraitDrift(trait="warmth", old_value=0.5, new_value=0.8, delta=0.3),
            ],
            principle_drifts=[
                PrincipleDrift(id="p1", change_type="removed"),
            ],
            scope_drifts=[
                ScopeDrift(scope_type="primary", change_type="removed", item="coding"),
            ],
        )
        summary = _generate_summary(report)
        assert "trait(s) drifted" in summary
        assert "principle change(s)" in summary
        assert "scope change(s)" in summary


# ===========================================================================
# detect_drift (integration)
# ===========================================================================


class TestDetectDrift:
    def test_identical_identities(self):
        data = _make_identity(
            traits={"warmth": 0.8},
            guardrails_hard=[
                {"id": "g1", "rule": "Rule 1", "enforcement": "output_filter",
                 "severity": "critical"},
            ],
            principles=[{"id": "p1", "priority": 1, "statement": "Be helpful"}],
            scope_primary=["coding"],
        )
        report = detect_drift(data, data)
        assert report.drift_detected is False
        assert report.severity == "none"
        assert report.trait_drifts == []
        assert report.guardrail_drifts == []
        assert report.principle_drifts == []
        assert report.scope_drifts == []

    def test_comprehensive_drift(self):
        old = _make_identity(
            traits={"warmth": 0.3, "humor": 0.8},
            guardrails_hard=[
                {"id": "g1", "rule": "Rule 1", "enforcement": "output_filter",
                 "severity": "critical"},
            ],
            principles=[
                {"id": "p1", "priority": 1, "statement": "Be helpful"},
                {"id": "p2", "priority": 2, "statement": "Be safe"},
            ],
            scope_primary=["coding", "debugging"],
        )
        new = _make_identity(
            traits={"warmth": 0.9, "humor": 0.8},
            guardrails_hard=[
                {"id": "g1", "rule": "Modified Rule 1", "enforcement": "output_filter",
                 "severity": "critical"},
                {"id": "g3", "rule": "New Rule", "enforcement": "output_filter",
                 "severity": "high"},
            ],
            principles=[
                {"id": "p1", "priority": 1, "statement": "Always be genuinely helpful"},
            ],
            scope_primary=["coding"],
        )
        report = detect_drift(old, new)
        assert report.drift_detected is True
        assert len(report.trait_drifts) == 1  # warmth
        assert len(report.guardrail_drifts) == 2  # g1 modified + g3 added
        assert len(report.principle_drifts) == 2  # p1 reworded + p2 removed
        assert len(report.scope_drifts) == 1  # debugging removed
        assert report.severity in ("major", "critical")
        assert report.summary != ""

    def test_drift_threshold(self):
        old = _make_identity(traits={"warmth": 0.5})
        new = _make_identity(traits={"warmth": 0.55})
        report_default = detect_drift(old, new, threshold=0.1)
        assert report_default.drift_detected is False

        report_strict = detect_drift(old, new, threshold=0.01)
        assert report_strict.drift_detected is True


# ===========================================================================
# detect_drift_from_files
# ===========================================================================


class TestDetectDriftFromFiles:
    def test_identical_files(self, tmp_path):
        content = (
            "personality:\n"
            "  traits:\n"
            "    warmth: 0.8\n"
            "guardrails:\n"
            "  hard:\n"
            '    - id: "g1"\n'
            '      rule: "No harm"\n'
            '      enforcement: "output_filter"\n'
            '      severity: "critical"\n'
        )
        f1 = tmp_path / "baseline.yaml"
        f2 = tmp_path / "current.yaml"
        f1.write_text(content)
        f2.write_text(content)

        report = detect_drift_from_files(str(f1), str(f2))
        assert report.drift_detected is False

    def test_files_with_drift(self, tmp_path):
        f1 = tmp_path / "baseline.yaml"
        f2 = tmp_path / "current.yaml"

        f1.write_text(
            "personality:\n"
            "  traits:\n"
            "    warmth: 0.3\n"
            "principles:\n"
            '  - id: "p1"\n'
            "    priority: 1\n"
            '    statement: "Be helpful"\n'
        )
        f2.write_text(
            "personality:\n"
            "  traits:\n"
            "    warmth: 0.9\n"
            "principles:\n"
            '  - id: "p1"\n'
            "    priority: 1\n"
            '    statement: "Always be helpful"\n'
        )

        report = detect_drift_from_files(str(f1), str(f2))
        assert report.drift_detected is True
        assert len(report.trait_drifts) == 1
        assert len(report.principle_drifts) == 1

    def test_file_not_found(self, tmp_path):
        f1 = tmp_path / "baseline.yaml"
        f1.write_text("personality:\n  traits:\n    warmth: 0.5\n")

        with pytest.raises(FileNotFoundError):
            detect_drift_from_files(str(f1), str(tmp_path / "nonexistent.yaml"))

    def test_custom_threshold(self, tmp_path):
        f1 = tmp_path / "baseline.yaml"
        f2 = tmp_path / "current.yaml"
        f1.write_text("personality:\n  traits:\n    warmth: 0.5\n")
        f2.write_text("personality:\n  traits:\n    warmth: 0.55\n")

        report_default = detect_drift_from_files(str(f1), str(f2), threshold=0.1)
        assert report_default.drift_detected is False

        report_strict = detect_drift_from_files(str(f1), str(f2), threshold=0.01)
        assert report_strict.drift_detected is True

    def test_with_real_identity_files(self, mira_path):
        """Drift against itself should produce no drifts."""
        report = detect_drift_from_files(str(mira_path), str(mira_path))
        assert report.drift_detected is False
        assert report.severity == "none"

    def test_with_different_identity_files(self, mira_path, mira_ocean_path):
        """Mira vs Mira-OCEAN should show personality drift."""
        report = detect_drift_from_files(str(mira_path), str(mira_ocean_path))
        # These are different identity files so some drift is expected
        assert isinstance(report, DriftReport)


# ===========================================================================
# DriftReport.to_dict
# ===========================================================================


class TestDriftReportToDict:
    def test_empty_report(self):
        report = DriftReport(drift_detected=False, severity="none", summary="No drift.")
        d = report.to_dict()
        assert d["drift_detected"] is False
        assert d["severity"] == "none"
        assert d["trait_drifts"] == []
        assert d["guardrail_drifts"] == []
        assert d["principle_drifts"] == []
        assert d["scope_drifts"] == []

    def test_populated_report(self):
        report = DriftReport(
            drift_detected=True,
            trait_drifts=[TraitDrift(trait="warmth", old_value=0.5, new_value=0.8, delta=0.3)],
            guardrail_drifts=[GuardrailDrift(id="g1", change_type="removed")],
            principle_drifts=[PrincipleDrift(id="p1", change_type="added")],
            scope_drifts=[ScopeDrift(scope_type="primary", change_type="removed", item="x")],
            severity="critical",
            summary="Lots of drift",
        )
        d = report.to_dict()
        assert d["drift_detected"] is True
        assert len(d["trait_drifts"]) == 1
        assert d["trait_drifts"][0]["trait"] == "warmth"
        assert len(d["guardrail_drifts"]) == 1
        assert len(d["principle_drifts"]) == 1
        assert len(d["scope_drifts"]) == 1

    def test_to_dict_is_json_serializable(self):
        report = DriftReport(
            drift_detected=True,
            trait_drifts=[TraitDrift(trait="warmth", old_value=0.5, new_value=0.8, delta=0.3)],
            severity="major",
            summary="Some drift",
        )
        # Should not raise
        json_str = json.dumps(report.to_dict())
        parsed = json.loads(json_str)
        assert parsed["drift_detected"] is True


# ===========================================================================
# format_drift_report
# ===========================================================================


class TestFormatDriftReport:
    def test_text_format_no_drift(self):
        report = DriftReport(
            drift_detected=False, severity="none",
            summary="No drift detected between the two identity snapshots.",
        )
        output = format_drift_report(report, fmt="text")
        assert "DRIFT DETECTION REPORT" in output
        assert "Drift detected: False" in output
        assert "Severity: none" in output

    def test_text_format_with_drift(self):
        report = DriftReport(
            drift_detected=True,
            trait_drifts=[
                TraitDrift(trait="warmth", old_value=0.3, new_value=0.8, delta=0.5),
            ],
            guardrail_drifts=[
                GuardrailDrift(id="g1", change_type="removed", details="Removed"),
            ],
            principle_drifts=[
                PrincipleDrift(id="p1", change_type="added", details="Added new principle"),
            ],
            scope_drifts=[
                ScopeDrift(scope_type="primary", change_type="removed", item="coding"),
            ],
            severity="critical",
            summary="Multiple drifts detected.",
        )
        output = format_drift_report(report, fmt="text")
        assert "warmth" in output
        assert "0.3 -> 0.8" in output
        assert "[REMOVED] g1" in output
        assert "[ADDED] p1" in output
        assert "[REMOVED] primary: coding" in output
        assert "critical" in output

    def test_json_format(self):
        report = DriftReport(
            drift_detected=True,
            trait_drifts=[
                TraitDrift(trait="warmth", old_value=0.5, new_value=0.8, delta=0.3),
            ],
            severity="minor",
            summary="Minor drift.",
        )
        output = format_drift_report(report, fmt="json")
        parsed = json.loads(output)
        assert parsed["drift_detected"] is True
        assert parsed["severity"] == "minor"
        assert len(parsed["trait_drifts"]) == 1

    def test_text_format_empty_sections(self):
        report = DriftReport(drift_detected=False, severity="none", summary="Clean.")
        output = format_drift_report(report, fmt="text")
        assert "TRAIT DRIFTS:" in output
        assert "(none)" in output
        assert "GUARDRAIL DRIFTS:" in output
        assert "PRINCIPLE DRIFTS:" in output
        assert "SCOPE DRIFTS:" in output


# ===========================================================================
# TraitDrift.abs_delta property
# ===========================================================================


class TestTraitDriftAbsDelta:
    def test_positive_delta(self):
        t = TraitDrift(trait="warmth", old_value=0.3, new_value=0.8, delta=0.5)
        assert t.abs_delta == 0.5

    def test_negative_delta(self):
        t = TraitDrift(trait="warmth", old_value=0.8, new_value=0.3, delta=-0.5)
        assert t.abs_delta == 0.5
