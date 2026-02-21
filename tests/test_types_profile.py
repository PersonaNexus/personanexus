"""Tests for personality profile Pydantic models and validation."""

import pytest
from pydantic import ValidationError

from personanexus.types import (
    DiscProfile,
    OceanProfile,
    OverridePriority,
    Personality,
    PersonalityMode,
    PersonalityProfile,
    PersonalityTraits,
)


# ---------------------------------------------------------------------------
# OceanProfile
# ---------------------------------------------------------------------------


class TestOceanProfile:
    def test_valid_profile(self):
        profile = OceanProfile(
            openness=0.7, conscientiousness=0.8,
            extraversion=0.5, agreeableness=0.6, neuroticism=0.3,
        )
        assert profile.openness == 0.7

    def test_boundary_values(self):
        profile = OceanProfile(
            openness=0.0, conscientiousness=1.0,
            extraversion=0.0, agreeableness=1.0, neuroticism=0.0,
        )
        assert profile.openness == 0.0
        assert profile.conscientiousness == 1.0

    def test_out_of_range_high(self):
        with pytest.raises(ValidationError):
            OceanProfile(
                openness=1.5, conscientiousness=0.5,
                extraversion=0.5, agreeableness=0.5, neuroticism=0.5,
            )

    def test_out_of_range_low(self):
        with pytest.raises(ValidationError):
            OceanProfile(
                openness=-0.1, conscientiousness=0.5,
                extraversion=0.5, agreeableness=0.5, neuroticism=0.5,
            )

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            OceanProfile(
                openness=0.5, conscientiousness=0.5,
                extraversion=0.5, agreeableness=0.5,
                # missing neuroticism
            )


# ---------------------------------------------------------------------------
# DiscProfile
# ---------------------------------------------------------------------------


class TestDiscProfile:
    def test_valid_profile(self):
        profile = DiscProfile(
            dominance=0.9, influence=0.4,
            steadiness=0.2, conscientiousness=0.5,
        )
        assert profile.dominance == 0.9

    def test_out_of_range(self):
        with pytest.raises(ValidationError):
            DiscProfile(
                dominance=1.5, influence=0.4,
                steadiness=0.2, conscientiousness=0.5,
            )

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            DiscProfile(
                dominance=0.9, influence=0.4,
                steadiness=0.2,
                # missing conscientiousness
            )


# ---------------------------------------------------------------------------
# PersonalityProfile
# ---------------------------------------------------------------------------


class TestPersonalityProfile:
    def test_default_is_custom(self):
        profile = PersonalityProfile()
        assert profile.mode == PersonalityMode.CUSTOM
        assert profile.ocean is None
        assert profile.disc is None
        assert profile.disc_preset is None
        assert profile.override_priority == OverridePriority.EXPLICIT_WINS

    def test_ocean_mode(self):
        profile = PersonalityProfile(
            mode=PersonalityMode.OCEAN,
            ocean=OceanProfile(
                openness=0.7, conscientiousness=0.8,
                extraversion=0.5, agreeableness=0.6, neuroticism=0.3,
            ),
        )
        assert profile.mode == PersonalityMode.OCEAN
        assert profile.ocean is not None

    def test_disc_mode_with_profile(self):
        profile = PersonalityProfile(
            mode=PersonalityMode.DISC,
            disc=DiscProfile(
                dominance=0.9, influence=0.4,
                steadiness=0.2, conscientiousness=0.5,
            ),
        )
        assert profile.mode == PersonalityMode.DISC
        assert profile.disc is not None

    def test_disc_mode_with_preset(self):
        profile = PersonalityProfile(
            mode=PersonalityMode.DISC,
            disc_preset="the_commander",
        )
        assert profile.disc_preset == "the_commander"


# ---------------------------------------------------------------------------
# Personality model validation
# ---------------------------------------------------------------------------


class TestPersonalityValidation:
    def test_custom_mode_requires_two_traits(self):
        with pytest.raises(ValidationError, match="At least 2"):
            Personality(
                traits=PersonalityTraits(warmth=0.7),
            )

    def test_custom_mode_valid_with_two_traits(self):
        p = Personality(
            traits=PersonalityTraits(warmth=0.7, rigor=0.9),
        )
        assert p.traits.warmth == 0.7

    def test_ocean_mode_requires_ocean_profile(self):
        with pytest.raises(ValidationError, match="OCEAN profile is required"):
            Personality(
                traits=PersonalityTraits(),
                profile=PersonalityProfile(mode=PersonalityMode.OCEAN),
            )

    def test_ocean_mode_valid(self):
        p = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.OCEAN,
                ocean=OceanProfile(
                    openness=0.5, conscientiousness=0.5,
                    extraversion=0.5, agreeableness=0.5, neuroticism=0.5,
                ),
            ),
        )
        assert p.profile.mode == PersonalityMode.OCEAN

    def test_disc_mode_requires_disc_or_preset(self):
        with pytest.raises(ValidationError, match="DISC profile or disc_preset"):
            Personality(
                traits=PersonalityTraits(),
                profile=PersonalityProfile(mode=PersonalityMode.DISC),
            )

    def test_disc_mode_valid_with_profile(self):
        p = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.DISC,
                disc=DiscProfile(
                    dominance=0.9, influence=0.4,
                    steadiness=0.2, conscientiousness=0.5,
                ),
            ),
        )
        assert p.profile.mode == PersonalityMode.DISC

    def test_disc_mode_valid_with_preset(self):
        p = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.DISC,
                disc_preset="the_analyst",
            ),
        )
        assert p.profile.disc_preset == "the_analyst"

    def test_hybrid_mode_requires_framework(self):
        with pytest.raises(ValidationError, match="framework profile"):
            Personality(
                traits=PersonalityTraits(warmth=0.7),
                profile=PersonalityProfile(mode=PersonalityMode.HYBRID),
            )

    def test_hybrid_mode_requires_overrides(self):
        with pytest.raises(ValidationError, match="explicit trait override"):
            Personality(
                traits=PersonalityTraits(),
                profile=PersonalityProfile(
                    mode=PersonalityMode.HYBRID,
                    ocean=OceanProfile(
                        openness=0.5, conscientiousness=0.5,
                        extraversion=0.5, agreeableness=0.5, neuroticism=0.5,
                    ),
                ),
            )

    def test_hybrid_mode_valid(self):
        p = Personality(
            traits=PersonalityTraits(warmth=0.85),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                ocean=OceanProfile(
                    openness=0.5, conscientiousness=0.5,
                    extraversion=0.5, agreeableness=0.5, neuroticism=0.5,
                ),
            ),
        )
        assert p.profile.mode == PersonalityMode.HYBRID

    def test_backwards_compat_no_profile(self):
        """Personality without explicit profile defaults to custom mode."""
        p = Personality(
            traits=PersonalityTraits(warmth=0.7, rigor=0.9),
        )
        assert p.profile.mode == PersonalityMode.CUSTOM
        assert p.profile.ocean is None

    def test_backwards_compat_from_dict(self):
        """Simulate parsing from YAML without profile field."""
        data = {
            "traits": {"warmth": 0.7, "rigor": 0.9},
        }
        p = Personality.model_validate(data)
        assert p.profile.mode == PersonalityMode.CUSTOM
