"""Tests for OCEAN/DISC/Jungian personality mapping functions."""

import pytest

from personanexus.personality import (
    closest_jungian_type,
    compute_personality_traits,
    disc_to_traits,
    get_disc_preset,
    get_jungian_preset,
    get_jungian_role_recommendations,
    jungian_to_traits,
    list_disc_presets,
    list_jungian_presets,
    ocean_to_traits,
    traits_to_disc,
    traits_to_jungian,
    traits_to_ocean,
)
from personanexus.types import (
    DiscProfile,
    JungianProfile,
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


# ---------------------------------------------------------------------------
# Jungian → Traits (forward mapping)
# ---------------------------------------------------------------------------


class TestJungianToTraits:
    def test_returns_all_ten_traits(self):
        profile = JungianProfile(ei=0.5, sn=0.5, tf=0.5, jp=0.5)
        traits = jungian_to_traits(profile)
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
        profile = JungianProfile(ei=0.8, sn=0.8, tf=0.2, jp=0.2)
        traits = jungian_to_traits(profile)
        for name, val in traits.items():
            assert 0.0 <= val <= 1.0, f"{name} = {val} out of range"

    def test_all_zeros(self):
        profile = JungianProfile(ei=0.0, sn=0.0, tf=0.0, jp=0.0)
        traits = jungian_to_traits(profile)
        for val in traits.values():
            assert 0.0 <= val <= 1.0

    def test_all_ones(self):
        profile = JungianProfile(ei=1.0, sn=1.0, tf=1.0, jp=1.0)
        traits = jungian_to_traits(profile)
        for val in traits.values():
            assert 0.0 <= val <= 1.0

    def test_neutral_profile_moderate_traits(self):
        profile = JungianProfile(ei=0.5, sn=0.5, tf=0.5, jp=0.5)
        traits = jungian_to_traits(profile)
        for val in traits.values():
            assert 0.3 <= val <= 0.7, f"Expected moderate value, got {val}"

    def test_intj_high_rigor_low_warmth(self):
        """INTJ (introvert, intuitive, thinking, judging) should have high rigor."""
        profile = get_jungian_preset("intj")
        traits = jungian_to_traits(profile)
        assert traits["rigor"] > 0.6
        assert traits["warmth"] < 0.5

    def test_enfp_high_creativity_high_warmth(self):
        """ENFP (extravert, intuitive, feeling, perceiving) should be creative and warm."""
        profile = get_jungian_preset("enfp")
        traits = jungian_to_traits(profile)
        assert traits["creativity"] > 0.6
        assert traits["warmth"] > 0.5

    def test_estj_high_assertiveness_high_directness(self):
        """ESTJ (extravert, sensing, thinking, judging) should be assertive and direct."""
        profile = get_jungian_preset("estj")
        traits = jungian_to_traits(profile)
        assert traits["assertiveness"] > 0.6
        assert traits["directness"] > 0.6

    def test_infp_high_empathy(self):
        """INFP (introvert, intuitive, feeling, perceiving) should be empathetic."""
        profile = get_jungian_preset("infp")
        traits = jungian_to_traits(profile)
        assert traits["empathy"] > 0.5

    @pytest.mark.parametrize("preset_name", list(list_jungian_presets().keys()))
    def test_all_16_presets_produce_valid_traits(self, preset_name):
        profile = get_jungian_preset(preset_name)
        traits = jungian_to_traits(profile)
        assert len(traits) == 10
        for name, val in traits.items():
            assert 0.0 <= val <= 1.0, f"{preset_name}: {name} = {val} out of range"


# ---------------------------------------------------------------------------
# Reverse mapping (traits → Jungian)
# ---------------------------------------------------------------------------


class TestTraitsToJungian:
    def test_returns_four_dims(self):
        traits = PersonalityTraits(
            warmth=0.7, rigor=0.9, empathy=0.7, directness=0.6, creativity=0.5
        )
        jungian = traits_to_jungian(traits)
        assert hasattr(jungian, "ei")
        assert hasattr(jungian, "sn")
        assert hasattr(jungian, "tf")
        assert hasattr(jungian, "jp")

    def test_values_in_range(self):
        traits = PersonalityTraits(
            warmth=0.7, rigor=0.9, empathy=0.7, directness=0.6, creativity=0.5
        )
        jungian = traits_to_jungian(traits)
        for dim in ["ei", "sn", "tf", "jp"]:
            val = getattr(jungian, dim)
            assert 0.0 <= val <= 1.0, f"{dim} = {val} out of range"

    def test_round_trip_approximate(self):
        """Jungian → traits → Jungian should be approximate (not exact)."""
        original = JungianProfile(ei=0.7, sn=0.8, tf=0.3, jp=0.2)
        traits_dict = jungian_to_traits(original)
        traits = PersonalityTraits(**traits_dict)
        recovered = traits_to_jungian(traits)
        for dim in ["ei", "sn", "tf", "jp"]:
            orig_val = getattr(original, dim)
            rec_val = getattr(recovered, dim)
            assert abs(orig_val - rec_val) < 0.4, f"{dim}: original={orig_val}, recovered={rec_val}"


# ---------------------------------------------------------------------------
# Jungian presets
# ---------------------------------------------------------------------------


class TestJungianPresets:
    def test_all_16_presets_exist(self):
        presets = list_jungian_presets()
        assert len(presets) == 16

    def test_known_preset_names(self):
        presets = list_jungian_presets()
        expected = {
            "intj",
            "intp",
            "entj",
            "entp",
            "infj",
            "infp",
            "enfj",
            "enfp",
            "istj",
            "isfj",
            "estj",
            "esfj",
            "istp",
            "isfp",
            "estp",
            "esfp",
        }
        assert set(presets.keys()) == expected

    def test_get_preset_case_insensitive(self):
        p1 = get_jungian_preset("INTJ")
        p2 = get_jungian_preset("intj")
        p3 = get_jungian_preset("Intj")
        assert p1.ei == p2.ei == p3.ei

    def test_get_preset_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown Jungian preset"):
            get_jungian_preset("xxxx")

    def test_intj_dimensions(self):
        p = get_jungian_preset("intj")
        assert p.ei == 0.8  # Introversion
        assert p.sn == 0.8  # iNtuition
        assert p.tf == 0.2  # Thinking
        assert p.jp == 0.2  # Judging


# ---------------------------------------------------------------------------
# Closest Jungian type
# ---------------------------------------------------------------------------


class TestClosestJungianType:
    @pytest.mark.parametrize("preset_name", list(list_jungian_presets().keys()))
    def test_preset_maps_to_itself(self, preset_name):
        """Each preset should be closest to itself."""
        profile = get_jungian_preset(preset_name)
        closest = closest_jungian_type(profile)
        assert closest.lower() == preset_name.lower()

    def test_near_intj_returns_intj(self):
        # Slightly off from INTJ preset
        profile = JungianProfile(ei=0.75, sn=0.85, tf=0.25, jp=0.15)
        closest = closest_jungian_type(profile)
        assert closest == "INTJ"


# ---------------------------------------------------------------------------
# Jungian role recommendations
# ---------------------------------------------------------------------------


class TestJungianRoleRecommendations:
    def test_known_role_returns_results(self):
        recs = get_jungian_role_recommendations("data_science")
        assert len(recs) >= 1
        # Each rec is (type_code, description)
        assert all(len(r) == 2 for r in recs)

    def test_unknown_role_raises(self):
        with pytest.raises(KeyError, match="Unknown role category"):
            get_jungian_role_recommendations("underwater_basket_weaving")

    def test_all_role_categories_have_recommendations(self):
        from personanexus.personality import JUNGIAN_ROLE_RECOMMENDATIONS

        for category, recs in JUNGIAN_ROLE_RECOMMENDATIONS.items():
            assert len(recs) >= 1, f"{category} has no recommendations"


# ---------------------------------------------------------------------------
# compute_personality_traits — Jungian mode
# ---------------------------------------------------------------------------


class TestComputePersonalityTraitsJungian:
    def test_jungian_mode_with_profile(self):
        personality = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.JUNGIAN,
                jungian=JungianProfile(ei=0.8, sn=0.8, tf=0.2, jp=0.2),
            ),
        )
        computed = compute_personality_traits(personality)
        assert len(computed.defined_traits()) == 10
        assert computed.rigor is not None
        assert computed.rigor > 0.6

    def test_jungian_mode_with_preset(self):
        personality = Personality(
            traits=PersonalityTraits(),
            profile=PersonalityProfile(
                mode=PersonalityMode.JUNGIAN,
                jungian_preset="enfp",
            ),
        )
        computed = compute_personality_traits(personality)
        assert len(computed.defined_traits()) == 10
        assert computed.creativity is not None
        assert computed.creativity > 0.5

    def test_hybrid_mode_with_jungian_base(self):
        personality = Personality(
            traits=PersonalityTraits(warmth=0.95),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                jungian_preset="intj",
                override_priority=OverridePriority.EXPLICIT_WINS,
            ),
        )
        computed = compute_personality_traits(personality)
        # Warmth should be the explicit override value
        assert computed.warmth == 0.95
        # Other traits should be computed from Jungian
        assert computed.rigor is not None

    def test_hybrid_mode_with_jungian_profile(self):
        personality = Personality(
            traits=PersonalityTraits(rigor=0.99),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                jungian=JungianProfile(ei=0.2, sn=0.8, tf=0.8, jp=0.8),
                override_priority=OverridePriority.EXPLICIT_WINS,
            ),
        )
        computed = compute_personality_traits(personality)
        assert computed.rigor == 0.99

    def test_hybrid_mode_with_disc_profile_directly(self):
        personality = Personality(
            traits=PersonalityTraits(warmth=0.9),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                disc=DiscProfile(
                    dominance=0.9,
                    influence=0.4,
                    steadiness=0.2,
                    conscientiousness=0.5,
                ),
                override_priority=OverridePriority.EXPLICIT_WINS,
            ),
        )
        computed = compute_personality_traits(personality)
        assert computed.warmth == 0.9
        assert len(computed.defined_traits()) == 10

    def test_hybrid_mode_with_disc_preset(self):
        personality = Personality(
            traits=PersonalityTraits(humor=0.8),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                disc_preset="the_commander",
                override_priority=OverridePriority.EXPLICIT_WINS,
            ),
        )
        computed = compute_personality_traits(personality)
        assert computed.humor == 0.8
        assert len(computed.defined_traits()) == 10

    def test_hybrid_mode_framework_wins(self):
        personality = Personality(
            traits=PersonalityTraits(warmth=0.1),
            profile=PersonalityProfile(
                mode=PersonalityMode.HYBRID,
                jungian_preset="enfp",
                override_priority=OverridePriority.FRAMEWORK_WINS,
            ),
        )
        computed = compute_personality_traits(personality)
        # Framework should win — warmth should be computed from ENFP, not the explicit 0.1
        assert computed.warmth != 0.1
        assert len(computed.defined_traits()) == 10
