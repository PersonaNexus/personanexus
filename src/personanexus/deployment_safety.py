"""Public-boundary safety validation for PersonaNexus deployment artifacts.

Initiative: PersonaNexus public deployment contract and Studio export path
            (initiative id: 0a10bb0b, packet id: f6573b4f)

When an agent identity is going to be deployed publicly (serving untrusted
users) it must meet a higher safety bar than what schema validation and the
general linter enforce.  This module provides a dedicated
:class:`PublicDeploymentChecker` that runs seven focused rules and returns
a :class:`DeploymentSafetyResult` with categorised findings.

The checker is intentionally strict about **errors** (blockers that MUST be
fixed before safe public deployment) while remaining informative about
**warnings** (risks that should be reviewed) and **info** (best-practice
suggestions).

Rules
-----
``public-critical-guardrail-required``
    At least one hard guardrail with ``severity: critical`` is required.
    Without a critical-severity guardrail the identity has no hard stop
    for the most dangerous outputs. (error)

``public-behavioral-contract-required``
    A ``behavioral_contract`` section is required.  Without it the
    agent's honesty mode, refusal posture, and boundary strictness default
    to library values that may not match the deployment context. (error)

``public-flexible-boundary-risk``
    ``behavioral_contract.boundary_strictness: flexible`` is acceptable
    for trusted-operator contexts but is risky for public audiences.
    Should be ``moderate`` or ``strict``. (warning)

``public-open-corrigibility-risk``
    ``behavioral_contract.user_corrigibility: open`` lets any user
    override the agent's reasoning.  Public deployments should use
    ``evidence_bound`` or ``limited``. (warning)

``public-autonomous-needs-contract``
    Any entry in ``guardrails.permissions.autonomous`` represents an
    action the agent will take without asking.  This is only safe in a
    public context when a behavioral_contract is also present. (error,
    only triggered when autonomous is non-empty AND contract is absent)

``public-out-of-scope-required``
    An explicit ``role.scope.out_of_scope`` list anchors what the agent
    will refuse to discuss.  Public deployments without it have undefined
    boundaries. (warning)

``public-audience-undefined``
    ``role.audience`` is not defined.  Public deployments should declare
    their intended audience so runtime systems can apply appropriate
    guardrails. (info)

CLI integration
---------------
Run the checker from the command line via the ``pn lint --public`` flag
(wired in by the CLI module) or call it programmatically::

    from personanexus.deployment_safety import PublicDeploymentChecker
    checker = PublicDeploymentChecker()
    result = checker.check(identity)
    if not result.safe_to_deploy:
        for finding in result.errors:
            print(f"[ERROR] {finding.message}")

Studio integration
------------------
The Studio export panel calls :func:`check_for_studio` which returns a
lightweight summary suitable for surfacing as a Streamlit warning banner.
"""

from __future__ import annotations

import dataclasses
from typing import Literal

from personanexus.types import (
    AgentIdentity,
    BehavioralContract,
    BoundaryStrictness,
    UserCorrigibility,
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class DeploymentFinding:
    """A single public-deployment safety finding."""

    rule: str
    message: str
    severity: Literal["error", "warning", "info"]
    path: str | None = None


@dataclasses.dataclass
class DeploymentSafetyResult:
    """Aggregated result from :class:`PublicDeploymentChecker`.

    ``safe_to_deploy`` is ``True`` only when there are zero error-level
    findings.  Warnings and info findings should be reviewed but do not
    block deployment.
    """

    findings: list[DeploymentFinding] = dataclasses.field(default_factory=list)

    @property
    def errors(self) -> list[DeploymentFinding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[DeploymentFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def infos(self) -> list[DeploymentFinding]:
        return [f for f in self.findings if f.severity == "info"]

    @property
    def safe_to_deploy(self) -> bool:
        """True when no error-level findings exist."""
        return not self.errors

    def summary(self) -> str:
        """One-line human-readable summary."""
        if self.safe_to_deploy:
            extra = (
                f" ({len(self.warnings)} warning(s), {len(self.infos)} info(s))"
                if self.warnings or self.infos
                else ""
            )
            return f"Safe to deploy{extra}"
        return (
            f"NOT safe to deploy — {len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s), {len(self.infos)} info(s)"
        )


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------


class PublicDeploymentChecker:
    """Run public-boundary safety checks on a :class:`PersonaNexus.AgentIdentity`.

    All rules are run on every call; the caller decides which severities
    to surface.  Rule names are stable — safe to reference in CI scripts
    or suppression lists.
    """

    def check(self, identity: AgentIdentity) -> DeploymentSafetyResult:
        """Run all public-deployment safety rules and return a result."""
        findings: list[DeploymentFinding] = []
        findings.extend(self._check_critical_guardrail(identity))
        findings.extend(self._check_behavioral_contract_required(identity))
        findings.extend(self._check_flexible_boundary(identity))
        findings.extend(self._check_open_corrigibility(identity))
        findings.extend(self._check_autonomous_needs_contract(identity))
        findings.extend(self._check_out_of_scope_required(identity))
        findings.extend(self._check_audience_defined(identity))
        return DeploymentSafetyResult(findings=findings)

    # -- Rule implementations ---------------------------------------------

    def _check_critical_guardrail(self, identity: AgentIdentity) -> list[DeploymentFinding]:
        """Rule: public-critical-guardrail-required.

        At least one hard guardrail with severity=CRITICAL must be present.
        """
        has_critical = any(g.severity.value == "critical" for g in identity.guardrails.hard)
        if has_critical:
            return []
        return [
            DeploymentFinding(
                rule="public-critical-guardrail-required",
                message=(
                    "Public deployments require at least one hard guardrail with "
                    "severity: critical.  Add a critical guardrail that defines "
                    "the absolute boundary for harmful output."
                ),
                severity="error",
                path="guardrails.hard",
            )
        ]

    def _check_behavioral_contract_required(
        self, identity: AgentIdentity
    ) -> list[DeploymentFinding]:
        """Rule: public-behavioral-contract-required.

        A behavioral_contract section must be present for public deployments.
        """
        if identity.behavioral_contract is not None:
            return []
        return [
            DeploymentFinding(
                rule="public-behavioral-contract-required",
                message=(
                    "Public deployments require a behavioral_contract section that "
                    "explicitly declares honesty_mode, refusal_posture, and "
                    "boundary_strictness.  Without it the agent uses library defaults "
                    "that may not match the deployment context."
                ),
                severity="error",
                path="behavioral_contract",
            )
        ]

    def _check_flexible_boundary(self, identity: AgentIdentity) -> list[DeploymentFinding]:
        """Rule: public-flexible-boundary-risk.

        FLEXIBLE boundary strictness is risky for public-facing agents.
        """
        contract: BehavioralContract | None = identity.behavioral_contract
        if contract is None:
            return []  # covered by public-behavioral-contract-required
        if contract.boundary_strictness != BoundaryStrictness.FLEXIBLE:
            return []
        return [
            DeploymentFinding(
                rule="public-flexible-boundary-risk",
                message=(
                    "behavioral_contract.boundary_strictness is 'flexible'.  "
                    "This is appropriate for trusted-operator contexts but is risky "
                    "for public audiences.  Consider 'moderate' or 'strict'."
                ),
                severity="warning",
                path="behavioral_contract.boundary_strictness",
            )
        ]

    def _check_open_corrigibility(self, identity: AgentIdentity) -> list[DeploymentFinding]:
        """Rule: public-open-corrigibility-risk.

        OPEN corrigibility lets any user override the agent's reasoning,
        which is unsafe for public deployments.
        """
        contract: BehavioralContract | None = identity.behavioral_contract
        if contract is None:
            return []  # covered by public-behavioral-contract-required
        if contract.user_corrigibility != UserCorrigibility.OPEN:
            return []
        return [
            DeploymentFinding(
                rule="public-open-corrigibility-risk",
                message=(
                    "behavioral_contract.user_corrigibility is 'open'.  "
                    "This allows any user to override the agent's reasoning. "
                    "Public deployments should use 'evidence_bound' or 'limited'."
                ),
                severity="warning",
                path="behavioral_contract.user_corrigibility",
            )
        ]

    def _check_autonomous_needs_contract(self, identity: AgentIdentity) -> list[DeploymentFinding]:
        """Rule: public-autonomous-needs-contract.

        Any autonomous permission requires a behavioral_contract in public
        contexts so that autonomy boundaries are explicitly declared.
        """
        has_autonomous = bool(identity.guardrails.permissions.autonomous)
        has_contract = identity.behavioral_contract is not None
        if not has_autonomous or has_contract:
            return []
        autonomous_items = ", ".join(
            f"'{a}'" for a in identity.guardrails.permissions.autonomous[:5]
        )
        more = (
            f" (and {len(identity.guardrails.permissions.autonomous) - 5} more)"
            if len(identity.guardrails.permissions.autonomous) > 5
            else ""
        )
        return [
            DeploymentFinding(
                rule="public-autonomous-needs-contract",
                message=(
                    f"Identity has autonomous permissions ({autonomous_items}{more}) "
                    "but no behavioral_contract.  Autonomous actions in public contexts "
                    "must be paired with an explicit behavioral contract."
                ),
                severity="error",
                path="guardrails.permissions.autonomous",
            )
        ]

    def _check_out_of_scope_required(self, identity: AgentIdentity) -> list[DeploymentFinding]:
        """Rule: public-out-of-scope-required.

        An explicit out_of_scope list anchors what the agent will refuse.
        """
        if identity.role.scope.out_of_scope:
            return []
        return [
            DeploymentFinding(
                rule="public-out-of-scope-required",
                message=(
                    "role.scope.out_of_scope is empty.  "
                    "Public deployments should explicitly list topics or actions "
                    "the agent will refuse so users understand its boundaries."
                ),
                severity="warning",
                path="role.scope.out_of_scope",
            )
        ]

    def _check_audience_defined(self, identity: AgentIdentity) -> list[DeploymentFinding]:
        """Rule: public-audience-undefined.

        role.audience should be defined for public deployments.
        """
        if identity.role.audience is not None:
            return []
        return [
            DeploymentFinding(
                rule="public-audience-undefined",
                message=(
                    "role.audience is not defined.  "
                    "Public deployments should declare the intended audience so "
                    "runtime systems can apply appropriate guardrails and context."
                ),
                severity="info",
                path="role.audience",
            )
        ]


# ---------------------------------------------------------------------------
# Studio helper
# ---------------------------------------------------------------------------


def check_for_studio(identity: AgentIdentity) -> dict:
    """Run public-deployment safety checks and return a Studio-friendly summary.

    Returns a dict with keys:
    - ``safe``: bool
    - ``summary``: str (one-line)
    - ``errors``: list[str]
    - ``warnings``: list[str]
    - ``infos``: list[str]

    Suitable for rendering as a Streamlit warning/info banner.
    """
    checker = PublicDeploymentChecker()
    result = checker.check(identity)
    return {
        "safe": result.safe_to_deploy,
        "summary": result.summary(),
        "errors": [f.message for f in result.errors],
        "warnings": [f.message for f in result.warnings],
        "infos": [f.message for f in result.infos],
    }
