"""Tests for the PersonaNexus Studio view helpers."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from studio import _compile_safe, _load_identity_safe, _studio_agent_from_yaml  # noqa: E402
from studio_model import StudioAgent, agent_signature, load_studio_agents  # noqa: E402


def test_load_studio_agents_maps_yaml_to_gallery_cards() -> None:
    agents = load_studio_agents(Path(__file__).resolve().parents[1] / "agents")

    assert agents
    atlas = next(agent for agent in agents if agent.slug == "atlas")
    assert atlas.name == "Atlas"
    assert atlas.title == "Research Coordinator & Orchestrator"
    assert atlas.motifs
    assert set(atlas.traits) >= {"warmth", "rigor", "creativity"}
    assert all(0.0 <= score <= 1.0 for score in atlas.traits.values())


def test_agent_signature_uses_strongest_trait_label() -> None:
    agent = StudioAgent(
        slug="demo",
        name="Demo",
        title="Demo Agent",
        description="",
        tags=(),
        status="draft",
        traits={"warmth": 0.2, "rigor": 0.95, "creativity": 0.4},
        tone="precise",
        principles=(),
        motifs=("blueprint grid",),
    )

    assert agent_signature(agent) == "Demo · Rigor · precise"


AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"


def test_load_identity_safe_returns_identity_for_known_agent() -> None:
    identity, err = _load_identity_safe(AGENTS_DIR / "forge.yaml")

    assert err is None
    assert identity is not None
    assert identity.metadata.name == "Forge"


def test_load_identity_safe_returns_error_for_missing_file(tmp_path: Path) -> None:
    identity, err = _load_identity_safe(tmp_path / "nonexistent.yaml")

    assert identity is None
    assert err is not None


def test_compile_safe_text_format_returns_string() -> None:
    identity, _ = _load_identity_safe(AGENTS_DIR / "forge.yaml")
    result, err = _compile_safe(identity, "text")

    assert err is None
    assert result is not None
    assert "Forge" in result


def test_compile_safe_openclaw_format_returns_json_string() -> None:
    import json as _json

    identity, _ = _load_identity_safe(AGENTS_DIR / "forge.yaml")
    result, err = _compile_safe(identity, "openclaw")

    assert err is None
    parsed = _json.loads(result)
    assert "agent_name" in parsed


def test_studio_agent_from_yaml_minimal() -> None:
    minimal = textwrap.dedent("""
        schema_version: '1.0'
        metadata:
          id: agt_test_001
          name: Tester
        role:
          title: QA Agent
          purpose: Test things.
        personality:
          traits:
            warmth: 0.8
            rigor: 0.9
    """)
    data = yaml.safe_load(minimal)
    agent = _studio_agent_from_yaml(data, slug="tester")

    assert agent.name == "Tester"
    assert agent.title == "QA Agent"
    assert agent.slug == "tester"
    assert 0.0 <= agent.traits.get("warmth", -1) <= 1.0


def test_studio_agent_from_yaml_uses_slug_as_fallback_name() -> None:
    data = yaml.safe_load("schema_version: '1.0'\nmetadata: {}")
    agent = _studio_agent_from_yaml(data, slug="fallback-slug")

    assert agent.name == "Fallback-Slug"
