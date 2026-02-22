"""Tests for OCEAN/DISC personality mapping functions."""

import pytest

from personanexus.personality import (
    compute_personality_traits,
    disc_to_traits,
    get_disc_preset,
    list_disc_presets,
    ocean_to_traits,
    traits_to_disc,
    traits_to_ocean,
)
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
# OCEAN → Traits (forward mapping)
# ---------------------------------------------------------------------------


class TestOceanToTraits:
    def test_returns_all_ten_traits(self):
        profile = OceanProfile(
            openness=0.5,
            conscientiousness=0.5,
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
        )
        traits = ocean_to_traits(profile)
        assert len(traits) == 10
        expected_keys = {
            "warmth",
            "verbosity",
            "assertiveness",
            "humor",
            "empathy",
            "directness",
            "rigor",
            "creativity",
            "epistemic_humility",
            "patience",
        }
        assert set(traits.keys()) == expected_keys

    def test_all_values_in_range(self):
        profile = OceanProfile(
            openness=0.8,
            conscientiousness=0.6,
            extraversion=0.7,
            agreeableness=0.5,
            neuroticism=0.3,
        )
        traits = ocean_to_traits(profile)
        for name, val in traits.items():
            assert 0.0 <= val <= 1.0, f"{name} = {val} out of range"

    def test_high_conscientiousness_high_rigor(self):
        profile = OceanProfile(
            openness=0.5,
            conscientiousness=0.95,
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.1,
        )
        traits = ocean_to_traits(profile)
        assert traits["rigor"] > 0.7

    def test_high_agreeableness_high_empathy(self):
        profile = OceanProfile(
            openness=0.5,
            conscientiousness=0.5,
            extraversion=0.5,
            agreeableness=0.95,
            neuroticism=0.1,
        )
        traits = ocean_to_traits(profile)
        assert traits["empathy"] > 0.7

    def test_high_openness_high_creativity(self):
        profile = OceanProfile(
            openness=0.95,
            conscientiousness=0.2,
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
        )
        traits = ocean_to_traits(profile)
        assert traits["creativity"] > 0.6

    def test_high_extraversion_high_assertiveness(self):
        profile = OceanProfile(
            openness=0.5,
            conscientiousness=0.5,
            extraversion=0.95,
            agreeableness=0.3,
            neuroticism=0.1,
        )
        traits = ocean_to_traits(profile)
        assert traits["assertiveness"] > 0.6

    def test_all_zeros(self):
        profile = OceanProfile(
            openness=0.0,
            conscientiousness=0.0,
            extraversion=0.0,
            agreeableness=0.0,
            neuroticism=0.0,
        )
        traits = ocean_to_traits(profile)
        for val in traits.values():
            assert 0.0 <= val <= 1.0

    def test_all_ones(self):
        profile = OceanProfile(
            openness=1.0,
            conscientiousness=1.0,
            extraversion=1.0,
            agreeableness=1.0,
            neuroticism=1.0,
        )
        traits = ocean_to_traits(profile)
        for val in traits.values():
            assert 0.0 <= val <= 1.0

    def test_neutral_profile_moderate_traits(self):
        """All 0.5 inputs should give moderate trait values."""
        profile = OceanProfile(
            openness=0.5,
            conscientiousness=0.5,
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
        )
        traits = ocean_to_traits(profile)
        for val in traits.values():
            assert 0.3 <= val <= 0.7, f"Expected moderate value, got {val}"


# ---------------------------------------------------------------------------
# DISC → Traits (forward mapping)
# ---------------------------------------------------------------------------


class TestDiscToTraits:
    def test_returns_all_ten_traits(self):
        profile = DiscProfile(
            dominance=0.5,
            influence=0.5,
            steadiness=0.5,
            conscientiousness=0.5,
        )
        traits = disc_to_traits(profile)
        assert len(traits) == 10

    def test_all_values_in_range(self):
        profile = DiscProfile(
            dominance=0.9,
            influence=0.4,
            steadiness=0.2,
            conscientiousness=0.5,
        )
        traits = disc_to_traits(profile)
        for name, val in traits.items():
            assert 0.0 <= val <= 1.0, f"{name} = {val} out of range"

    def test_high_dominance_high_assertiveness(self):
        profile = DiscProfile(
            dominance=0.95,
            influence=0.3,
            steadiness=0.2,
            conscientiousness=0.5,
        )
        traits = disc_to_traits(profile)
        assert traits["assertiveness"] > 0.7

    def test_high_influence_high_humor(self):
        profile = DiscProfile(
            dominance=0.2,
            influence=0.95,
            steadiness=0.5,
            conscientiousness=0.3,
        )
        traits = disc_to_traits(profile)
        assert traits["humor"] > 0.5

    def test_high_steadiness_high_patience(self):
        profile = DiscProfile(
            dominance=0.2,
            influence=0.3,
            steadiness=0.95,
            conscientiousness=0.5,
        )
        traits = disc_to_traits(profile)
        assert traits["patience"] > 0.6

    def test_high_conscientiousness_high_rigor(self):
        profile = DiscProfile(
            dominance=0.3,
            influence=0.2,
            steadiness=0.5,
            conscientiousness=0.95,
        )
        traits = disc_to_traits(profile)
        assert traits["rigor"] > 0.6


# ---------------------------------------------------------------------------
# Reverse mapping (traits → OCEAN/DISC)
# ---------------------------------------------------------------------------


class TestReverseMapping:
    def test_traits_to_ocean_returns_five_dims(self):
        traits = PersonalityTraits(
            warmth=0.7,
            rigor=0.9,
            empathy=0.7,
            directness=0.6,
            creativity=0.5,
        )
        ocean = traits_to_ocean(traits)
        assert hasattr(ocean, "openness")
        assert hasattr(ocean, "conscientiousness")
        assert hasattr(ocean, "extraversion")
        assert hasattr(ocean, "agreeableness")
        assert hasattr(ocean, "neuroticism")

    def test_traits_to_ocean_values_in_range(self):
        traits = PersonalityTraits(
            warmth=0.7,
            rigor=0.9,
            empathy=0.7,
            directness=0.6,
            creativity=0.5,
        )
        ocean = traits_to_ocean(traits)
        dims = [
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
        ]
        for dim in dims:
            val = getattr(ocean, dim)
            assert 0.0 <= val <= 1.0, f"{dim} = {val} out of range"

    def test_traits_to_disc_returns_four_dims(self):
        traits = PersonalityTraits(
            warmth=0.7,
            rigor=0.9,
            empathy=0.7,
            directness=0.6,
            creativity=0.5,
        )
        disc = traits_to_disc(traits)
        assert hasattr(disc, "dominance")
        assert hasattr(disc, "influence")
        assert hasattr(disc, "steadiness")
        assert hasattr(disc, "conscientiousness")

    def test_traits_to_disc_values_in_range(self):
        traits = PersonalityTraits(
            warmth=0.7,
            rigor=0.9,
            empathy=0.7,
            directness=0.6,
            creativity=0.5,
        )
        disc = traits_to_disc(traits)
        for dim in ["dominance", "influence", "steadiness", "conscientiousness"]:
            val = getattr(disc, dim)
            assert 0.0 <= val <= 1.0, f"{dim} = {val} out of range"

    def test_round_trip_ocean_approximate(self):
        """OCEAN → traits → OCEAN should be approximate (not exact)."""
        original = OceanProfile(
            openness=0.7,
            conscientiousness=0.8,
            extraversion=0.6,
            agreeableness=0.5,
            neuroticism=0.3,
        )
        traits_dict = ocean_to_traits(original)
        traits = PersonalityTraits(**traits_dict)
        recovered = traits_to_ocean(traits)

        # Should be within ~0.2 of original (approximate mapping)
        dims = [
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
        ]
        for dim in dims:
            orig_val = getattr(original, dim)
            rec_val = getattr(recovered, dim)
            assert abs(orig_val - rec_val) < 0.3, f"{dim}: original={orig_val}, recovered={rec_val}"


# ---------------------------------------------------------------------------
# DISC presets
# ---------------------------------------------------------------------------


class TestDiscPresets:
    def test_all_four_presets_exist(self):
        presets = list_disc_presets()
        assert "the_commander" in presets
        assert "the_influencer" in presets
        assert "the_steady_hand" in presets
        assert "the_analyst" in presets

    @pytest.mark.parametrize(
        "preset_name,dom,inf,ste,con",
        [
            ("the_commander", 0.9, 0.4, 0.2, 0.5),
            ("the_analyst", 0.3, 0.2, 0.6, 0.9),
        ],
        ids=["commander", "analyst"],
    )
    def test_disc_preset_values(self, preset_name, dom, inf, ste, con):
        profile = get_disc_preset(preset_name)
        assert profile.dominance == dom
        assert profile.conscientiousness == con

    def test_get_disc_preset_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown DISC preset"):
            get_disc_preset("the_pirate")

    @pytest.mark.parametrize(
        "preset_name,expected_trait,min_val",
        [
            ("the_commander", "assertiveness", 0.7),
            ("the_analyst", "rigor", 0.6),
        ],
        ids=["commander-assertiveness", "analyst-rigor"],
    )
    def test_preset_trait_patterns(self, preset_name, expected_trait, min_val):
        profile = get_disc_preset(preset_name)
        traits = disc_to_traits(profile)
        assert traits[expected_trait] > min_val


# ---------------------------------------------------------------------------
# compute_personality_traits
# ---------------------------------------------------------------------------


class TestComputePersonalityTraits:
    def test_custom_mode_returns_original_traits(self):
        personality = Personality(
            traits=PersonalityTraits(warmth=0.7, rigor=0.9),
        )
        computed = compute_personality_traits(personality)
        assert computed.warmth == 0.7
        assert computed.rigor == 0.9

    def test_ocean_mode_computes_traits(self):
        personality = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.OCEAN,
                ocean=OceanProfile(
                    openness=0.7,
                    conscientiousness=0.85,
                    extraversion=0.5,
                    agreeableness=0.6,
                    neuroticism=0.2,
                ),
            ),
        )
        computed = compute_personality_traits(personality)
        assert len(computed.defined_traits()) == 10
        assert computed.rigor is not None
        assert computed.rigor > 0.6

    def test_disc_mode_with_profile(self):
        personality = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.DISC,
                disc=DiscProfile(
                    dominance=0.9,
                    influence=0.4,
                    steadiness=0.2,
                    conscientiousness=0.5,
                ),
            ),
        )
        computed = compute_personality_traits(personality)
        assert len(computed.defined_traits()) == 10
        assert computed.assertiveness is not None
        assert computed.assertiveness > 0.7

    def test_disc_mode_with_preset(self):
        personality = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.DISC,
                disc_preset="the_analyst",
            ),
        )
        computed = compute_personality_traits(personality)
        assert len(computed.defined_traits()) == 10
        assert computed.rigor is not None
        assert computed.rigor > 0.6

    def test_hybrid_mode_explicit_wins(self):
        personality = Personality(
            traits=PersonalityTraits(warmth=0.95),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                ocean=OceanProfile(
                    openness=0.5,
                    conscientiousness=0.5,
                    extraversion=0.5,
                    agreeableness=0.5,
                    neuroticism=0.5,
                ),
                override_priority=OverridePriority.EXPLICIT_WINS,
            ),
        )
        computed = compute_personality_traits(personality)
        # Warmth should be the explicit override value
        assert computed.warmth == 0.95
        # Other traits should be computed from OCEAN
        assert computed.rigor is not None

    def test_hybrid_mode_framework_wins(self):
        personality = Personality(
            traits=PersonalityTraits(warmth=0.95),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                ocean=OceanProfile(
                    openness=0.5,
                    conscientiousness=0.5,
                    extraversion=0.5,
                    agreeableness=0.5,
                    neuroticism=0.5,
                ),
                override_priority=OverridePriority.FRAMEWORK_WINS,
            ),
        )
        computed = compute_personality_traits(personality)
        # Warmth should be the framework-computed value (not 0.95)
        assert computed.warmth != 0.95
