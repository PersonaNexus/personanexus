"""Tests for behavioral modes system."""
import pytest
from personanexus.types import (
    BehavioralMode,
    BehavioralModeConfig,
    BehavioralModeOverrides,
    TraitModifier,
    AgentIdentity,
)
from personanexus.compiler import SystemPromptCompiler
from personanexus.parser import parse_identity_file


def test_mode_creation():
    mode = BehavioralMode(
        name="formal",
        description="Client-facing",
        overrides=BehavioralModeOverrides(
            tone_register="formal",
            trait_modifiers=[TraitModifier(trait="warmth", delta=-0.1)]
        )
    )
    assert mode.name == "formal"
    assert mode.overrides.tone_register == "formal"


def test_mode_config_default():
    config = BehavioralModeConfig()
    assert config.default == "standard"
    assert config.modes == []


def test_mode_config_with_modes():
    config = BehavioralModeConfig(
        default="standard",
        modes=[
            BehavioralMode(name="standard"),
            BehavioralMode(name="formal", overrides=BehavioralModeOverrides(
                tone_register="formal", emoji_usage="never"
            )),
            BehavioralMode(name="crisis", additional_guardrails=["Escalate always"])
        ]
    )
    assert len(config.modes) == 3
    assert config.modes[2].additional_guardrails == ["Escalate always"]


def test_compiler_renders_modes():
    compiler = SystemPromptCompiler()
    config = BehavioralModeConfig(
        default="standard",
        modes=[
            BehavioralMode(name="standard", description="Default"),
            BehavioralMode(name="formal", description="Executive comms",
                          overrides=BehavioralModeOverrides(tone_register="formal"))
        ]
    )
    result = compiler._render_behavioral_modes(config)
    assert "Behavioral Modes" in result
    assert "formal" in result
    assert "Executive comms" in result


def test_compiler_renders_empty_modes():
    compiler = SystemPromptCompiler()
    assert compiler._render_behavioral_modes(None) == ""
    assert compiler._render_behavioral_modes(BehavioralModeConfig()) == ""


def test_example_yaml_loads():
    identity = parse_identity_file(
        "examples/identities/ada-modes.yaml",
        base_dir="/home/node/.openclaw/workspace/personanexus"
    )
    assert identity.behavioral_modes is not None
    assert len(identity.behavioral_modes.modes) >= 3
    assert identity.behavioral_modes.default == "standard"
