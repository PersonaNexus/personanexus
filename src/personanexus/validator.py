"""Validation for PersonaNexus specs — schema + semantic warnings."""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from personanexus.parser import IdentityParser, ParseError
from personanexus.types import AgentIdentity, PersonalityMode, TRAIT_ORDER

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ValidationWarning:
    type: str  # trait_tension | archetype_default | contradiction | unused_field
    message: str
    severity: str = "medium"  # low | medium | high
    path: str | None = None


@dataclasses.dataclass
class ValidationResult:
    valid: bool
    identity: AgentIdentity | None = None
    errors: list[str] = dataclasses.field(default_factory=list)
    warnings: list[ValidationWarning] = dataclasses.field(default_factory=list)


# Pairs of traits that can be in tension
_TRAIT_TENSION_PAIRS: list[tuple[str, str, float]] = [
    ("warmth", "directness", 0.7),
    ("rigor", "creativity", 0.7),
    ("verbosity", "patience", 0.6),
    ("humor", "rigor", 0.7),
    ("empathy", "directness", 0.7),
]


class IdentityValidator:
    """Validates PersonaNexus specs with schema validation and semantic checks."""

    def __init__(self) -> None:
        self._parser = IdentityParser()

    def validate_file(self, path: str | Path) -> ValidationResult:
        """Validate a YAML file end-to-end."""
        try:
            data = self._parser.parse_file(path)
        except ParseError as exc:
            return ValidationResult(valid=False, errors=[str(exc)])

        return self.validate_dict(data)

    def validate_dict(self, data: dict[str, Any]) -> ValidationResult:
        """Validate a parsed dictionary against the schema."""
        errors: list[str] = []
        identity: AgentIdentity | None = None

        try:
            identity = AgentIdentity.model_validate(data)
        except ValidationError as exc:
            for err in exc.errors():
                loc = " -> ".join(str(part) for part in err["loc"])
                errors.append(f"{loc}: {err['msg']}")

        if errors:
            return ValidationResult(valid=False, errors=errors)

        # identity is guaranteed non-None: no ValidationError was raised above
        warnings = self._check_warnings(identity)  # type: ignore[arg-type]

        return ValidationResult(valid=True, identity=identity, warnings=warnings)

    def validate_identity(self, identity: AgentIdentity) -> ValidationResult:
        """Run semantic checks on an already-constructed identity."""
        warnings = self._check_warnings(identity)
        return ValidationResult(valid=True, identity=identity, warnings=warnings)

    # ------------------------------------------------------------------
    # Semantic warning checks
    # ------------------------------------------------------------------

    def _check_warnings(self, identity: AgentIdentity) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []
        warnings.extend(self._check_trait_tensions(identity))
        warnings.extend(self._check_personality_profile(identity))
        warnings.extend(self._check_principle_ordering(identity))
        warnings.extend(self._check_scope_overlap(identity))
        warnings.extend(self._check_dynamics(identity))
        return warnings

    def _check_trait_tensions(self, identity: AgentIdentity) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []
        traits = identity.personality.traits.defined_traits()

        for trait_a, trait_b, threshold in _TRAIT_TENSION_PAIRS:
            if trait_a in traits and trait_b in traits:
                diff = abs(traits[trait_a] - traits[trait_b])
                if diff > threshold:
                    warnings.append(
                        ValidationWarning(
                            type="trait_tension",
                            message=(
                                f"personality.traits.{trait_a} ({traits[trait_a]}) and "
                                f"{trait_b} ({traits[trait_b]}) differ by {diff:.2f} "
                                f"— potential tension"
                            ),
                            severity="medium",
                            path="personality.traits",
                        )
                    )

        return warnings

    def _check_principle_ordering(self, identity: AgentIdentity) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []
        priorities = [p.priority for p in identity.principles]
        if priorities != sorted(priorities):
            warnings.append(
                ValidationWarning(
                    type="ordering",
                    message="Principles are not listed in priority order",
                    severity="low",
                    path="principles",
                )
            )
        return warnings

    def _check_scope_overlap(self, identity: AgentIdentity) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []
        primary = set(identity.role.scope.primary)
        secondary = set(identity.role.scope.secondary)
        out_of_scope = set(identity.role.scope.out_of_scope)

        overlap = primary & secondary
        if overlap:
            warnings.append(
                ValidationWarning(
                    type="scope_overlap",
                    message=f"Scope items appear in both primary and secondary: {overlap}",
                    severity="low",
                    path="role.scope",
                )
            )

        primary_out = primary & out_of_scope
        if primary_out:
            warnings.append(
                ValidationWarning(
                    type="scope_overlap",
                    message=f"Scope items appear in both primary and out_of_scope: {primary_out}",
                    severity="high",
                    path="role.scope",
                )
            )

        secondary_out = secondary & out_of_scope
        if secondary_out:
            warnings.append(
                ValidationWarning(
                    type="scope_overlap",
                    message=(
                        f"Scope items appear in both secondary and out_of_scope: {secondary_out}"
                    ),
                    severity="high",
                    path="role.scope",
                )
            )

        return warnings

    def _check_personality_profile(self, identity: AgentIdentity) -> list[ValidationWarning]:
        """Check personality profile for enterprise recommendations."""
        warnings: list[ValidationWarning] = []
        profile = identity.personality.profile

        # Enterprise recommendation: neuroticism > 0.6 may cause inconsistent behavior
        if (
            profile.mode in (PersonalityMode.OCEAN, PersonalityMode.HYBRID)
            and profile.ocean is not None
            and profile.ocean.neuroticism > 0.6
        ):
            warnings.append(
                ValidationWarning(
                    type="personality_profile",
                    message=(
                        f"OCEAN neuroticism ({profile.ocean.neuroticism}) is above 0.6 "
                        "— enterprise agents typically perform better with lower neuroticism"
                    ),
                    severity="medium",
                    path="personality.profile.ocean.neuroticism",
                )
            )

        # Enterprise recommendation for customer-facing agents
        if (
            profile.mode in (PersonalityMode.OCEAN, PersonalityMode.HYBRID)
            and profile.ocean is not None
        ):
            combined = profile.ocean.conscientiousness + profile.ocean.agreeableness
            if combined < 0.8:
                warnings.append(
                    ValidationWarning(
                        type="personality_profile",
                        message=(
                            f"OCEAN conscientiousness + agreeableness = {combined:.2f} "
                            "(below 0.8) — customer-facing agents benefit from higher values"
                        ),
                        severity="low",
                        path="personality.profile.ocean",
                    )
                )

        # DISC preset validation (soft check — preset may not exist)
        if profile.disc_preset is not None:
            from personanexus.personality import DISC_PRESETS

            if profile.disc_preset.lower() not in DISC_PRESETS:
                available = ", ".join(sorted(DISC_PRESETS.keys()))
                warnings.append(
                    ValidationWarning(
                        type="personality_profile",
                        message=(
                            f"Unknown DISC preset '{profile.disc_preset}'. Available: {available}"
                        ),
                        severity="high",
                        path="personality.profile.disc_preset",
                    )
                )

        # Jungian preset validation (soft check — preset may not exist)
        if profile.jungian_preset is not None:
            from personanexus.personality import JUNGIAN_PRESETS

            if profile.jungian_preset.lower() not in JUNGIAN_PRESETS:
                available = ", ".join(sorted(JUNGIAN_PRESETS.keys()))
                warnings.append(
                    ValidationWarning(
                        type="personality_profile",
                        message=(
                            f"Unknown Jungian preset '{profile.jungian_preset}'. "
                            f"Available: {available}"
                        ),
                        severity="high",
                        path="personality.profile.jungian_preset",
                    )
                )

        return warnings

    def _check_dynamics(self, identity: AgentIdentity) -> list[ValidationWarning]:
        """Check dynamics config for potential issues."""
        warnings: list[ValidationWarning] = []
        dynamics = identity.dynamics
        if dynamics is None:
            return warnings

        known_traits = set(TRAIT_ORDER)

        # Check mood trait_deltas reference known traits
        for mood in dynamics.moods:
            for trait_name in mood.trait_deltas:
                if trait_name not in known_traits:
                    warnings.append(
                        ValidationWarning(
                            type="dynamics_unknown_trait",
                            message=(
                                f"Mood '{mood.name}' references unknown trait "
                                f"'{trait_name}' in trait_deltas"
                            ),
                            severity="medium",
                            path=f"dynamics.moods.{mood.name}.trait_deltas",
                        )
                    )

        # Check mode trait_overrides reference known traits
        for mode in dynamics.modes:
            for trait_name in mode.trait_overrides:
                if trait_name not in known_traits:
                    warnings.append(
                        ValidationWarning(
                            type="dynamics_unknown_trait",
                            message=(
                                f"Mode '{mode.name}' references unknown trait "
                                f"'{trait_name}' in trait_overrides"
                            ),
                            severity="medium",
                            path=f"dynamics.modes.{mode.name}.trait_overrides",
                        )
                    )

        # Check memory influence unlock_mode targets reference defined modes
        mode_names = {m.name for m in dynamics.modes}
        for rule in dynamics.memory_influences:
            parts = rule.effect.strip().split()
            if len(parts) >= 2 and parts[0] == "unlock_mode":
                target = parts[1]
                if target not in mode_names:
                    warnings.append(
                        ValidationWarning(
                            type="dynamics_invalid_unlock",
                            message=(
                                f"Memory influence effect 'unlock_mode {target}' "
                                f"references undefined mode (defined: "
                                f"{', '.join(sorted(mode_names)) or 'none'})"
                            ),
                            severity="high",
                            path="dynamics.memory_influences",
                        )
                    )

        # Check for moods/modes without triggers (they can never activate)
        for mood in dynamics.moods:
            if mood.name != dynamics.default_mood and not mood.triggers:
                warnings.append(
                    ValidationWarning(
                        type="dynamics_unreachable",
                        message=(
                            f"Mood '{mood.name}' has no triggers and is not "
                            f"the default — it can never be activated"
                        ),
                        severity="low",
                        path=f"dynamics.moods.{mood.name}",
                    )
                )
        for mode in dynamics.modes:
            if mode.name != dynamics.default_mode and not mode.triggers:
                warnings.append(
                    ValidationWarning(
                        type="dynamics_unreachable",
                        message=(
                            f"Mode '{mode.name}' has no triggers and is not "
                            f"the default — it can never be activated"
                        ),
                        severity="low",
                        path=f"dynamics.modes.{mode.name}",
                    )
                )

        return warnings
