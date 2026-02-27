"""Identity linter -- deep semantic checks beyond schema validation.

Catches logical inconsistencies, unused fields, conflicting settings,
and missing recommended configuration that the Pydantic schema cannot express.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Literal

from personanexus.parser import IdentityParser
from personanexus.types import AgentIdentity


@dataclasses.dataclass
class LintWarning:
    """A single lint finding."""

    rule: str
    message: str
    severity: Literal["info", "warning", "error"]
    path: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-zA-Z]{3,}")


def _word_set(text: str) -> set[str]:
    """Extract lowercased words (>= 3 chars) from *text*."""
    return {w.lower() for w in _WORD_RE.findall(text)}


def _word_overlap_ratio(a: str, b: str) -> float:
    """Return the Jaccard-style overlap ratio between two strings' word sets."""
    words_a = _word_set(a)
    words_b = _word_set(b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller if smaller else 0.0


# ---------------------------------------------------------------------------
# Conflict detection tables
# ---------------------------------------------------------------------------

# (trait_name, threshold_direction, threshold, conflicting_tone, explanation)
_TONE_TRAIT_CONFLICTS: list[tuple[str, str, float, str, str]] = [
    (
        "directness",
        "high",
        0.8,
        "diplomatic",
        "High directness (>{threshold}) conflicts with a 'diplomatic' tone",
    ),
    (
        "humor",
        "high",
        0.8,
        "formal",
        "High humor (>{threshold}) conflicts with a 'formal' tone",
    ),
    (
        "warmth",
        "low",
        0.2,
        "friendly",
        "Low warmth (<{threshold}) conflicts with a 'friendly' tone",
    ),
    (
        "humor",
        "high",
        0.8,
        "serious",
        "High humor (>{threshold}) conflicts with a 'serious' tone",
    ),
]


# ---------------------------------------------------------------------------
# Core linter
# ---------------------------------------------------------------------------


class IdentityLinter:
    """Run semantic lint checks on a parsed :class:`AgentIdentity`."""

    def __init__(self) -> None:
        self._parser = IdentityParser()

    # -- public API --------------------------------------------------------

    def lint_file(self, path: str) -> list[LintWarning]:
        """Parse a YAML file and lint the resulting identity."""
        data = self._parser.parse_file(path)
        identity = AgentIdentity.model_validate(data)
        return self.lint(identity)

    def lint(self, identity: AgentIdentity) -> list[LintWarning]:
        """Run all lint rules on an already-constructed identity."""
        warnings: list[LintWarning] = []
        warnings.extend(self._check_unused_expertise(identity))
        warnings.extend(self._check_conflicting_tone(identity))
        warnings.extend(self._check_guardrail_principle_overlap(identity))
        warnings.extend(self._check_empty_sections(identity))
        warnings.extend(self._check_trait_extremes(identity))
        warnings.extend(self._check_inconsistent_naming(identity))
        warnings.extend(self._check_missing_recommended(identity))
        return warnings

    # -- rule implementations ----------------------------------------------

    def _check_unused_expertise(self, identity: AgentIdentity) -> list[LintWarning]:
        """Rule ``unused-expertise``: domains listed but never referenced in
        scope or principles."""
        warnings: list[LintWarning] = []
        domains = identity.expertise.domains
        if not domains:
            return warnings

        # Build a combined text corpus from scope items and principle statements.
        scope_text = " ".join(
            identity.role.scope.primary
            + identity.role.scope.secondary
            + identity.role.scope.out_of_scope
        ).lower()
        principle_text = " ".join(p.statement for p in identity.principles).lower()
        combined = scope_text + " " + principle_text

        for idx, domain in enumerate(domains):
            # Check if any significant word from the domain name appears in
            # the combined corpus.
            domain_words = _word_set(domain.name)
            if domain_words and not any(w in combined for w in domain_words):
                warnings.append(
                    LintWarning(
                        rule="unused-expertise",
                        message=(
                            f"Expertise domain '{domain.name}' is not referenced "
                            "in scope or principles"
                        ),
                        severity="info",
                        path=f"expertise.domains[{idx}].name",
                    )
                )
        return warnings

    def _check_conflicting_tone(self, identity: AgentIdentity) -> list[LintWarning]:
        """Rule ``conflicting-tone``: personality traits that clash with the
        declared tone."""
        warnings: list[LintWarning] = []
        traits = identity.personality.traits.defined_traits()
        tone_default = identity.communication.tone.default.lower()

        for trait_name, direction, threshold, tone_kw, explanation in _TONE_TRAIT_CONFLICTS:
            if trait_name not in traits:
                continue
            value = traits[trait_name]
            tone_match = tone_kw in tone_default
            if not tone_match:
                continue
            conflict = (
                (direction == "high" and value > threshold)
                or (direction == "low" and value < threshold)
            )
            if conflict:
                warnings.append(
                    LintWarning(
                        rule="conflicting-tone",
                        message=explanation.format(threshold=threshold),
                        severity="warning",
                        path="personality.traits." + trait_name,
                    )
                )
        return warnings

    def _check_guardrail_principle_overlap(
        self, identity: AgentIdentity
    ) -> list[LintWarning]:
        """Rule ``guardrail-principle-overlap``: guardrail rules that largely
        duplicate a principle statement (word overlap > 60 %)."""
        warnings: list[LintWarning] = []
        all_rules: list[tuple[str, str, str]] = []  # (id, rule_text, path)

        for idx, g in enumerate(identity.guardrails.hard):
            all_rules.append((g.id, g.rule, f"guardrails.hard[{idx}]"))
        for idx, g in enumerate(identity.guardrails.soft):
            all_rules.append((g.id, g.rule, f"guardrails.soft[{idx}]"))

        for rule_id, rule_text, rule_path in all_rules:
            for _pidx, principle in enumerate(identity.principles):
                ratio = _word_overlap_ratio(rule_text, principle.statement)
                if ratio > 0.6:
                    warnings.append(
                        LintWarning(
                            rule="guardrail-principle-overlap",
                            message=(
                                f"Guardrail '{rule_id}' overlaps with principle "
                                f"'{principle.id}' ({ratio:.0%} word overlap)"
                            ),
                            severity="info",
                            path=rule_path,
                        )
                    )
        return warnings

    def _check_empty_sections(self, identity: AgentIdentity) -> list[LintWarning]:
        """Rule ``empty-section``: sections that are technically valid but
        effectively empty."""
        warnings: list[LintWarning] = []

        # Expertise with no domains
        if not identity.expertise.domains:
            warnings.append(
                LintWarning(
                    rule="empty-section",
                    message="Expertise section has no domains defined",
                    severity="info",
                    path="expertise.domains",
                )
            )

        # Guardrails with empty soft list (hard is required to be non-empty by schema)
        if not identity.guardrails.soft:
            warnings.append(
                LintWarning(
                    rule="empty-section",
                    message="No soft guardrails defined",
                    severity="info",
                    path="guardrails.soft",
                )
            )

        # Empty vocabulary lists when vocabulary section exists
        if identity.communication.vocabulary is not None:
            vocab = identity.communication.vocabulary
            if not vocab.preferred and not vocab.avoided and not vocab.signature_phrases:
                warnings.append(
                    LintWarning(
                        rule="empty-section",
                        message=(
                            "Vocabulary section exists but all lists "
                            "(preferred, avoided, signature_phrases) are empty"
                        ),
                        severity="info",
                        path="communication.vocabulary",
                    )
                )

        return warnings

    def _check_trait_extremes(self, identity: AgentIdentity) -> list[LintWarning]:
        """Rule ``trait-extreme``: traits at exactly 0.0 or 1.0 may produce
        unnatural behaviour."""
        warnings: list[LintWarning] = []
        traits = identity.personality.traits.defined_traits()

        for name, value in traits.items():
            if value == 0.0 or value == 1.0:
                warnings.append(
                    LintWarning(
                        rule="trait-extreme",
                        message=(
                            f"Trait '{name}' is at {value} -- extreme values "
                            "may cause unnatural behavior"
                        ),
                        severity="warning",
                        path=f"personality.traits.{name}",
                    )
                )
        return warnings

    def _check_inconsistent_naming(self, identity: AgentIdentity) -> list[LintWarning]:
        """Rule ``inconsistent-naming``: metadata.name should appear (case-
        insensitively) somewhere in metadata.id."""
        warnings: list[LintWarning] = []
        agent_id = identity.metadata.id.lower()
        name = identity.metadata.name.lower()

        # The id format is ``agt_<something>``.  Strip prefix.
        id_body = agent_id.replace("agt_", "", 1).replace("_", " ")

        # Check if any significant word from the name appears in the id body.
        name_words = _word_set(name)
        id_words = _word_set(id_body)

        if name_words and id_words and not (name_words & id_words):
            warnings.append(
                LintWarning(
                    rule="inconsistent-naming",
                    message=(
                        f"metadata.name '{identity.metadata.name}' does not match "
                        f"metadata.id '{identity.metadata.id}' pattern"
                    ),
                    severity="warning",
                    path="metadata",
                )
            )
        return warnings

    def _check_missing_recommended(self, identity: AgentIdentity) -> list[LintWarning]:
        """Rule ``missing-recommended``: fields that are optional but strongly
        recommended."""
        warnings: list[LintWarning] = []

        # out_of_scope is empty
        if not identity.role.scope.out_of_scope:
            warnings.append(
                LintWarning(
                    rule="missing-recommended",
                    message="role.scope.out_of_scope is empty -- consider defining boundaries",
                    severity="info",
                    path="role.scope.out_of_scope",
                )
            )

        # No audience defined
        if identity.role.audience is None:
            warnings.append(
                LintWarning(
                    rule="missing-recommended",
                    message="role.audience is not defined -- consider specifying a target audience",
                    severity="info",
                    path="role.audience",
                )
            )

        return warnings
