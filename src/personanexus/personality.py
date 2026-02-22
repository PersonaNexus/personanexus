"""OCEAN/DISC personality framework mapping.

Provides forward mapping (OCEAN/DISC → custom traits), reverse mapping
(custom traits → OCEAN/DISC), DISC presets, and the main
``compute_personality_traits`` entry-point used by the compiler and CLI.

All formulas are pure Python weighted sums — no external dependencies.
Weights are sourced from the AgentGov Multi-Agent Spec (Deliverable 2).
"""

from __future__ import annotations

from personanexus.types import (
    DiscProfile,
    OceanProfile,
    OverridePriority,
    Personality,
    PersonalityMode,
    PersonalityTraits,
)

# ---------------------------------------------------------------------------
# Weight tables — OCEAN → custom traits
# ---------------------------------------------------------------------------
# Each key is a trait name; value is {ocean_dim: weight}.
# Complement dimensions use (1 - dim) and are stored as tuples.

OCEAN_WEIGHTS: dict[str, list[tuple[str, float, bool]]] = {
    # (ocean_dimension, weight, complement?)
    "warmth": [
        ("agreeableness", 0.5, False),
        ("extraversion", 0.3, False),
        ("neuroticism", 0.2, True),
    ],
    "verbosity": [
        ("extraversion", 0.4, False),
        ("openness", 0.3, False),
        ("conscientiousness", 0.15, True),
        ("agreeableness", 0.15, False),
    ],
    "assertiveness": [
        ("extraversion", 0.4, False),
        ("agreeableness", 0.3, True),
        ("conscientiousness", 0.2, False),
        ("neuroticism", 0.1, True),
    ],
    "humor": [
        ("extraversion", 0.35, False),
        ("openness", 0.35, False),
        ("neuroticism", 0.15, True),
        ("agreeableness", 0.15, False),
    ],
    "empathy": [
        ("agreeableness", 0.6, False),
        ("neuroticism", 0.2, True),
        ("openness", 0.1, False),
        ("extraversion", 0.1, False),
    ],
    "directness": [
        ("agreeableness", 0.4, True),
        ("extraversion", 0.3, False),
        ("conscientiousness", 0.2, False),
        ("neuroticism", 0.1, True),
    ],
    "rigor": [
        ("conscientiousness", 0.7, False),
        ("openness", 0.15, True),
        ("neuroticism", 0.15, True),
    ],
    "creativity": [
        ("openness", 0.6, False),
        ("extraversion", 0.2, False),
        ("conscientiousness", 0.2, True),
    ],
    "epistemic_humility": [
        ("agreeableness", 0.3, False),
        ("openness", 0.3, False),
        ("extraversion", 0.2, True),
        ("conscientiousness", 0.2, False),
    ],
    "patience": [
        ("agreeableness", 0.35, False),
        ("conscientiousness", 0.25, False),
        ("neuroticism", 0.25, True),
        ("extraversion", 0.15, True),
    ],
}

# ---------------------------------------------------------------------------
# Weight tables — DISC → custom traits
# ---------------------------------------------------------------------------

DISC_WEIGHTS: dict[str, list[tuple[str, float, bool]]] = {
    "warmth": [
        ("influence", 0.45, False),
        ("steadiness", 0.35, False),
        ("dominance", 0.2, True),
    ],
    "verbosity": [
        ("influence", 0.4, False),
        ("conscientiousness", 0.3, False),
        ("dominance", 0.15, True),
        ("steadiness", 0.15, False),
    ],
    "assertiveness": [
        ("dominance", 0.6, False),
        ("influence", 0.2, False),
        ("steadiness", 0.2, True),
    ],
    "humor": [
        ("influence", 0.6, False),
        ("dominance", 0.2, True),
        ("steadiness", 0.1, False),
        ("conscientiousness", 0.1, True),
    ],
    "empathy": [
        ("steadiness", 0.4, False),
        ("influence", 0.35, False),
        ("dominance", 0.25, True),
    ],
    "directness": [
        ("dominance", 0.55, False),
        ("conscientiousness", 0.2, False),
        ("steadiness", 0.15, True),
        ("influence", 0.1, True),
    ],
    "rigor": [
        ("conscientiousness", 0.65, False),
        ("steadiness", 0.2, False),
        ("influence", 0.15, True),
    ],
    "creativity": [
        ("influence", 0.4, False),
        ("dominance", 0.25, False),
        ("conscientiousness", 0.35, True),
    ],
    "epistemic_humility": [
        ("conscientiousness", 0.35, False),
        ("steadiness", 0.3, False),
        ("dominance", 0.35, True),
    ],
    "patience": [
        ("steadiness", 0.55, False),
        ("dominance", 0.25, True),
        ("conscientiousness", 0.2, False),
    ],
}

# ---------------------------------------------------------------------------
# Weight tables — reverse mapping (traits → OCEAN)
# ---------------------------------------------------------------------------

REVERSE_OCEAN_WEIGHTS: dict[str, list[tuple[str, float, bool]]] = {
    "openness": [
        ("creativity", 0.4, False),
        ("humor", 0.2, False),
        ("epistemic_humility", 0.2, False),
        ("rigor", 0.2, True),
    ],
    "conscientiousness": [
        ("rigor", 0.5, False),
        ("patience", 0.2, False),
        ("directness", 0.15, False),
        ("creativity", 0.15, True),
    ],
    "extraversion": [
        ("assertiveness", 0.3, False),
        ("warmth", 0.25, False),
        ("humor", 0.2, False),
        ("verbosity", 0.25, False),
    ],
    "agreeableness": [
        ("empathy", 0.35, False),
        ("warmth", 0.25, False),
        ("patience", 0.25, False),
        ("directness", 0.15, True),
    ],
    "neuroticism": [
        ("patience", 0.3, True),
        ("empathy", 0.2, True),
        ("warmth", 0.2, True),
        ("rigor", 0.15, True),
        ("humor", 0.15, True),
    ],
}

# ---------------------------------------------------------------------------
# Weight tables — reverse mapping (traits → DISC)
# ---------------------------------------------------------------------------
# Derived by mirroring the OCEAN reverse approach using DISC forward weights.

REVERSE_DISC_WEIGHTS: dict[str, list[tuple[str, float, bool]]] = {
    "dominance": [
        ("assertiveness", 0.35, False),
        ("directness", 0.30, False),
        ("patience", 0.20, True),
        ("empathy", 0.15, True),
    ],
    "influence": [
        ("humor", 0.30, False),
        ("warmth", 0.25, False),
        ("verbosity", 0.25, False),
        ("creativity", 0.20, False),
    ],
    "steadiness": [
        ("patience", 0.35, False),
        ("empathy", 0.25, False),
        ("epistemic_humility", 0.20, False),
        ("assertiveness", 0.20, True),
    ],
    "conscientiousness": [
        ("rigor", 0.45, False),
        ("patience", 0.20, False),
        ("directness", 0.15, False),
        ("creativity", 0.20, True),
    ],
}

# ---------------------------------------------------------------------------
# DISC presets
# ---------------------------------------------------------------------------

DISC_PRESETS: dict[str, DiscProfile] = {
    "the_commander": DiscProfile(
        dominance=0.9, influence=0.4, steadiness=0.2, conscientiousness=0.5
    ),
    "the_influencer": DiscProfile(
        dominance=0.4, influence=0.9, steadiness=0.4, conscientiousness=0.3
    ),
    "the_steady_hand": DiscProfile(
        dominance=0.2, influence=0.5, steadiness=0.9, conscientiousness=0.5
    ),
    "the_analyst": DiscProfile(dominance=0.3, influence=0.2, steadiness=0.6, conscientiousness=0.9),
}


# ---------------------------------------------------------------------------
# Forward mapping functions
# ---------------------------------------------------------------------------


def _apply_weights(
    weights: dict[str, list[tuple[str, float, bool]]],
    values: dict[str, float],
) -> dict[str, float]:
    """Apply weighted-sum formulas to compute trait values.

    Parameters
    ----------
    weights:
        Mapping of trait_name -> list of (dimension, weight, complement).
    values:
        Mapping of dimension_name -> float score (0-1).

    Returns
    -------
    dict of trait_name -> computed float value, clamped to [0, 1].
    """
    result: dict[str, float] = {}
    for trait, components in weights.items():
        total = 0.0
        for dim, weight, complement in components:
            raw = values[dim]
            val = (1.0 - raw) if complement else raw
            total += val * weight
        # Clamp to [0, 1] for safety (should be in range with valid weights)
        result[trait] = round(max(0.0, min(1.0, total)), 4)
    return result


def ocean_to_traits(profile: OceanProfile) -> dict[str, float]:
    """Map an OCEAN (Big Five) profile to the 10 custom personality traits."""
    values = {
        "openness": profile.openness,
        "conscientiousness": profile.conscientiousness,
        "extraversion": profile.extraversion,
        "agreeableness": profile.agreeableness,
        "neuroticism": profile.neuroticism,
    }
    return _apply_weights(OCEAN_WEIGHTS, values)


def disc_to_traits(profile: DiscProfile) -> dict[str, float]:
    """Map a DISC profile to the 10 custom personality traits."""
    values = {
        "dominance": profile.dominance,
        "influence": profile.influence,
        "steadiness": profile.steadiness,
        "conscientiousness": profile.conscientiousness,
    }
    return _apply_weights(DISC_WEIGHTS, values)


# ---------------------------------------------------------------------------
# Reverse mapping functions
# ---------------------------------------------------------------------------


def traits_to_ocean(traits: PersonalityTraits) -> OceanProfile:
    """Approximate reverse mapping from custom traits to OCEAN profile.

    Uses weighted-sum formulas from the AgentGov spec. The result is an
    approximation — a round-trip (ocean → traits → ocean) will not be exact.
    """
    defined = traits.defined_traits()
    # Use 0.5 as neutral default for undefined traits
    values = {
        "warmth": defined.get("warmth", 0.5),
        "verbosity": defined.get("verbosity", 0.5),
        "assertiveness": defined.get("assertiveness", 0.5),
        "humor": defined.get("humor", 0.5),
        "empathy": defined.get("empathy", 0.5),
        "directness": defined.get("directness", 0.5),
        "rigor": defined.get("rigor", 0.5),
        "creativity": defined.get("creativity", 0.5),
        "epistemic_humility": defined.get("epistemic_humility", 0.5),
        "patience": defined.get("patience", 0.5),
    }
    ocean_vals = _apply_weights(REVERSE_OCEAN_WEIGHTS, values)
    return OceanProfile(**ocean_vals)


def traits_to_disc(traits: PersonalityTraits) -> DiscProfile:
    """Approximate reverse mapping from custom traits to DISC profile.

    Uses weighted-sum formulas derived from the forward DISC mapping.
    The result is an approximation.
    """
    defined = traits.defined_traits()
    values = {
        "warmth": defined.get("warmth", 0.5),
        "verbosity": defined.get("verbosity", 0.5),
        "assertiveness": defined.get("assertiveness", 0.5),
        "humor": defined.get("humor", 0.5),
        "empathy": defined.get("empathy", 0.5),
        "directness": defined.get("directness", 0.5),
        "rigor": defined.get("rigor", 0.5),
        "creativity": defined.get("creativity", 0.5),
        "epistemic_humility": defined.get("epistemic_humility", 0.5),
        "patience": defined.get("patience", 0.5),
    }
    disc_vals = _apply_weights(REVERSE_DISC_WEIGHTS, values)
    return DiscProfile(**disc_vals)


# ---------------------------------------------------------------------------
# Preset lookup
# ---------------------------------------------------------------------------


def get_disc_preset(name: str) -> DiscProfile:
    """Look up a named DISC preset.

    Raises ``KeyError`` if the preset name is not found.
    """
    if name not in DISC_PRESETS:
        available = ", ".join(sorted(DISC_PRESETS.keys()))
        raise KeyError(f"Unknown DISC preset '{name}'. Available: {available}")
    return DISC_PRESETS[name]


def list_disc_presets() -> dict[str, DiscProfile]:
    """Return all available DISC presets."""
    return dict(DISC_PRESETS)


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------


def compute_personality_traits(personality: Personality) -> PersonalityTraits:
    """Compute the final personality traits from a Personality object.

    Routing logic by mode:

    - **custom**: returns ``personality.traits`` as-is
    - **ocean**: computes traits from ``personality.profile.ocean``
    - **disc**: computes traits from ``personality.profile.disc`` (or preset)
    - **hybrid**: computes from framework, then applies explicit overrides

    Returns a new ``PersonalityTraits`` instance with all 10 traits populated.
    """
    profile = personality.profile
    mode = profile.mode

    if mode == PersonalityMode.CUSTOM:
        return personality.traits

    # Compute base traits from framework
    if mode == PersonalityMode.OCEAN:
        if profile.ocean is None:
            raise ValueError("OCEAN mode requires an ocean profile to be set")
        computed = ocean_to_traits(profile.ocean)

    elif mode == PersonalityMode.DISC:
        disc = profile.disc
        if disc is None and profile.disc_preset:
            disc = get_disc_preset(profile.disc_preset)
        if disc is None:
            raise ValueError("DISC mode requires a disc profile or disc_preset to be set")
        computed = disc_to_traits(disc)

    elif mode == PersonalityMode.HYBRID:
        # HYBRID mode computes base traits from a framework profile, then applies
        # explicit trait overrides on top (see override_priority below). When both
        # OCEAN and DISC profiles are provided, OCEAN takes precedence as the base.
        # To use DISC as the base instead, omit the OCEAN profile from the identity.
        if profile.ocean is not None:
            computed = ocean_to_traits(profile.ocean)
        elif profile.disc is not None:
            computed = disc_to_traits(profile.disc)
        elif profile.disc_preset:
            disc = get_disc_preset(profile.disc_preset)
            computed = disc_to_traits(disc)
        else:
            # Should not happen — validated at model level
            computed = {}
    else:
        return personality.traits

    # For hybrid mode, apply explicit overrides
    if mode == PersonalityMode.HYBRID:
        explicit = personality.traits.defined_traits()
        if profile.override_priority == OverridePriority.EXPLICIT_WINS:
            # Explicit overrides win over computed values
            computed.update(explicit)
        else:
            # Framework wins — only fill in missing traits from explicit
            for k, v in explicit.items():
                if k not in computed:
                    computed[k] = v

    return PersonalityTraits(**computed)
