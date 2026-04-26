"""Tests for the PersonaNexus Studio view helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))

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
