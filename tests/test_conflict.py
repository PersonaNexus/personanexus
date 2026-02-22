"""Tests for the conflict resolution engine."""

import pytest

from personanexus.conflict import ConflictResolver, MergeTrace, MergeTraceEntry
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
        resolver = ConflictResolver(ConflictResolution(list_fields=ListConflictStrategy.REPLACE))
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
                explicit_resolutions=[ExplicitResolution(field="tags", strategy="union")]
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


# ---------------------------------------------------------------------------
# MergeTrace unit tests
# ---------------------------------------------------------------------------


class TestMergeTraceEntry:
    def test_create_entry(self):
        entry = MergeTraceEntry(
            field_path="personality.traits.rigor",
            source="mixin:safety",
            strategy="highest",
            base_value=0.5,
            override_value=0.9,
            result_value=0.9,
        )
        assert entry.field_path == "personality.traits.rigor"
        assert entry.source == "mixin:safety"
        assert entry.strategy == "highest"
        assert entry.base_value == 0.5
        assert entry.override_value == 0.9
        assert entry.result_value == 0.9


class TestMergeTrace:
    def test_empty_trace(self):
        trace = MergeTrace()
        assert len(trace.entries) == 0
        assert trace.summary() == {}
        assert trace.get_source("any.field") is None

    def test_add_entries(self):
        trace = MergeTrace()
        trace.add("x", "archetype", "last_wins", 0.5, 0.8, 0.8)
        trace.add("y", "mixin:safety", "highest", 0.3, 0.7, 0.7)
        assert len(trace.entries) == 2

    def test_get_source(self):
        trace = MergeTrace()
        trace.add("x", "archetype", "last_wins", 0.5, 0.8, 0.8)
        trace.add("x", "mixin:safety", "highest", 0.8, 0.9, 0.9)
        # Last entry wins
        assert trace.get_source("x") == "mixin:safety"
        assert trace.get_source("nonexistent") is None

    def test_summary(self):
        trace = MergeTrace()
        trace.add("x", "archetype", "last_wins", 0.5, 0.8, 0.8)
        trace.add("y", "archetype", "last_wins", 0.3, 0.7, 0.7)
        trace.add("z", "mixin:safety", "highest", 0.2, 0.9, 0.9)
        result = trace.summary()
        assert "archetype" in result
        assert "mixin:safety" in result
        assert set(result["archetype"]) == {"x", "y"}
        assert result["mixin:safety"] == ["z"]

    def test_format_text_empty(self):
        trace = MergeTrace()
        assert trace.format_text() == "No merge operations recorded."

    def test_format_text_with_entries(self):
        trace = MergeTrace()
        trace.add("personality.traits.rigor", "archetype", "last_wins", 0.5, 0.9, 0.9)
        trace.add("metadata.name", "own", "last_wins", "Base", "Override", "Override")
        text = trace.format_text()
        assert "Merge Trace" in text
        assert "Fields by source:" in text
        assert "archetype" in text
        assert "own" in text
        assert "Detailed operations:" in text
        assert "personality.traits.rigor" in text
        assert "metadata.name" in text

    def test_format_text_truncates_long_values(self):
        trace = MergeTrace()
        long_value = "x" * 200
        trace.add("field", "src", "strategy", long_value, long_value, long_value)
        text = trace.format_text()
        assert "..." in text


class TestMergeWithTrace:
    """Test that merge() records trace entries when a MergeTrace is provided."""

    def test_numeric_merge_traced(self):
        resolver = ConflictResolver()
        trace = MergeTrace()
        resolver.merge({"x": 0.5}, {"x": 0.8}, trace=trace, source="test")
        assert len(trace.entries) == 1
        assert trace.entries[0].field_path == "x"
        assert trace.entries[0].source == "test"
        assert trace.entries[0].strategy == "last_wins"

    def test_new_field_traced(self):
        resolver = ConflictResolver()
        trace = MergeTrace()
        resolver.merge({}, {"x": 0.8}, trace=trace, source="mixin:a")
        assert len(trace.entries) == 1
        assert trace.entries[0].strategy == "new_field"
        assert trace.entries[0].base_value is None

    def test_string_last_wins_traced(self):
        resolver = ConflictResolver()
        trace = MergeTrace()
        resolver.merge({"name": "old"}, {"name": "new"}, trace=trace, source="own")
        assert len(trace.entries) == 1
        assert trace.entries[0].strategy == "last_wins"
        assert trace.entries[0].result_value == "new"

    def test_list_merge_traced(self):
        resolver = ConflictResolver()
        trace = MergeTrace()
        resolver.merge({"tags": ["a"]}, {"tags": ["b"]}, trace=trace, source="mixin:x")
        assert len(trace.entries) == 1
        assert trace.entries[0].strategy in ("append", "union_by_id", "unique_append")

    def test_deep_merge_traced(self):
        resolver = ConflictResolver()
        trace = MergeTrace()
        resolver.merge(
            {"cfg": {"a": 1, "b": 2}},
            {"cfg": {"b": 3, "c": 4}},
            trace=trace,
            source="override",
        )
        # Should have entries for the nested fields
        assert len(trace.entries) >= 1

    def test_highest_strategy_traced(self):
        resolver = ConflictResolver(
            ConflictResolution(numeric_traits=NumericConflictStrategy.HIGHEST)
        )
        trace = MergeTrace()
        resolver.merge({"x": 0.9}, {"x": 0.5}, trace=trace, source="test")
        assert trace.entries[0].strategy == "highest"
        assert trace.entries[0].result_value == 0.9

    def test_average_strategy_traced(self):
        resolver = ConflictResolver(
            ConflictResolution(numeric_traits=NumericConflictStrategy.AVERAGE)
        )
        trace = MergeTrace()
        resolver.merge({"x": 0.4}, {"x": 0.8}, trace=trace, source="test")
        assert trace.entries[0].strategy == "average"
        assert trace.entries[0].result_value == pytest.approx(0.6)

    def test_lowest_strategy_traced(self):
        resolver = ConflictResolver(
            ConflictResolution(numeric_traits=NumericConflictStrategy.LOWEST)
        )
        trace = MergeTrace()
        resolver.merge({"x": 0.9}, {"x": 0.5}, trace=trace, source="test")
        assert trace.entries[0].strategy == "lowest"
        assert trace.entries[0].result_value == 0.5

    def test_id_keyed_list_traced(self):
        resolver = ConflictResolver()
        trace = MergeTrace()
        base = {"items": [{"id": "a", "val": 1}]}
        override = {"items": [{"id": "b", "val": 2}]}
        resolver.merge(base, override, trace=trace, source="mixin:x")
        assert any(e.strategy == "union_by_id" for e in trace.entries)

    def test_explicit_resolution_traced(self):
        resolver = ConflictResolver(
            ConflictResolution(
                explicit_resolutions=[
                    ExplicitResolution(field="personality.traits.rigor", strategy="highest")
                ]
            )
        )
        trace = MergeTrace()
        base = {"personality": {"traits": {"rigor": 0.9}}}
        override = {"personality": {"traits": {"rigor": 0.7}}}
        resolver.merge(base, override, trace=trace, source="test")
        rigor_entries = [e for e in trace.entries if "rigor" in e.field_path]
        assert len(rigor_entries) >= 1
        assert any("explicit" in e.strategy for e in rigor_entries)

    def test_replace_list_traced(self):
        resolver = ConflictResolver(ConflictResolution(list_fields=ListConflictStrategy.REPLACE))
        trace = MergeTrace()
        resolver.merge({"items": ["a"]}, {"items": ["b"]}, trace=trace, source="s")
        assert any(e.strategy == "replace" for e in trace.entries)

    def test_unique_append_traced(self):
        resolver = ConflictResolver(
            ConflictResolution(list_fields=ListConflictStrategy.UNIQUE_APPEND)
        )
        trace = MergeTrace()
        resolver.merge({"items": ["a", "b"]}, {"items": ["b", "c"]}, trace=trace, source="s")
        assert any(e.strategy == "unique_append" for e in trace.entries)

    def test_object_replace_traced(self):
        resolver = ConflictResolver(
            ConflictResolution(object_fields=ObjectConflictStrategy.REPLACE)
        )
        trace = MergeTrace()
        resolver.merge({"cfg": {"a": 1}}, {"cfg": {"b": 2}}, trace=trace, source="s")
        assert any(e.strategy == "replace" for e in trace.entries)
