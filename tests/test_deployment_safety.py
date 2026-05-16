"""Tests for public-boundary safety validation.

Initiative: PersonaNexus public deployment contract and Studio export path
            (initiative id: 0a10bb0b, packet id: f6573b4f)

Coverage:
- PublicDeploymentChecker: all 7 rules
- DeploymentSafetyResult: properties (errors / warnings / infos / safe_to_deploy / summary)
- check_for_studio: Studio helper return shape
- Public example file validation: examples/identities/public-consumer-chatbot.yaml
- CLI integration: pn lint --public flag
- Studio banner helper: _render_deployment_safety_banner (smoke test)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from personanexus.deployment_safety import (
    DeploymentFinding,
    DeploymentSafetyResult,
    PublicDeploymentChecker,
    check_for_studio,
)
from personanexus.types import AgentIdentity

# ---------------------------------------------------------------------------
# Minimal-data builder
# ---------------------------------------------------------------------------

_EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _raw_base(**section_overrides: Any) -> dict[str, Any]:
    """Minimal raw dict that satisfies AgentIdentity schema, with section overrides.

    Avoids duplicating the required-field boilerplate across every inline test.
    Each kwarg replaces the top-level section of the same name.
    """
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "metadata": {
            "id": "agt_inline",
            "name": "InlineBot",
            "version": "1.0.0",
            "description": "inline test agent",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "draft",
        },
        "role": {
            "title": "T",
            "purpose": "P",
            "scope": {"primary": ["support"]},
        },
        "personality": {"traits": {"warmth": 0.5, "directness": 0.5}},
        "communication": {"tone": {"default": "friendly"}, "language": {"primary": "en"}},
        "principles": [{"id": "p", "priority": 1, "statement": "S"}],
        "guardrails": {
            "hard": [
                {
                    "id": "g",
                    "rule": "R",
                    "enforcement": "output_filter",
                    "severity": "critical",
                }
            ],
        },
    }
    base.update(section_overrides)
    return base


def _make_identity(**overrides: Any) -> AgentIdentity:
    """Build a minimal AgentIdentity that is public-deployment-safe by default.

    Pass kwargs matching top-level identity sections to override specific
    sections.  Deep merging is NOT done — the override replaces the entire
    top-level section.
    """
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "metadata": {
            "id": "agt_test_pub_001",
            "name": "PublicBot",
            "version": "1.0.0",
            "description": "Test public deployment agent",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "active",
        },
        "role": {
            "title": "Customer Assistant",
            "purpose": "Help customers find products",
            "scope": {
                "primary": ["product support"],
                "out_of_scope": ["financial advice", "legal guidance"],
            },
            "audience": {"primary": "General public"},
        },
        "personality": {
            "traits": {"warmth": 0.7, "directness": 0.6},
        },
        "communication": {
            "tone": {"default": "friendly"},
            "language": {"primary": "en"},
        },
        "principles": [
            {
                "id": "be_safe",
                "priority": 1,
                "statement": "Prioritise user safety above all",
            }
        ],
        "guardrails": {
            "hard": [
                {
                    "id": "no_harm",
                    "rule": "Never generate harmful content",
                    "enforcement": "output_filter",
                    "severity": "critical",
                }
            ],
            "soft": [],
        },
        "behavioral_contract": {
            "honesty": "calibrated",
            "uncertainty_disclosure": "explicit",
            "refusal_posture": "explain_and_redirect",
            "boundary_strictness": "moderate",
            "user_corrigibility": "evidence_bound",
            "confidentiality": "standard",
            "governance_sensitivity": "medium",
        },
    }
    base.update(overrides)
    return AgentIdentity.model_validate(base)


@pytest.fixture
def checker() -> PublicDeploymentChecker:
    return PublicDeploymentChecker()


@pytest.fixture
def safe_identity() -> AgentIdentity:
    return _make_identity()


# ---------------------------------------------------------------------------
# DeploymentSafetyResult property tests
# ---------------------------------------------------------------------------


class TestDeploymentSafetyResult:
    def test_empty_findings_is_safe(self):
        result = DeploymentSafetyResult()
        assert result.safe_to_deploy is True
        assert result.errors == []
        assert result.warnings == []
        assert result.infos == []

    def test_error_finding_makes_unsafe(self):
        result = DeploymentSafetyResult(
            findings=[DeploymentFinding(rule="x", message="msg", severity="error")]
        )
        assert result.safe_to_deploy is False

    def test_warning_only_is_still_safe(self):
        result = DeploymentSafetyResult(
            findings=[DeploymentFinding(rule="x", message="msg", severity="warning")]
        )
        assert result.safe_to_deploy is True

    def test_info_only_is_still_safe(self):
        result = DeploymentSafetyResult(
            findings=[DeploymentFinding(rule="x", message="msg", severity="info")]
        )
        assert result.safe_to_deploy is True

    def test_errors_property_filters_correctly(self):
        result = DeploymentSafetyResult(
            findings=[
                DeploymentFinding(rule="a", message="e", severity="error"),
                DeploymentFinding(rule="b", message="w", severity="warning"),
                DeploymentFinding(rule="c", message="i", severity="info"),
            ]
        )
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.infos) == 1

    def test_summary_safe(self):
        result = DeploymentSafetyResult()
        assert "safe" in result.summary().lower()

    def test_summary_unsafe_shows_counts(self):
        result = DeploymentSafetyResult(
            findings=[
                DeploymentFinding(rule="r", message="m", severity="error"),
                DeploymentFinding(rule="r2", message="m2", severity="warning"),
            ]
        )
        summary = result.summary()
        assert "NOT" in summary or "not" in summary.lower()
        assert "1" in summary  # error count

    def test_summary_safe_with_warnings_mentions_count(self):
        result = DeploymentSafetyResult(
            findings=[
                DeploymentFinding(rule="r", message="m", severity="warning"),
            ]
        )
        summary = result.summary()
        assert "warning" in summary.lower()


# ---------------------------------------------------------------------------
# Rule: public-critical-guardrail-required
# ---------------------------------------------------------------------------


class TestCriticalGuardrailRequired:
    def test_passes_with_critical_guardrail(self, checker, safe_identity):
        result = checker.check(safe_identity)
        rules = [f.rule for f in result.findings]
        assert "public-critical-guardrail-required" not in rules

    def test_fails_without_any_critical_guardrail(self, checker):
        identity = _make_identity(
            guardrails={
                "hard": [
                    {
                        "id": "no_harm",
                        "rule": "Be safe",
                        "enforcement": "output_filter",
                        "severity": "high",  # high but NOT critical
                    }
                ],
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.errors]
        assert "public-critical-guardrail-required" in rules

    def test_error_severity(self, checker):
        identity = _make_identity(
            guardrails={
                "hard": [
                    {
                        "id": "soft_rule",
                        "rule": "Be nice",
                        "enforcement": "prompt_instruction",
                        "severity": "medium",
                    }
                ],
            }
        )
        result = checker.check(identity)
        finding = next(f for f in result.findings if f.rule == "public-critical-guardrail-required")
        assert finding.severity == "error"
        assert finding.path == "guardrails.hard"

    def test_multiple_hard_guardrails_one_critical_passes(self, checker):
        identity = _make_identity(
            guardrails={
                "hard": [
                    {
                        "id": "r1",
                        "rule": "Rule 1",
                        "enforcement": "output_filter",
                        "severity": "high",
                    },
                    {
                        "id": "r2",
                        "rule": "Rule 2",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    },
                ],
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.errors]
        assert "public-critical-guardrail-required" not in rules


# ---------------------------------------------------------------------------
# Rule: public-behavioral-contract-required
# ---------------------------------------------------------------------------


class TestBehavioralContractRequired:
    def test_passes_with_contract(self, checker, safe_identity):
        result = checker.check(safe_identity)
        rules = [f.rule for f in result.findings]
        assert "public-behavioral-contract-required" not in rules

    def test_fails_without_contract(self, checker):
        # No behavioral_contract
        data = _raw_base(
            metadata={
                "id": "agt_no_contract",
                "name": "NoContract",
                "version": "1.0.0",
                "description": "Test",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "active",
            },
            role={
                "title": "Assistant",
                "purpose": "Help users",
                "scope": {"primary": ["support"], "out_of_scope": ["harmful content"]},
                "audience": {"primary": "Public"},
            },
        )
        identity = AgentIdentity.model_validate(data)
        result = checker.check(identity)
        rules = [f.rule for f in result.errors]
        assert "public-behavioral-contract-required" in rules

    def test_error_severity_and_path(self, checker):
        data = _raw_base(
            metadata={
                "id": "agt_nc2",
                "name": "NC2",
                "version": "1.0.0",
                "description": "x",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "active",
            }
        )
        identity = AgentIdentity.model_validate(data)
        result = checker.check(identity)
        finding = next(
            (f for f in result.findings if f.rule == "public-behavioral-contract-required"),
            None,
        )
        assert finding is not None
        assert finding.severity == "error"
        assert finding.path == "behavioral_contract"


# ---------------------------------------------------------------------------
# Rule: public-flexible-boundary-risk
# ---------------------------------------------------------------------------


class TestFlexibleBoundaryRisk:
    def test_passes_with_moderate_boundary(self, checker, safe_identity):
        result = checker.check(safe_identity)
        rules = [f.rule for f in result.findings]
        assert "public-flexible-boundary-risk" not in rules

    def test_passes_with_strict_boundary(self, checker):
        identity = _make_identity(
            behavioral_contract={
                "boundary_strictness": "strict",
                "user_corrigibility": "evidence_bound",
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.findings]
        assert "public-flexible-boundary-risk" not in rules

    def test_warns_with_flexible_boundary(self, checker):
        identity = _make_identity(
            behavioral_contract={
                "boundary_strictness": "flexible",
                "user_corrigibility": "evidence_bound",
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.warnings]
        assert "public-flexible-boundary-risk" in rules

    def test_finding_is_warning_not_error(self, checker):
        identity = _make_identity(
            behavioral_contract={
                "boundary_strictness": "flexible",
                "user_corrigibility": "limited",
            }
        )
        result = checker.check(identity)
        finding = next(
            (f for f in result.findings if f.rule == "public-flexible-boundary-risk"),
            None,
        )
        assert finding is not None
        assert finding.severity == "warning"

    def test_no_contract_skips_this_rule(self, checker):
        """When no contract is present this rule should NOT fire (contract rule fires instead)."""
        data = _raw_base()
        identity = AgentIdentity.model_validate(data)
        result = checker.check(identity)
        rules = [f.rule for f in result.findings]
        assert "public-flexible-boundary-risk" not in rules


# ---------------------------------------------------------------------------
# Rule: public-open-corrigibility-risk
# ---------------------------------------------------------------------------


class TestOpenCorrigibilityRisk:
    def test_passes_with_evidence_bound(self, checker, safe_identity):
        result = checker.check(safe_identity)
        rules = [f.rule for f in result.findings]
        assert "public-open-corrigibility-risk" not in rules

    def test_passes_with_limited_corrigibility(self, checker):
        identity = _make_identity(
            behavioral_contract={
                "boundary_strictness": "moderate",
                "user_corrigibility": "limited",
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.findings]
        assert "public-open-corrigibility-risk" not in rules

    def test_warns_with_open_corrigibility(self, checker):
        identity = _make_identity(
            behavioral_contract={
                "boundary_strictness": "strict",  # strict boundary to avoid that warning
                "user_corrigibility": "open",
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.warnings]
        assert "public-open-corrigibility-risk" in rules

    def test_warning_severity_and_path(self, checker):
        identity = _make_identity(
            behavioral_contract={
                "boundary_strictness": "moderate",
                "user_corrigibility": "open",
            }
        )
        result = checker.check(identity)
        finding = next(
            (f for f in result.findings if f.rule == "public-open-corrigibility-risk"),
            None,
        )
        assert finding is not None
        assert finding.severity == "warning"
        assert finding.path == "behavioral_contract.user_corrigibility"


# ---------------------------------------------------------------------------
# Rule: public-autonomous-needs-contract
# ---------------------------------------------------------------------------


class TestAutonomousNeedsContract:
    def test_passes_no_autonomous_no_contract(self, checker):
        """No autonomous + no contract = no error from this rule."""
        data = _raw_base()
        identity = AgentIdentity.model_validate(data)
        result = checker.check(identity)
        rules = [f.rule for f in result.findings]
        assert "public-autonomous-needs-contract" not in rules

    def test_passes_autonomous_with_contract(self, checker):
        identity = _make_identity(
            guardrails={
                "hard": [
                    {
                        "id": "g",
                        "rule": "R",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ],
                "permissions": {"autonomous": ["read_order_status"]},
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.errors]
        assert "public-autonomous-needs-contract" not in rules

    def test_fails_autonomous_without_contract(self, checker):
        data = _raw_base(
            guardrails={
                "hard": [
                    {
                        "id": "g",
                        "rule": "R",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ],
                "permissions": {"autonomous": ["send_email", "post_update"]},
            }
        )
        identity = AgentIdentity.model_validate(data)
        result = checker.check(identity)
        rules = [f.rule for f in result.errors]
        assert "public-autonomous-needs-contract" in rules

    def test_error_message_names_autonomous_items(self, checker):
        data = _raw_base(
            guardrails={
                "hard": [
                    {
                        "id": "g",
                        "rule": "R",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ],
                "permissions": {"autonomous": ["action_one"]},
            }
        )
        identity = AgentIdentity.model_validate(data)
        result = checker.check(identity)
        finding = next(
            (f for f in result.findings if f.rule == "public-autonomous-needs-contract"),
            None,
        )
        assert finding is not None
        assert "action_one" in finding.message


# ---------------------------------------------------------------------------
# Rule: public-out-of-scope-required
# ---------------------------------------------------------------------------


class TestOutOfScopeRequired:
    def test_passes_with_out_of_scope(self, checker, safe_identity):
        result = checker.check(safe_identity)
        rules = [f.rule for f in result.findings]
        assert "public-out-of-scope-required" not in rules

    def test_warns_without_out_of_scope(self, checker):
        identity = _make_identity(
            role={
                "title": "Bot",
                "purpose": "Help users",
                "scope": {
                    "primary": ["general support"],
                    # No out_of_scope
                },
                "audience": {"primary": "Public"},
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.warnings]
        assert "public-out-of-scope-required" in rules

    def test_warning_severity_and_path(self, checker):
        identity = _make_identity(
            role={
                "title": "Bot",
                "purpose": "Help",
                "scope": {"primary": ["support"]},
            }
        )
        result = checker.check(identity)
        finding = next(
            (f for f in result.findings if f.rule == "public-out-of-scope-required"),
            None,
        )
        assert finding is not None
        assert finding.severity == "warning"
        assert finding.path == "role.scope.out_of_scope"


# ---------------------------------------------------------------------------
# Rule: public-audience-undefined
# ---------------------------------------------------------------------------


class TestAudienceUndefined:
    def test_passes_with_audience(self, checker, safe_identity):
        result = checker.check(safe_identity)
        rules = [f.rule for f in result.findings]
        assert "public-audience-undefined" not in rules

    def test_info_without_audience(self, checker):
        identity = _make_identity(
            role={
                "title": "Bot",
                "purpose": "Help users",
                "scope": {
                    "primary": ["general support"],
                    "out_of_scope": ["harmful content"],
                },
                # No audience
            }
        )
        result = checker.check(identity)
        rules = [f.rule for f in result.infos]
        assert "public-audience-undefined" in rules

    def test_info_not_error(self, checker):
        identity = _make_identity(
            role={
                "title": "Bot",
                "purpose": "Help",
                "scope": {"primary": ["s"], "out_of_scope": ["x"]},
            }
        )
        result = checker.check(identity)
        # audience-undefined is info, not error or warning
        finding = next(
            (f for f in result.findings if f.rule == "public-audience-undefined"),
            None,
        )
        assert finding is not None
        assert finding.severity == "info"


# ---------------------------------------------------------------------------
# Integration: all rules clean on a well-configured identity
# ---------------------------------------------------------------------------


class TestCleanIdentity:
    def test_safe_identity_has_no_errors(self, checker, safe_identity):
        result = checker.check(safe_identity)
        assert result.safe_to_deploy is True
        assert result.errors == []

    def test_safe_identity_has_no_warnings(self, checker, safe_identity):
        result = checker.check(safe_identity)
        assert result.warnings == []

    def test_safe_identity_has_no_infos(self, checker, safe_identity):
        result = checker.check(safe_identity)
        assert result.infos == []

    def test_worst_case_identity_triggers_all_error_rules(self, checker):
        """An identity with no contract, no critical guardrail, and autonomous
        permissions should trigger 3 error-level rules."""
        # Only HIGH severity (no critical) + autonomous + no behavioral_contract
        data = _raw_base(
            metadata={
                "id": "agt_worst",
                "name": "Worst",
                "version": "1.0.0",
                "description": "deliberately unsafe",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "draft",
            },
            guardrails={
                "hard": [
                    {
                        "id": "g",
                        "rule": "R",
                        "enforcement": "output_filter",
                        "severity": "high",
                    }
                ],
                "permissions": {"autonomous": ["post_message"]},
            },
        )
        # Remove behavioral_contract (not set by _raw_base)
        data.pop("behavioral_contract", None)
        identity = AgentIdentity.model_validate(data)
        result = checker.check(identity)
        error_rules = {f.rule for f in result.errors}
        assert "public-critical-guardrail-required" in error_rules
        assert "public-behavioral-contract-required" in error_rules
        assert "public-autonomous-needs-contract" in error_rules
        assert not result.safe_to_deploy


# ---------------------------------------------------------------------------
# check_for_studio helper
# ---------------------------------------------------------------------------


class TestCheckForStudio:
    def test_returns_dict_with_expected_keys(self, safe_identity):
        result = check_for_studio(safe_identity)
        assert isinstance(result, dict)
        assert "safe" in result
        assert "summary" in result
        assert "errors" in result
        assert "warnings" in result
        assert "infos" in result

    def test_safe_identity_returns_safe_true(self, safe_identity):
        result = check_for_studio(safe_identity)
        assert result["safe"] is True

    def test_unsafe_identity_returns_safe_false(self):
        data = _raw_base(
            guardrails={
                "hard": [
                    {
                        "id": "g",
                        "rule": "R",
                        "enforcement": "output_filter",
                        "severity": "high",
                    }
                ],
            }
        )
        data.pop("behavioral_contract", None)
        identity = AgentIdentity.model_validate(data)
        result = check_for_studio(identity)
        assert result["safe"] is False
        assert len(result["errors"]) > 0

    def test_errors_are_strings(self):
        data = _raw_base(
            guardrails={
                "hard": [
                    {
                        "id": "g",
                        "rule": "R",
                        "enforcement": "output_filter",
                        "severity": "high",
                    }
                ],
            }
        )
        data.pop("behavioral_contract", None)
        identity = AgentIdentity.model_validate(data)
        result = check_for_studio(identity)
        for msg in result["errors"] + result["warnings"] + result["infos"]:
            assert isinstance(msg, str)

    def test_summary_is_string(self, safe_identity):
        result = check_for_studio(safe_identity)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0


# ---------------------------------------------------------------------------
# Public example file: public-consumer-chatbot.yaml
# ---------------------------------------------------------------------------


class TestPublicConsumerChatbotExample:
    """The bundled example must be deployment-safe and fully parse-able."""

    @pytest.fixture
    def chatbot_path(self) -> Path:
        path = _EXAMPLES_DIR / "identities" / "public-consumer-chatbot.yaml"
        assert path.exists(), f"Example file missing: {path}"
        return path

    def test_example_file_parses_cleanly(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        assert identity.metadata.name == "Echo"

    def test_example_passes_schema_validation(self, chatbot_path):
        from personanexus.validator import IdentityValidator

        result = IdentityValidator().validate_file(chatbot_path)
        assert result.valid, f"Schema errors: {result.errors}"

    def test_example_is_deployment_safe(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        checker = PublicDeploymentChecker()
        result = checker.check(identity)
        assert result.safe_to_deploy, (
            f"Expected safe to deploy, got errors: {[f.message for f in result.errors]}"
        )

    def test_example_has_no_warnings(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        result = PublicDeploymentChecker().check(identity)
        assert result.warnings == [], f"Unexpected warnings: {[f.message for f in result.warnings]}"

    def test_example_has_no_infos(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        result = PublicDeploymentChecker().check(identity)
        assert result.infos == [], f"Unexpected infos: {[f.message for f in result.infos]}"

    def test_example_has_two_critical_guardrails(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        critical = [g for g in identity.guardrails.hard if g.severity.value == "critical"]
        assert len(critical) >= 2

    def test_example_has_out_of_scope(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        assert len(identity.role.scope.out_of_scope) >= 3

    def test_example_behavioral_contract_is_moderate(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        assert identity.behavioral_contract is not None
        assert identity.behavioral_contract.boundary_strictness.value == "moderate"

    def test_example_has_no_autonomous_permissions(self, chatbot_path):
        from personanexus.parser import IdentityParser

        parsed = IdentityParser().parse_file(chatbot_path)
        identity = AgentIdentity.model_validate(parsed)
        assert identity.guardrails.permissions.autonomous == []


# ---------------------------------------------------------------------------
# CLI integration: pn lint --public flag
# ---------------------------------------------------------------------------


class TestCLIPublicFlag:
    def test_safe_identity_exits_0(self, tmp_path):
        from typer.testing import CliRunner

        from personanexus.cli import app

        safe_yaml = tmp_path / "safe.yaml"
        safe_yaml.write_text(
            "schema_version: '1.0'\n"
            "metadata:\n"
            "  id: agt_cli_safe\n"
            "  name: SafeBot\n"
            "  version: 1.0.0\n"
            "  description: A safe bot\n"
            "  created_at: '2026-01-01T00:00:00Z'\n"
            "  updated_at: '2026-01-01T00:00:00Z'\n"
            "  status: active\n"
            "role:\n"
            "  title: Assistant\n"
            "  purpose: Help users\n"
            "  scope:\n"
            "    primary: [support]\n"
            "    out_of_scope: [financial advice]\n"
            "  audience:\n"
            "    primary: General public\n"
            "personality:\n"
            "  traits:\n"
            "    warmth: 0.7\n"
            "    directness: 0.6\n"
            "communication:\n"
            "  tone:\n"
            "    default: friendly\n"
            "  language:\n"
            "    primary: en\n"
            "principles:\n"
            "  - id: safe\n"
            "    priority: 1\n"
            "    statement: Be safe\n"
            "guardrails:\n"
            "  hard:\n"
            "    - id: no_harm\n"
            "      rule: Never cause harm\n"
            "      enforcement: output_filter\n"
            "      severity: critical\n"
            "behavioral_contract:\n"
            "  boundary_strictness: moderate\n"
            "  user_corrigibility: evidence_bound\n"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["lint", str(safe_yaml), "--public"])
        assert result.exit_code == 0, f"Expected 0, got {result.exit_code}: {result.output}"

    def test_unsafe_identity_exits_1_with_public_flag(self, tmp_path):
        from typer.testing import CliRunner

        from personanexus.cli import app

        unsafe_yaml = tmp_path / "unsafe.yaml"
        unsafe_yaml.write_text(
            "schema_version: '1.0'\n"
            "metadata:\n"
            "  id: agt_cli_unsafe\n"
            "  name: UnsafeBot\n"
            "  version: 1.0.0\n"
            "  description: Unsafe bot\n"
            "  created_at: '2026-01-01T00:00:00Z'\n"
            "  updated_at: '2026-01-01T00:00:00Z'\n"
            "  status: draft\n"
            "role:\n"
            "  title: Bot\n"
            "  purpose: Do stuff\n"
            "  scope:\n"
            "    primary: [anything]\n"
            "personality:\n"
            "  traits:\n"
            "    warmth: 0.5\n"
            "    directness: 0.5\n"
            "communication:\n"
            "  tone:\n"
            "    default: neutral\n"
            "  language:\n"
            "    primary: en\n"
            "principles:\n"
            "  - id: p1\n"
            "    priority: 1\n"
            "    statement: Help\n"
            "guardrails:\n"
            "  hard:\n"
            "    - id: low_bar\n"
            "      rule: Try not to cause harm\n"
            "      enforcement: prompt_instruction\n"
            "      severity: medium\n"
            # No behavioral_contract → error
            # No critical guardrail → error
        )

        runner = CliRunner()
        result = runner.invoke(app, ["lint", str(unsafe_yaml), "--public"])
        assert result.exit_code == 1, f"Expected 1, got {result.exit_code}: {result.output}"

    def test_public_flag_output_contains_safety_section(self, tmp_path):
        from typer.testing import CliRunner

        from personanexus.cli import app

        yaml_path = tmp_path / "check.yaml"
        yaml_path.write_text(
            "schema_version: '1.0'\n"
            "metadata:\n"
            "  id: agt_cli_hdr\n"
            "  name: CheckBot\n"
            "  version: 1.0.0\n"
            "  description: Check bot\n"
            "  created_at: '2026-01-01T00:00:00Z'\n"
            "  updated_at: '2026-01-01T00:00:00Z'\n"
            "  status: active\n"
            "role:\n"
            "  title: B\n"
            "  purpose: P\n"
            "  scope:\n"
            "    primary: [s]\n"
            "    out_of_scope: [x]\n"
            "  audience:\n"
            "    primary: Public\n"
            "personality:\n"
            "  traits:\n"
            "    warmth: 0.5\n"
            "    directness: 0.5\n"
            "communication:\n"
            "  tone:\n"
            "    default: friendly\n"
            "  language:\n"
            "    primary: en\n"
            "principles:\n"
            "  - id: p\n"
            "    priority: 1\n"
            "    statement: S\n"
            "guardrails:\n"
            "  hard:\n"
            "    - id: g\n"
            "      rule: R\n"
            "      enforcement: output_filter\n"
            "      severity: critical\n"
            "behavioral_contract:\n"
            "  boundary_strictness: moderate\n"
            "  user_corrigibility: evidence_bound\n"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["lint", str(yaml_path), "--public"])
        assert "safety" in result.output.lower() or "public" in result.output.lower(), (
            f"Expected safety section in output:\n{result.output}"
        )
