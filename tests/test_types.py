"""Tests for Pydantic type models."""

import pytest
from pydantic import ValidationError

from personanexus.types import (
    AgentIdentity,
    Metadata,
    Personality,
    PersonalityTraits,
    Scope,
)


def _minimal_identity(**overrides):
    """Build a minimal valid AgentIdentity dict, with optional overrides."""
    data = {
        "schema_version": "1.0",
        "metadata": {
            "id": "agt_test_001",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "A test agent",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "draft",
        },
        "role": {
            "title": "Tester",
            "purpose": "Test things",
            "scope": {"primary": ["testing"]},
        },
        "personality": {"traits": {"warmth": 0.5, "rigor": 0.5}},
        "communication": {
            "tone": {"default": "neutral"},
            "language": {"primary": "en"},
        },
        "principles": [{"id": "be_good", "priority": 1, "statement": "Be good"}],
        "guardrails": {
            "hard": [
                {
                    "id": "no_harm",
                    "rule": "Do no harm",
                    "enforcement": "output_filter",
                    "severity": "critical",
                }
            ]
        },
    }
    data.update(overrides)
    return data


class TestAgentIdentity:
    def test_minimal_valid(self):
        identity = AgentIdentity.model_validate(_minimal_identity())
        assert identity.metadata.name == "Test Agent"
        assert identity.schema_version == "1.0"

    def test_missing_metadata(self):
        data = _minimal_identity()
        del data["metadata"]
        with pytest.raises(ValidationError, match="metadata"):
            AgentIdentity.model_validate(data)

    def test_missing_role(self):
        data = _minimal_identity()
        del data["role"]
        with pytest.raises(ValidationError, match="role"):
            AgentIdentity.model_validate(data)

    def test_missing_personality(self):
        data = _minimal_identity()
        del data["personality"]
        with pytest.raises(ValidationError, match="personality"):
            AgentIdentity.model_validate(data)

    def test_missing_principles(self):
        data = _minimal_identity()
        del data["principles"]
        with pytest.raises(ValidationError, match="principles"):
            AgentIdentity.model_validate(data)

    def test_missing_guardrails(self):
        data = _minimal_identity()
        del data["guardrails"]
        with pytest.raises(ValidationError, match="guardrails"):
            AgentIdentity.model_validate(data)

    def test_invalid_schema_version(self):
        with pytest.raises(ValidationError, match="schema_version"):
            AgentIdentity.model_validate(_minimal_identity(schema_version="abc"))

    def test_extends_and_mixins(self):
        identity = AgentIdentity.model_validate(
            _minimal_identity(extends="archetypes/analyst", mixins=["mixins/empathetic"])
        )
        assert identity.extends == "archetypes/analyst"
        assert identity.mixins == ["mixins/empathetic"]


class TestMetadata:
    def test_valid_id_pattern(self):
        m = Metadata(
            id="agt_test_123",
            name="Test",
            version="1.0.0",
            description="A test",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            status="active",
        )
        assert m.id == "agt_test_123"

    def test_invalid_id_pattern(self):
        with pytest.raises(ValidationError, match="id"):
            Metadata(
                id="bad-id",
                name="Test",
                version="1.0.0",
                description="A test",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                status="active",
            )

    def test_invalid_version(self):
        with pytest.raises(ValidationError, match="version"):
            Metadata(
                id="agt_test",
                name="Test",
                version="not-semver",
                description="A test",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                status="active",
            )

    def test_name_length_limit(self):
        with pytest.raises(ValidationError, match="name"):
            Metadata(
                id="agt_test",
                name="x" * 101,
                version="1.0.0",
                description="A test",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                status="active",
            )

    def test_invalid_status(self):
        with pytest.raises(ValidationError, match="status"):
            Metadata(
                id="agt_test",
                name="Test",
                version="1.0.0",
                description="A test",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                status="invalid",
            )


class TestPersonalityTraits:
    def test_valid_traits(self):
        traits = PersonalityTraits(warmth=0.7, rigor=0.9)
        assert traits.warmth == 0.7
        assert traits.rigor == 0.9

    def test_trait_out_of_range_high(self):
        with pytest.raises(ValidationError):
            PersonalityTraits(warmth=1.5, rigor=0.5)

    def test_trait_out_of_range_low(self):
        with pytest.raises(ValidationError):
            PersonalityTraits(warmth=-0.1, rigor=0.5)

    def test_fewer_than_two_traits_in_custom_mode(self):
        """In custom mode, Personality requires at least 2 traits."""
        with pytest.raises(ValidationError, match="At least 2"):
            Personality(traits=PersonalityTraits(warmth=0.5))

    def test_single_trait_allowed_on_personalitytraits(self):
        """PersonalityTraits itself no longer enforces the 2-trait minimum."""
        traits = PersonalityTraits(warmth=0.5)
        assert traits.warmth == 0.5

    def test_all_ten_traits(self):
        traits = PersonalityTraits(
            warmth=0.5,
            verbosity=0.5,
            assertiveness=0.5,
            humor=0.5,
            empathy=0.5,
            directness=0.5,
            rigor=0.5,
            creativity=0.5,
            epistemic_humility=0.5,
            patience=0.5,
        )
        assert len(traits.defined_traits()) == 10

    def test_defined_traits_excludes_none(self):
        traits = PersonalityTraits(warmth=0.7, rigor=0.9)
        defined = traits.defined_traits()
        assert "warmth" in defined
        assert "rigor" in defined
        assert "humor" not in defined

    def test_boundary_values(self):
        traits = PersonalityTraits(warmth=0.0, rigor=1.0)
        assert traits.warmth == 0.0
        assert traits.rigor == 1.0


class TestPrinciples:
    def test_duplicate_priorities_rejected(self):
        data = _minimal_identity()
        data["principles"] = [
            {"id": "p1", "priority": 1, "statement": "First"},
            {"id": "p2", "priority": 1, "statement": "Second"},
        ]
        with pytest.raises(ValidationError, match="priorities must be unique"):
            AgentIdentity.model_validate(data)

    def test_empty_principles_rejected(self):
        data = _minimal_identity()
        data["principles"] = []
        with pytest.raises(ValidationError):
            AgentIdentity.model_validate(data)

    def test_valid_principles(self):
        data = _minimal_identity()
        data["principles"] = [
            {"id": "p1", "priority": 1, "statement": "First"},
            {"id": "p2", "priority": 2, "statement": "Second"},
        ]
        identity = AgentIdentity.model_validate(data)
        assert len(identity.principles) == 2


class TestGuardrails:
    def test_empty_hard_guardrails_rejected(self):
        data = _minimal_identity()
        data["guardrails"]["hard"] = []
        with pytest.raises(ValidationError):
            AgentIdentity.model_validate(data)

    def test_invalid_enforcement(self):
        data = _minimal_identity()
        data["guardrails"]["hard"][0]["enforcement"] = "nonexistent"
        with pytest.raises(ValidationError):
            AgentIdentity.model_validate(data)

    def test_invalid_severity(self):
        data = _minimal_identity()
        data["guardrails"]["hard"][0]["severity"] = "nonexistent"
        with pytest.raises(ValidationError):
            AgentIdentity.model_validate(data)

    def test_valid_enforcement_values(self):
        for enforcement in ["output_filter", "runtime_sandbox", "prompt_instruction"]:
            data = _minimal_identity()
            data["guardrails"]["hard"][0]["enforcement"] = enforcement
            identity = AgentIdentity.model_validate(data)
            assert identity.guardrails.hard[0].enforcement.value == enforcement


class TestScope:
    def test_primary_required(self):
        with pytest.raises(ValidationError):
            Scope(primary=[])

    def test_valid_scope(self):
        scope = Scope(
            primary=["data analysis"],
            secondary=["python"],
            out_of_scope=["legal advice"],
        )
        assert len(scope.primary) == 1
