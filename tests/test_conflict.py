"""Tests for the conflict resolution engine."""

import pytest

from personanexus.conflict import ConflictResolver
from personanexus.types import (
    ConflictResolution,
    ExplicitResolution,
    ListConflictStrategy,
    NumericConflictStrategy,
    ObjectConflictStrategy,
)


@pytest.fixture
def default_resolver():
    return ConflictResolver()


class TestNumericResolution:
    def test_last_wins_default(self, default_resolver):
        result = default_resolver.merge({"x": 0.5}, {"x": 0.8})
        assert result["x"] == 0.8

    def test_highest(self):
        resolver = ConflictResolver(
            ConflictResolution(numeric_traits=NumericConflictStrategy.HIGHEST)
        )
        result = resolver.merge({"x": 0.9}, {"x": 0.5})
        assert result["x"] == 0.9

    def test_lowest(self):
        resolver = ConflictResolver(
            ConflictResolution(numeric_traits=NumericConflictStrategy.LOWEST)
        )
        result = resolver.merge({"x": 0.9}, {"x": 0.5})
        assert result["x"] == 0.5

    def test_average(self):
        resolver = ConflictResolver(
            ConflictResolution(numeric_traits=NumericConflictStrategy.AVERAGE)
        )
        result = resolver.merge({"x": 0.4}, {"x": 0.8})
        assert result["x"] == pytest.approx(0.6)


class TestListResolution:
    def test_append_default(self, default_resolver):
        result = default_resolver.merge({"items": ["a", "b"]}, {"items": ["c"]})
        assert result["items"] == ["a", "b", "c"]

    def test_replace(self):
        resolver = ConflictResolver(
            ConflictResolution(list_fields=ListConflictStrategy.REPLACE)
        )
        result = resolver.merge({"items": ["a", "b"]}, {"items": ["c"]})
        assert result["items"] == ["c"]

    def test_unique_append(self):
        resolver = ConflictResolver(
            ConflictResolution(list_fields=ListConflictStrategy.UNIQUE_APPEND)
        )
        result = resolver.merge({"items": ["a", "b"]}, {"items": ["b", "c"]})
        assert result["items"] == ["a", "b", "c"]

    def test_id_keyed_lists_deduplicate(self, default_resolver):
        base = {"items": [{"id": "a", "val": 1}, {"id": "b", "val": 2}]}
        override = {"items": [{"id": "b", "val": 99}, {"id": "c", "val": 3}]}
        result = default_resolver.merge(base, override)
        ids = [item["id"] for item in result["items"]]
        assert ids == ["a", "b", "c"]
        # Override version of 'b' should win
        b_item = next(i for i in result["items"] if i["id"] == "b")
        assert b_item["val"] == 99


class TestObjectResolution:
    def test_deep_merge_default(self, default_resolver):
        base = {"config": {"a": 1, "b": 2}}
        override = {"config": {"b": 3, "c": 4}}
        result = default_resolver.merge(base, override)
        assert result["config"] == {"a": 1, "b": 3, "c": 4}

    def test_replace(self):
        resolver = ConflictResolver(
            ConflictResolution(object_fields=ObjectConflictStrategy.REPLACE)
        )
        base = {"config": {"a": 1, "b": 2}}
        override = {"config": {"b": 3, "c": 4}}
        result = resolver.merge(base, override)
        assert result["config"] == {"b": 3, "c": 4}

    def test_nested_deep_merge(self, default_resolver):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 3, "e": 4}}}
        result = default_resolver.merge(base, override)
        assert result["a"]["b"] == {"c": 3, "d": 2, "e": 4}


class TestGuardrailsUnion:
    def test_hard_guardrails_always_union(self, default_resolver):
        base = {
            "guardrails": {
                "hard": [
                    {"id": "no_harm", "rule": "No harm"},
                    {"id": "no_pii", "rule": "No PII"},
                ]
            }
        }
        override = {
            "guardrails": {
                "hard": [
                    {"id": "no_harm", "rule": "Updated no harm"},
                    {"id": "confidential", "rule": "Keep secrets"},
                ]
            }
        }
        result = default_resolver.merge(base, override)
        hard = result["guardrails"]["hard"]
        ids = [g["id"] for g in hard]
        assert "no_harm" in ids
        assert "no_pii" in ids
        assert "confidential" in ids
        # Override version of no_harm should win
        no_harm = next(g for g in hard if g["id"] == "no_harm")
        assert no_harm["rule"] == "Updated no harm"


class TestExplicitResolution:
    def test_explicit_highest(self):
        resolver = ConflictResolver(
            ConflictResolution(
                explicit_resolutions=[
                    ExplicitResolution(field="personality.traits.rigor", strategy="highest")
                ]
            )
        )
        base = {"personality": {"traits": {"rigor": 0.9}}}
        override = {"personality": {"traits": {"rigor": 0.7}}}
        result = resolver.merge(base, override)
        assert result["personality"]["traits"]["rigor"] == 0.9

    def test_explicit_union(self):
        resolver = ConflictResolver(
            ConflictResolution(
                explicit_resolutions=[
                    ExplicitResolution(field="tags", strategy="union")
                ]
            )
        )
        base = {"tags": [{"id": "a"}, {"id": "b"}]}
        override = {"tags": [{"id": "b"}, {"id": "c"}]}
        result = resolver.merge(base, override)
        ids = [t["id"] for t in result["tags"]]
        assert ids == ["a", "b", "c"]


class TestNewKeysAdded:
    def test_new_key_from_override(self, default_resolver):
        result = default_resolver.merge({"a": 1}, {"a": 1, "b": 2})
        assert result["b"] == 2

    def test_base_keys_preserved(self, default_resolver):
        result = default_resolver.merge({"a": 1, "b": 2}, {"c": 3})
        assert result["a"] == 1
        assert result["b"] == 2
        assert result["c"] == 3
