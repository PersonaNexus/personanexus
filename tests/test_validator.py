"""Tests for the identity validator."""

import pytest

from personanexus.validator import IdentityValidator


@pytest.fixture
def validator():
    return IdentityValidator()


def _minimal_data(**overrides):
    data = {
        "schema_version": "1.0",
        "metadata": {
            "id": "agt_test_001",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test agent",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "draft",
        },
        "role": {
            "title": "Tester",
            "purpose": "Test",
            "scope": {"primary": ["testing"]},
        },
        "personality": {"traits": {"warmth": 0.5, "rigor": 0.5}},
        "communication": {"tone": {"default": "neutral"}},
        "principles": [{"id": "p1", "priority": 1, "statement": "Be good"}],
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


class TestValidateDict:
    def test_valid_minimal(self, validator):
        result = validator.validate_dict(_minimal_data())
        assert result.valid is True
        assert result.identity is not None
        assert len(result.errors) == 0

    def test_missing_required_field(self, validator):
        data = _minimal_data()
        del data["metadata"]
        result = validator.validate_dict(data)
        assert result.valid is False
        assert any("metadata" in e for e in result.errors)

    def test_invalid_trait_range(self, validator):
        data = _minimal_data()
        data["personality"]["traits"]["warmth"] = 1.5
        result = validator.validate_dict(data)
        assert result.valid is False

    def test_invalid_enforcement(self, validator):
        data = _minimal_data()
        data["guardrails"]["hard"][0]["enforcement"] = "invalid"
        result = validator.validate_dict(data)
        assert result.valid is False


class TestTraitTensions:
    def test_no_tension(self, validator):
        data = _minimal_data()
        data["personality"]["traits"] = {"warmth": 0.5, "directness": 0.5}
        result = validator.validate_dict(data)
        assert result.valid is True
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        assert len(tension_warnings) == 0

    def test_warmth_directness_tension(self, validator):
        data = _minimal_data()
        data["personality"]["traits"] = {"warmth": 0.9, "directness": 0.1}
        result = validator.validate_dict(data)
        assert result.valid is True
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        assert len(tension_warnings) == 1
        assert "warmth" in tension_warnings[0].message
        assert "directness" in tension_warnings[0].message

    def test_rigor_creativity_tension(self, validator):
        data = _minimal_data()
        data["personality"]["traits"] = {"rigor": 0.95, "creativity": 0.1}
        result = validator.validate_dict(data)
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        assert len(tension_warnings) == 1
        assert "rigor" in tension_warnings[0].message

    def test_no_tension_when_traits_absent(self, validator):
        data = _minimal_data()
        data["personality"]["traits"] = {"warmth": 0.5, "rigor": 0.5}
        result = validator.validate_dict(data)
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        assert len(tension_warnings) == 0


class TestPrincipleOrderingWarning:
    def test_ordered_principles(self, validator):
        data = _minimal_data()
        data["principles"] = [
            {"id": "p1", "priority": 1, "statement": "First"},
            {"id": "p2", "priority": 2, "statement": "Second"},
        ]
        result = validator.validate_dict(data)
        ordering_warnings = [w for w in result.warnings if w.type == "ordering"]
        assert len(ordering_warnings) == 0

    def test_unordered_principles(self, validator):
        data = _minimal_data()
        data["principles"] = [
            {"id": "p2", "priority": 2, "statement": "Second"},
            {"id": "p1", "priority": 1, "statement": "First"},
        ]
        result = validator.validate_dict(data)
        ordering_warnings = [w for w in result.warnings if w.type == "ordering"]
        assert len(ordering_warnings) == 1


class TestValidateFile:
    def test_validate_ada(self, validator, mira_path):
        result = validator.validate_file(mira_path)
        assert result.valid is True
        assert result.identity is not None
        assert result.identity.metadata.name == "Mira"

    def test_validate_minimal(self, validator, minimal_path):
        result = validator.validate_file(minimal_path)
        assert result.valid is True

    def test_validate_nonexistent_file(self, validator):
        result = validator.validate_file("/nonexistent/file.yaml")
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_all_examples(self, validator, examples_dir):
        for path in examples_dir.rglob("*.yaml"):
            # Skip team definitions (different schema, not individual agents)
            if "teams" in path.parts:
                continue
            result = validator.validate_file(path)
            assert result.valid is True, f"{path.name} failed: {result.errors}"
