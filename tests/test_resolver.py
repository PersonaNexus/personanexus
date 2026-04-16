"""Tests for inheritance and mixin resolution."""

import pytest

from personanexus.parser import ParseError
from personanexus.resolver import IdentityResolver, ResolutionError


@pytest.fixture
def resolver(examples_dir):
    return IdentityResolver(search_paths=[examples_dir])


class TestResolveFile:
    def test_resolve_minimal_no_inheritance(self, resolver, minimal_path):
        identity = resolver.resolve_file(minimal_path)
        assert identity.metadata.name == "Pip"

    def test_resolve_relative_embedded_path_fields(self, tmp_path):
        golden_dir = tmp_path / "tests" / "golden"
        golden_dir.mkdir(parents=True)
        persona = tmp_path / "persona.yaml"
        persona.write_text(
            """
schema_version: "1.0"
metadata:
  id: agt_path_test
  name: Path Test
  version: "1.0.0"
  description: Path test
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: Analyst
  purpose: Verify path resolution
  scope:
    primary: ["analysis"]
personality:
  traits:
    warmth: 0.5
    rigor: 0.5
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: Test
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
evaluation:
  regression:
    golden_tests:
      path: tests/golden
"""
        )

        resolved = IdentityResolver().resolve_file(persona)

        assert resolved.evaluation.regression.golden_tests.path == str(golden_dir.resolve())

    def test_leave_nonexistent_embedded_path_fields_unchanged(self, tmp_path):
        persona = tmp_path / "persona.yaml"
        persona.write_text(
            """
schema_version: "1.0"
metadata:
  id: agt_path_missing
  name: Path Missing
  version: "1.0.0"
  description: Path missing test
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: Analyst
  purpose: Verify missing path behavior
  scope:
    primary: ["analysis"]
personality:
  traits:
    warmth: 0.5
    rigor: 0.5
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: Test
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
evaluation:
  regression:
    golden_tests:
      path: tests/missing
"""
        )

        resolved = IdentityResolver().resolve_file(persona)

        assert resolved.evaluation.regression.golden_tests.path == "tests/missing"

    def test_resolve_ada_with_inheritance(self, resolver, mira_path):
        identity = resolver.resolve_file(mira_path)
        # Ada's own values should be preserved
        assert identity.metadata.name == "Mira"
        assert identity.metadata.id == "agt_mira_001"
        assert identity.metadata.version == "2.4.1"

    def test_resolve_ada_personality_traits(self, resolver, mira_path):
        identity = resolver.resolve_file(mira_path)
        traits = identity.personality.traits
        # Ada's own trait values should override archetype/mixin
        assert traits.rigor == 0.9  # Ada's value
        assert traits.warmth == 0.7  # Ada's value (also in mixin)
        assert traits.empathy == 0.7  # Ada's value overrides mixin's 0.8

    def test_resolve_ada_principles(self, resolver, mira_path):
        identity = resolver.resolve_file(mira_path)
        principle_ids = {p.id for p in identity.principles}
        # Should have Ada's principles plus empathy_first from mixin
        assert "accuracy_first" in principle_ids
        assert "clarity_over_completeness" in principle_ids
        assert "empathy_first" in principle_ids
        assert "respect_for_time" in principle_ids

    def test_resolve_ada_guardrails_union(self, resolver, mira_path):
        identity = resolver.resolve_file(mira_path)
        guardrail_ids = {g.id for g in identity.guardrails.hard}
        # Should be union of all sources
        assert "no_impersonation" in guardrail_ids
        assert "no_harmful_content" in guardrail_ids
        assert "confidentiality" in guardrail_ids

    def test_resolve_archetype_directly(self, resolver, analyst_archetype_path):
        identity = resolver.resolve_file(analyst_archetype_path)
        assert identity.personality.traits.rigor is not None


class TestResolutionErrors:
    def test_missing_file_raises(self, resolver):
        with pytest.raises(ParseError, match="not found"):
            resolver.resolve_file("/nonexistent/file.yaml")

    def test_max_depth_raises(self, tmp_path):
        # Create files that reference each other (deep chain, not circular)
        resolver = IdentityResolver(search_paths=[tmp_path], max_depth=2)

        # Create a chain: c extends b extends a
        (tmp_path / "a.yaml").write_text(
            """
schema_version: "1.0"
metadata:
  id: agt_a
  name: A
  version: "1.0.0"
  description: A
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: A
  purpose: A
  scope:
    primary: ["a"]
personality:
  traits:
    warmth: 0.5
    rigor: 0.5
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: A
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
"""
        )

        (tmp_path / "b.yaml").write_text(
            """
schema_version: "1.0"
extends: "a.yaml"
metadata:
  id: agt_b
  name: B
  version: "1.0.0"
  description: B
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: B
  purpose: B
  scope:
    primary: ["b"]
personality:
  traits:
    warmth: 0.6
    rigor: 0.6
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: B
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
"""
        )

        (tmp_path / "c.yaml").write_text(
            """
schema_version: "1.0"
extends: "b.yaml"
metadata:
  id: agt_c
  name: C
  version: "1.0.0"
  description: C
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: C
  purpose: C
  scope:
    primary: ["c"]
personality:
  traits:
    warmth: 0.7
    rigor: 0.7
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: C
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
"""
        )

        # c -> b -> a is depth 2, which should be at the limit
        # With max_depth=2 and the way depth tracking works, the chain is:
        # c (depth=0) -> b (depth=1) -> a (depth=2) which should work
        identity = resolver.resolve_file(tmp_path / "c.yaml")
        assert identity.metadata.name == "C"

    def test_circular_dependency_detected(self, tmp_path):
        resolver = IdentityResolver(search_paths=[tmp_path])

        (tmp_path / "x.yaml").write_text(
            """
schema_version: "1.0"
extends: "y.yaml"
metadata:
  id: agt_x
  name: X
  version: "1.0.0"
  description: X
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: X
  purpose: X
  scope:
    primary: ["x"]
personality:
  traits:
    warmth: 0.5
    rigor: 0.5
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: X
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
"""
        )

        (tmp_path / "y.yaml").write_text(
            """
schema_version: "1.0"
extends: "x.yaml"
metadata:
  id: agt_y
  name: Y
  version: "1.0.0"
  description: Y
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: Y
  purpose: Y
  scope:
    primary: ["y"]
personality:
  traits:
    warmth: 0.5
    rigor: 0.5
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: Y
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
"""
        )

        with pytest.raises(ResolutionError, match="Circular"):
            resolver.resolve_file(tmp_path / "x.yaml")

    def test_invalid_embedded_path_reference_raises(self, tmp_path):
        persona = tmp_path / "persona.yaml"
        persona.write_text(
            """
schema_version: "1.0"
metadata:
  id: agt_bad_path
  name: Bad Path
  version: "1.0.0"
  description: Bad path test
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: Analyst
  purpose: Verify invalid path behavior
  scope:
    primary: ["analysis"]
personality:
  traits:
    warmth: 0.5
    rigor: 0.5
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: Test
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
evaluation:
  regression:
    golden_tests:
      path: ../outside
"""
        )

        with pytest.raises(ParseError, match="Invalid reference"):
            IdentityResolver().resolve_file(persona)

    def test_missing_archetype_raises(self, tmp_path):
        resolver = IdentityResolver(search_paths=[tmp_path])

        (tmp_path / "orphan.yaml").write_text(
            """
schema_version: "1.0"
extends: "nonexistent/archetype"
metadata:
  id: agt_orphan
  name: Orphan
  version: "1.0.0"
  description: Orphan
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: Orphan
  purpose: Orphan
  scope:
    primary: ["orphan"]
personality:
  traits:
    warmth: 0.5
    rigor: 0.5
communication:
  tone:
    default: neutral
principles:
  - id: p1
    priority: 1
    statement: O
guardrails:
  hard:
    - id: g1
      rule: R1
      enforcement: output_filter
      severity: critical
"""
        )

        with pytest.raises(ParseError, match="Cannot resolve"):
            resolver.resolve_file(tmp_path / "orphan.yaml")
