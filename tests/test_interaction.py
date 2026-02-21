"""Tests for interaction protocols."""
import pytest
from personanexus.types import (
    HumanInteraction, AgentInteraction, InteractionConfig,
    InteractionEscalationTrigger
)
from personanexus.compiler import SystemPromptCompiler


def test_human_interaction_defaults():
    h = HumanInteraction()
    assert h.greeting_style is None
    assert h.tone_matching is False
    assert h.escalation_triggers == []


def test_human_interaction_full():
    h = HumanInteraction(
        greeting_style="warm-personal",
        farewell_style="encouraging",
        tone_matching=True,
        escalation_triggers=[
            InteractionEscalationTrigger.UNABLE_TO_HELP,
            InteractionEscalationTrigger.SAFETY_CONCERN
        ],
        escalation_message="Let me connect you with someone who can help."
    )
    assert h.tone_matching is True
    assert len(h.escalation_triggers) == 2


def test_agent_interaction_defaults():
    a = AgentInteraction()
    assert a.handoff_style == "structured"
    assert a.status_reporting == "on_request"
    assert a.conflict_resolution == "defer_to_hierarchy"


def test_interaction_config():
    config = InteractionConfig(
        human=HumanInteraction(greeting_style="professional", tone_matching=True),
        agent=AgentInteraction(handoff_style="verbose", status_reporting="proactive")
    )
    assert config.human.greeting_style == "professional"
    assert config.agent.status_reporting == "proactive"


def test_compiler_renders_interaction():
    compiler = SystemPromptCompiler()
    config = InteractionConfig(
        human=HumanInteraction(
            greeting_style="warm",
            tone_matching=True,
            escalation_triggers=[InteractionEscalationTrigger.UNABLE_TO_HELP],
            escalation_message="Connecting you with a human."
        ),
        agent=AgentInteraction(handoff_style="structured")
    )
    result = compiler._render_interaction(config)
    assert "Interaction Protocols" in result
    assert "warm" in result
    assert "Tone matching" in result
    assert "unable_to_help" in result
    assert "structured" in result


def test_compiler_renders_none():
    compiler = SystemPromptCompiler()
    assert compiler._render_interaction(None) == ""


def test_all_escalation_triggers():
    for t in InteractionEscalationTrigger:
        h = HumanInteraction(escalation_triggers=[t])
        assert len(h.escalation_triggers) == 1
