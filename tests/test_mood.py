"""Tests for mood/emotional state system."""
from pathlib import Path

import pytest

from personanexus.compiler import SystemPromptCompiler
from personanexus.parser import IdentityParser
from personanexus.types import (
    MoodConfig,
    MoodState,
    MoodTransition,
    OceanProfile,
    Personality,
    PersonalityMode,
    PersonalityProfile,
    TraitModifier,
)


def test_mood_state_creation():
    state = MoodState(
        name="focused",
        description="Deep work",
        trait_modifiers=[TraitModifier(trait="conscientiousness", delta=0.15)],
        tone_override="precise"
    )
    assert state.name == "focused"
    assert len(state.trait_modifiers) == 1


def test_mood_config_default():
    config = MoodConfig()
    assert config.default == "neutral"
    assert config.states == []


def test_mood_config_with_states():
    config = MoodConfig(
        default="neutral",
        states=[
            MoodState(name="focused", trait_modifiers=[
                TraitModifier(trait="conscientiousness", delta=0.15)
            ]),
            MoodState(name="empathetic", trait_modifiers=[
                TraitModifier(trait="agreeableness", delta=0.2)
            ])
        ],
        transitions=[
            MoodTransition(to_state="focused", trigger="complex_query")
        ]
    )
    assert len(config.states) == 2
    assert config.transitions[0].from_state == "*"


def test_personality_with_mood():
    p = Personality(
        profile=PersonalityProfile(
            mode=PersonalityMode.OCEAN,
            ocean=OceanProfile(openness=0.7, conscientiousness=0.8,
                             extraversion=0.5, agreeableness=0.6, neuroticism=0.2)
        ),
        mood=MoodConfig(
            default="neutral",
            states=[MoodState(name="focused")]
        )
    )
    assert p.mood is not None
    assert p.mood.default == "neutral"


def test_personality_without_mood():
    p = Personality(
        profile=PersonalityProfile(
            mode=PersonalityMode.OCEAN,
            ocean=OceanProfile(openness=0.7, conscientiousness=0.8,
                             extraversion=0.5, agreeableness=0.6, neuroticism=0.2)
        )
    )
    assert p.mood is None


def test_trait_modifier_bounds():
    with pytest.raises(Exception):
        TraitModifier(trait="x", delta=1.5)
    with pytest.raises(Exception):
        TraitModifier(trait="x", delta=-1.5)


def test_compiler_renders_mood():
    compiler = SystemPromptCompiler()
    p = Personality(
        profile=PersonalityProfile(
            mode=PersonalityMode.OCEAN,
            ocean=OceanProfile(openness=0.7, conscientiousness=0.8,
                             extraversion=0.5, agreeableness=0.6, neuroticism=0.2)
        ),
        mood=MoodConfig(
            default="neutral",
            states=[
                MoodState(name="focused", description="Deep work",
                         trait_modifiers=[TraitModifier(trait="conscientiousness", delta=0.15)])
            ]
        )
    )
    result = compiler._render_personality(p)
    assert "Emotional States" in result or "Mood" in result
    assert "focused" in result


def test_example_yaml_loads():
    examples_dir = Path(__file__).parent.parent / "examples"
    parser = IdentityParser()
    identity = parser.load_identity(
        examples_dir / "identities" / "ada-mood.yaml"
    )
    assert identity.personality.mood is not None
    assert len(identity.personality.mood.states) >= 2
