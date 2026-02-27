"""Tests for the identity linter."""

from __future__ import annotations

import pytest

from personanexus.linter import IdentityLinter, LintWarning, _word_overlap_ratio
from personanexus.types import AgentIdentity


@pytest.fixture
def linter():
    return IdentityLinter()


def _minimal_data(**overrides):
    """Return a minimal valid identity dict, with optional overrides."""
    data = {
        "schema_version": "1.0",
        "metadata": {
            "id": "agt_test_001",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test agent",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "draft",
        },
        "role": {
            "title": "Tester",
            "purpose": "Test",
            "scope": {"primary": ["testing"]},
        },
        "personality": {"traits": {"warmth": 0.5, "rigor": 0.5}},
        "communication": {"tone": {"default": "neutral"}},
        "principles": [{"id": "p1", "priority": 1, "statement": "Be good"}],
        "guardrails": {
            "hard": [
                {
                    "id": "no_harm",
                    "rule": "Do no harm",
                    "enforcement": "output_filter",
                    "severity": "critical",
                }
            ]
        },
    }
    data.update(overrides)
    return data


def _make_identity(**overrides) -> AgentIdentity:
    return AgentIdentity.model_validate(_minimal_data(**overrides))


def _rules(warnings: list[LintWarning]) -> list[str]:
    """Extract rule ids from warnings."""
    return [w.rule for w in warnings]


# =========================================================================
# Helper tests
# =========================================================================


class TestWordOverlapRatio:
    def test_identical(self):
        assert _word_overlap_ratio("hello world foo", "hello world foo") == 1.0

    def test_no_overlap(self):
        assert _word_overlap_ratio("alpha beta gamma", "delta epsilon zeta") == 0.0

    def test_partial_overlap(self):
        ratio = _word_overlap_ratio("never generate harmful content", "avoid harmful content")
        assert ratio > 0.6

    def test_empty(self):
        assert _word_overlap_ratio("", "") == 0.0

    def test_short_words_ignored(self):
        # Words < 3 chars are excluded
        assert _word_overlap_ratio("do it", "do it") == 0.0


# =========================================================================
# Rule 1: unused-expertise
# =========================================================================


class TestUnusedExpertise:
    def test_no_domains_no_warning(self, linter: IdentityLinter):
        identity = _make_identity()
        warnings = linter.lint(identity)
        assert "unused-expertise" not in _rules(warnings)

    def test_domain_referenced_in_scope(self, linter: IdentityLinter):
        identity = _make_identity(
            role={
                "title": "Tester",
                "purpose": "Test",
                "scope": {"primary": ["python development"]},
            },
            expertise={
                "domains": [
                    {"name": "Python", "level": 0.9, "category": "primary"},
                ]
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "unused-expertise"]
        assert len(warnings) == 0

    def test_domain_referenced_in_principles(self, linter: IdentityLinter):
        identity = _make_identity(
            principles=[
                {
                    "id": "p1",
                    "priority": 1,
                    "statement": "Apply Python best practices",
                }
            ],
            expertise={
                "domains": [
                    {"name": "Python", "level": 0.9, "category": "primary"},
                ]
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "unused-expertise"]
        assert len(warnings) == 0

    def test_domain_not_referenced(self, linter: IdentityLinter):
        identity = _make_identity(
            expertise={
                "domains": [
                    {
                        "name": "Quantum Computing",
                        "level": 0.9,
                        "category": "primary",
                    },
                ]
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "unused-expertise"]
        assert len(warnings) == 1
        assert "Quantum Computing" in warnings[0].message
        assert warnings[0].severity == "info"
        assert warnings[0].path == "expertise.domains[0].name"


# =========================================================================
# Rule 2: conflicting-tone
# =========================================================================


class TestConflictingTone:
    def test_high_directness_diplomatic(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"directness": 0.9, "warmth": 0.5}},
            communication={"tone": {"default": "diplomatic"}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "conflicting-tone"]
        assert len(warnings) == 1
        assert "directness" in warnings[0].message
        assert warnings[0].severity == "warning"

    def test_high_humor_formal(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"humor": 0.9, "warmth": 0.5}},
            communication={"tone": {"default": "formal"}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "conflicting-tone"]
        assert len(warnings) == 1
        assert "humor" in warnings[0].message

    def test_no_conflict(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"directness": 0.5, "warmth": 0.5}},
            communication={"tone": {"default": "diplomatic"}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "conflicting-tone"]
        assert len(warnings) == 0

    def test_low_warmth_friendly(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"warmth": 0.1, "rigor": 0.5}},
            communication={"tone": {"default": "friendly"}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "conflicting-tone"]
        assert len(warnings) == 1
        assert "warmth" in warnings[0].message

    def test_high_humor_serious(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"humor": 0.95, "warmth": 0.5}},
            communication={"tone": {"default": "serious"}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "conflicting-tone"]
        assert len(warnings) == 1
        assert "humor" in warnings[0].message


# =========================================================================
# Rule 3: guardrail-principle-overlap
# =========================================================================


class TestGuardrailPrincipleOverlap:
    def test_high_overlap_detected(self, linter: IdentityLinter):
        identity = _make_identity(
            principles=[
                {
                    "id": "p1",
                    "priority": 1,
                    "statement": "Never generate harmful or dangerous content for users",
                }
            ],
            guardrails={
                "hard": [
                    {
                        "id": "g1",
                        "rule": "Never generate harmful or dangerous content",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ]
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "guardrail-principle-overlap"]
        assert len(warnings) == 1
        assert "g1" in warnings[0].message
        assert "p1" in warnings[0].message

    def test_no_overlap(self, linter: IdentityLinter):
        identity = _make_identity(
            principles=[
                {
                    "id": "p1",
                    "priority": 1,
                    "statement": "Always prioritize being genuinely helpful",
                }
            ],
            guardrails={
                "hard": [
                    {
                        "id": "g1",
                        "rule": "Do no harm",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ]
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "guardrail-principle-overlap"]
        assert len(warnings) == 0

    def test_soft_guardrail_overlap(self, linter: IdentityLinter):
        identity = _make_identity(
            principles=[
                {
                    "id": "p1",
                    "priority": 1,
                    "statement": "Always provide accurate technical information to users",
                }
            ],
            guardrails={
                "hard": [
                    {
                        "id": "g_hard",
                        "rule": "Do no harm",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ],
                "soft": [
                    {
                        "id": "g_soft",
                        "rule": "Provide accurate technical information to users always",
                        "enforcement": "prompt_instruction",
                    }
                ],
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "guardrail-principle-overlap"]
        assert len(warnings) == 1
        assert "g_soft" in warnings[0].message


# =========================================================================
# Rule 4: empty-section
# =========================================================================


class TestEmptySection:
    def test_no_domains(self, linter: IdentityLinter):
        identity = _make_identity()
        warnings = [w for w in linter.lint(identity) if w.rule == "empty-section"]
        # Should flag: expertise.domains empty, guardrails.soft empty
        rules_with_paths = [(w.rule, w.path) for w in warnings]
        assert ("empty-section", "expertise.domains") in rules_with_paths
        assert ("empty-section", "guardrails.soft") in rules_with_paths

    def test_with_domains_no_warning(self, linter: IdentityLinter):
        identity = _make_identity(
            expertise={
                "domains": [
                    {"name": "Python", "level": 0.9, "category": "primary"},
                ]
            },
        )
        warnings = [
            w
            for w in linter.lint(identity)
            if w.rule == "empty-section" and w.path == "expertise.domains"
        ]
        assert len(warnings) == 0

    def test_empty_vocabulary(self, linter: IdentityLinter):
        identity = _make_identity(
            communication={
                "tone": {"default": "neutral"},
                "vocabulary": {"preferred": [], "avoided": [], "signature_phrases": []},
            },
        )
        warnings = [
            w
            for w in linter.lint(identity)
            if w.rule == "empty-section" and w.path == "communication.vocabulary"
        ]
        assert len(warnings) == 1

    def test_non_empty_vocabulary_no_warning(self, linter: IdentityLinter):
        identity = _make_identity(
            communication={
                "tone": {"default": "neutral"},
                "vocabulary": {"preferred": ["certainly"], "avoided": [], "signature_phrases": []},
            },
        )
        warnings = [
            w
            for w in linter.lint(identity)
            if w.rule == "empty-section" and w.path == "communication.vocabulary"
        ]
        assert len(warnings) == 0


# =========================================================================
# Rule 5: trait-extreme
# =========================================================================


class TestTraitExtreme:
    def test_extreme_zero(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"warmth": 0.0, "rigor": 0.5}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "trait-extreme"]
        assert len(warnings) == 1
        assert "warmth" in warnings[0].message
        assert "0.0" in warnings[0].message
        assert warnings[0].severity == "warning"

    def test_extreme_one(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"warmth": 1.0, "rigor": 0.5}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "trait-extreme"]
        assert len(warnings) == 1
        assert "warmth" in warnings[0].message
        assert "1.0" in warnings[0].message

    def test_multiple_extremes(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"warmth": 0.0, "rigor": 1.0}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "trait-extreme"]
        assert len(warnings) == 2

    def test_no_extremes(self, linter: IdentityLinter):
        identity = _make_identity(
            personality={"traits": {"warmth": 0.5, "rigor": 0.5}},
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "trait-extreme"]
        assert len(warnings) == 0


# =========================================================================
# Rule 6: inconsistent-naming
# =========================================================================


class TestInconsistentNaming:
    def test_matching_name_and_id(self, linter: IdentityLinter):
        identity = _make_identity(
            metadata={
                "id": "agt_test_001",
                "name": "Test",
                "version": "1.0.0",
                "description": "A test agent",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "draft",
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "inconsistent-naming"]
        assert len(warnings) == 0

    def test_mismatched_name_and_id(self, linter: IdentityLinter):
        identity = _make_identity(
            metadata={
                "id": "agt_alpha_001",
                "name": "Bravo",
                "version": "1.0.0",
                "description": "A test agent",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "draft",
            },
        )
        warnings = [w for w in linter.lint(identity) if w.rule == "inconsistent-naming"]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"
        assert "Bravo" in warnings[0].message
        assert "agt_alpha_001" in warnings[0].message

    def test_short_name_no_crash(self, linter: IdentityLinter):
        """Names with only short words (< 3 chars) should not crash."""
        identity = _make_identity(
            metadata={
                "id": "agt_ab_001",
                "name": "Ab",
                "version": "1.0.0",
                "description": "A test agent",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "draft",
            },
        )
        # Should not raise; short names produce no word set so no warning
        warnings = [w for w in linter.lint(identity) if w.rule == "inconsistent-naming"]
        assert len(warnings) == 0


# =========================================================================
# Rule 7: missing-recommended
# =========================================================================


class TestMissingRecommended:
    def test_empty_out_of_scope(self, linter: IdentityLinter):
        identity = _make_identity()
        warnings = [w for w in linter.lint(identity) if w.rule == "missing-recommended"]
        paths = [w.path for w in warnings]
        assert "role.scope.out_of_scope" in paths

    def test_with_out_of_scope(self, linter: IdentityLinter):
        identity = _make_identity(
            role={
                "title": "Tester",
                "purpose": "Test",
                "scope": {
                    "primary": ["testing"],
                    "out_of_scope": ["production deployments"],
                },
            },
        )
        warnings = [
            w
            for w in linter.lint(identity)
            if w.rule == "missing-recommended" and w.path == "role.scope.out_of_scope"
        ]
        assert len(warnings) == 0

    def test_no_audience(self, linter: IdentityLinter):
        identity = _make_identity()
        warnings = [
            w
            for w in linter.lint(identity)
            if w.rule == "missing-recommended" and w.path == "role.audience"
        ]
        assert len(warnings) == 1

    def test_with_audience(self, linter: IdentityLinter):
        identity = _make_identity(
            role={
                "title": "Tester",
                "purpose": "Test",
                "scope": {"primary": ["testing"]},
                "audience": {"primary": "developers"},
            },
        )
        warnings = [
            w
            for w in linter.lint(identity)
            if w.rule == "missing-recommended" and w.path == "role.audience"
        ]
        assert len(warnings) == 0


# =========================================================================
# Integration: lint on a clean identity
# =========================================================================


class TestLintIntegration:
    def test_all_rules_return_lint_warnings(self, linter: IdentityLinter):
        """Every warning should be a LintWarning instance."""
        identity = _make_identity()
        warnings = linter.lint(identity)
        for w in warnings:
            assert isinstance(w, LintWarning)
            assert w.rule
            assert w.message
            assert w.severity in ("info", "warning", "error")

    def test_clean_identity_has_only_info(self, linter: IdentityLinter):
        """A well-configured identity should produce at most info-level warnings."""
        identity = _make_identity(
            role={
                "title": "Tester",
                "purpose": "Test",
                "scope": {
                    "primary": ["testing"],
                    "out_of_scope": ["production"],
                },
                "audience": {"primary": "developers"},
            },
            expertise={
                "domains": [
                    {"name": "Testing", "level": 0.9, "category": "primary"},
                ]
            },
            guardrails={
                "hard": [
                    {
                        "id": "no_harm",
                        "rule": "Do no harm",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ],
                "soft": [
                    {
                        "id": "s1",
                        "rule": "Be polite",
                        "enforcement": "prompt_instruction",
                    }
                ],
            },
        )
        warnings = linter.lint(identity)
        for w in warnings:
            assert w.severity != "error", f"Unexpected error: {w}"


class TestLintFile:
    def test_lint_minimal_example(self, linter: IdentityLinter, minimal_path):
        """Lint the minimal example file without errors."""
        warnings = linter.lint_file(str(minimal_path))
        assert isinstance(warnings, list)
        for w in warnings:
            assert isinstance(w, LintWarning)
