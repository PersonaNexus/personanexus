"""Tests for enhanced agent relationships."""

from personanexus.compiler import SystemPromptCompiler
from personanexus.types import (
    AgentRelationship,
    Memory,
    RelationshipDynamic,
    Relationships,
)


def test_relationship_with_dynamic():
    r = AgentRelationship(
        agent_id="agt_rex_001",
        name="Rex",
        relationship="security advisor",
        dynamic=RelationshipDynamic.DEFERS_TO,
        context="Security and compliance decisions",
        interaction_style="formal-respectful",
    )
    assert r.dynamic == RelationshipDynamic.DEFERS_TO
    assert r.name == "Rex"
    assert r.context == "Security and compliance decisions"


def test_relationship_backward_compat():
    r = AgentRelationship(agent_id="agt_old_001", relationship="collaborator")
    assert r.dynamic is None
    assert r.name is None
    assert r.interaction_style is None


def test_relationships_escalation():
    rels = Relationships(
        enabled=True,
        agent_relationships=[
            AgentRelationship(agent_id="a1", relationship="peer"),
            AgentRelationship(
                agent_id="a2",
                relationship="supervisor",
                dynamic=RelationshipDynamic.ESCALATES_TO,
            ),
        ],
        escalation_path=["a2", "human_operator"],
        unknown_agent_default="professional-cautious",
    )
    assert len(rels.escalation_path) == 2
    assert rels.unknown_agent_default == "professional-cautious"


def test_all_dynamics():
    for d in RelationshipDynamic:
        r = AgentRelationship(agent_id="x", relationship="test", dynamic=d)
        assert r.dynamic == d


def test_compiler_renders_relationships():
    compiler = SystemPromptCompiler()
    mem = Memory()
    mem.relationships = Relationships(
        enabled=True,
        agent_relationships=[
            AgentRelationship(
                agent_id="agt_rex",
                name="Rex",
                relationship="security lead",
                dynamic=RelationshipDynamic.DEFERS_TO,
                context="compliance matters",
                interaction_style="formal",
            )
        ],
        escalation_path=["agt_rex", "human"],
        unknown_agent_default="cautious",
    )
    result = compiler._render_relationships(mem)
    assert "Agent Relationships" in result
    assert "Rex" in result
    assert "defers_to" in result
    assert "Escalation path" in result


def test_compiler_empty_relationships():
    compiler = SystemPromptCompiler()
    mem = Memory()
    result = compiler._render_relationships(mem)
    assert result == ""
