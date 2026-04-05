from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.evolution import (
    TOTAL_HARD_CAP,
    apply_deltas,
    configure_evolution,
    evolve_persona,
    evolution_state_path,
    export_evolved_persona,
    get_candidates,
    load_evolution_state,
    load_identity_with_evolution,
    promote_all,
    promote_candidate,
    reset_evolution,
    rollback_evolution,
)
from personanexus.resolver import IdentityResolver
from personanexus.types import EvolutionMode, LearningRate, ReviewMode

runner = CliRunner()


def _persona_copy(tmp_path: Path, minimal_path: Path) -> Path:
    target = tmp_path / "pip.yaml"
    target.write_text(minimal_path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


@pytest.fixture
def evolved_persona_path(tmp_path: Path, minimal_path: Path) -> Path:
    persona = _persona_copy(tmp_path, minimal_path)
    configure_evolution(
        persona,
        mode=EvolutionMode.BOTH,
        learning_rate=LearningRate.MEDIUM,
        consensus_threshold=2,
        review_mode=ReviewMode.PROMPT,
    )
    return persona


def test_enable_adds_yaml_schema_fields(tmp_path: Path, minimal_path: Path):
    persona = _persona_copy(tmp_path, minimal_path)
    configure_evolution(
        persona,
        mode=EvolutionMode.SOFT,
        learning_rate=LearningRate.LOW,
        consensus_threshold=4,
        review_mode=ReviewMode.AUTO,
    )
    text = persona.read_text(encoding="utf-8")
    assert "evolution:" in text
    assert "enabled: true" in text
    assert "mode: soft" in text
    assert "learning_rate: low" in text
    assert "review_mode: auto" in text


def test_initial_state_is_created(evolved_persona_path: Path):
    state = load_evolution_state(evolved_persona_path)
    assert state is not None
    assert state.persona == "pip"
    assert state.version == 1
    assert evolution_state_path(evolved_persona_path).exists()


def test_soft_feedback_creates_pending_candidate(evolved_persona_path: Path):
    candidate = evolve_persona(evolved_persona_path, feedback="be more concise please")
    assert candidate.type == "soft"
    assert candidate.guidance is not None
    assert len(get_candidates(evolved_persona_path)) == 1


def test_hard_feedback_caps_change_to_learning_rate(evolved_persona_path: Path):
    candidate = evolve_persona(
        evolved_persona_path,
        feedback="be more empathetic",
        candidate_type="hard",
        trait="agreeableness",
        change=0.9,
    )
    assert candidate.change == pytest.approx(0.15)


def test_hard_feedback_rejects_protected_trait(tmp_path: Path, minimal_path: Path):
    persona = _persona_copy(tmp_path, minimal_path)
    configure_evolution(persona, mode=EvolutionMode.BOTH)
    data = json.loads(evolution_state_path(persona).read_text())
    yaml_text = persona.read_text(encoding="utf-8")
    yaml_text += "\nevolution:\n  enabled: true\n  mode: both\n  learning_rate: medium\n  consensus_threshold: 2\n  protected_traits:\n    - agreeableness\n"
    persona.write_text(yaml_text, encoding="utf-8")
    with pytest.raises(ValueError):
        evolve_persona(
            persona,
            feedback="be warmer",
            candidate_type="hard",
            trait="agreeableness",
            change=0.1,
        )
    assert json.loads(evolution_state_path(persona).read_text())["rejected_candidates"]
    assert data["persona"] == "pip"


def test_pending_support_counts_accumulate(evolved_persona_path: Path):
    first = evolve_persona(
        evolved_persona_path,
        feedback="be more empathetic",
        candidate_type="hard",
        trait="agreeableness",
        change=0.1,
    )
    second = evolve_persona(
        evolved_persona_path,
        feedback="be more empathetic again",
        candidate_type="hard",
        trait="agreeableness",
        change=0.1,
    )
    assert first.signals_supporting == 1
    assert second.signals_supporting == 2


def test_promote_soft_candidate_applies_guidance(evolved_persona_path: Path):
    candidate = evolve_persona(evolved_persona_path, feedback="be less wordy")
    promote_candidate(evolved_persona_path, candidate.id, accept=True)
    state = load_evolution_state(evolved_persona_path)
    assert state is not None
    assert "concise" in state.soft_deltas["tone_guidance"].lower()


def test_promote_hard_candidate_requires_consensus(evolved_persona_path: Path):
    candidate = evolve_persona(
        evolved_persona_path,
        feedback="be more empathetic",
        candidate_type="hard",
        trait="agreeableness",
        change=0.1,
    )
    with pytest.raises(ValueError):
        promote_candidate(evolved_persona_path, candidate.id, accept=True)


def test_promote_hard_candidate_with_consensus_updates_state(evolved_persona_path: Path):
    c1 = evolve_persona(
        evolved_persona_path,
        feedback="be more empathetic",
        candidate_type="hard",
        trait="agreeableness",
        change=0.1,
    )
    c2 = evolve_persona(
        evolved_persona_path,
        feedback="be warmer",
        candidate_type="hard",
        trait="agreeableness",
        change=0.1,
    )
    promote_candidate(evolved_persona_path, c2.id, accept=True)
    state = load_evolution_state(evolved_persona_path)
    assert state is not None
    assert state.hard_deltas["agreeableness"].delta == pytest.approx(0.10)
    assert any(adj.id == c2.id for adj in state.adjustments)
    assert c1.id != c2.id


def test_total_hard_cap_blocks_overevolution(evolved_persona_path: Path):
    # build enough consensus for three hard accepts
    for _ in range(2):
        evolve_persona(
            evolved_persona_path,
            feedback="more empathy",
            candidate_type="hard",
            trait="agreeableness",
            change=0.15,
        )
    accepted, errors = promote_all(evolved_persona_path)
    assert len(accepted) == 1
    assert not errors

    for _ in range(2):
        evolve_persona(
            evolved_persona_path,
            feedback="even warmer",
            candidate_type="hard",
            trait="agreeableness",
            change=0.15,
        )
    accepted, errors = promote_all(evolved_persona_path)
    assert len(accepted) == 1
    assert not errors

    for _ in range(2):
        evolve_persona(
            evolved_persona_path,
            feedback="push further",
            candidate_type="hard",
            trait="agreeableness",
            change=0.15,
        )
    accepted, errors = promote_all(evolved_persona_path)
    assert accepted == []
    assert any("±0.30" in err for err in errors)
    state = load_evolution_state(evolved_persona_path)
    assert state is not None
    assert state.hard_deltas["agreeableness"].delta == pytest.approx(TOTAL_HARD_CAP)


def test_apply_deltas_updates_custom_traits(evolved_persona_path: Path):
    candidate = evolve_persona(
        evolved_persona_path,
        feedback="be warmer",
        candidate_type="hard",
        trait="warmth",
        change=0.1,
    )
    state = load_evolution_state(evolved_persona_path)
    assert state is not None
    # cheat consensus for direct unit test
    state.pending_candidates[-1].signals_supporting = 2
    state.pending_candidates[-1].change = 0.1
    state.pending_candidates[-1].trait = "warmth"
    state.pending_candidates[-1].type = "hard"
    state.pending_candidates[-1].id = candidate.id
    state.pending_candidates[-1].status = "pending"
    state.pending_candidates[-1].reason = "manual"
    state.pending_candidates[-1].source = "manual"
    state.pending_candidates[-1].guidance = None
    from personanexus.evolution import save_evolution_state

    save_evolution_state(evolved_persona_path, state)
    promote_candidate(evolved_persona_path, candidate.id, accept=True)
    identity = load_identity_with_evolution(evolved_persona_path)
    assert identity.personality.traits.warmth == pytest.approx(0.7)


def test_apply_deltas_updates_ocean_profile(tmp_path: Path):
    persona = tmp_path / "ocean.yaml"
    persona.write_text(
        '''schema_version: "1.0"
metadata:
  id: "agt_ocean_001"
  name: "Ocean"
  version: "1.0.0"
  description: "Ocean test"
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: "active"
role:
  title: "General Assistant"
  purpose: "Help users"
  scope:
    primary: ["general"]
personality:
  profile:
    mode: "ocean"
    ocean:
      openness: 0.4
      conscientiousness: 0.5
      extraversion: 0.5
      agreeableness: 0.5
      neuroticism: 0.2
communication:
  tone:
    default: "friendly"
principles:
  - id: "helpful"
    priority: 1
    statement: "Be helpful"
guardrails:
  hard:
    - id: "safe"
      rule: "Stay safe"
      enforcement: "output_filter"
      severity: "critical"
''',
        encoding="utf-8",
    )
    configure_evolution(persona, mode=EvolutionMode.BOTH, consensus_threshold=1)
    candidate = evolve_persona(
        persona,
        feedback="be more open",
        candidate_type="hard",
        trait="openness",
        change=0.1,
    )
    promote_candidate(persona, candidate.id, accept=True)
    identity = load_identity_with_evolution(persona)
    assert identity.personality.profile.ocean is not None
    assert identity.personality.profile.ocean.openness == pytest.approx(0.5)


def test_export_writes_evolved_yaml(evolved_persona_path: Path, tmp_path: Path):
    candidate = evolve_persona(evolved_persona_path, feedback="be less wordy")
    promote_candidate(evolved_persona_path, candidate.id, accept=True)
    output = tmp_path / "pip-evolved.yaml"
    export_evolved_persona(evolved_persona_path, output)
    text = output.read_text(encoding="utf-8")
    assert "Evolution guidance:" in text


def test_reset_clears_active_deltas(evolved_persona_path: Path):
    candidate = evolve_persona(evolved_persona_path, feedback="be less wordy")
    promote_candidate(evolved_persona_path, candidate.id, accept=True)
    state = reset_evolution(evolved_persona_path)
    assert state.soft_deltas == {}
    assert state.hard_deltas == {}
    assert state.pending_candidates == []


def test_rollback_restores_previous_snapshot(evolved_persona_path: Path):
    candidate = evolve_persona(evolved_persona_path, feedback="be less wordy")
    promote_candidate(evolved_persona_path, candidate.id, accept=True)
    state_before = load_evolution_state(evolved_persona_path)
    assert state_before is not None
    reset_evolution(evolved_persona_path)
    rolled = rollback_evolution(evolved_persona_path, version=state_before.version)
    assert rolled.soft_deltas == state_before.soft_deltas


def test_compile_with_apply_evolution_flag(evolved_persona_path: Path, tmp_path: Path):
    candidate = evolve_persona(evolved_persona_path, feedback="be less wordy")
    promote_candidate(evolved_persona_path, candidate.id, accept=True)
    output = tmp_path / "compiled.md"
    result = runner.invoke(
        app,
        ["compile", str(evolved_persona_path), "--apply-evolution", "--output", str(output)],
    )
    assert result.exit_code == 0
    assert "Evolution guidance:" in output.read_text(encoding="utf-8")


def test_cli_pending_and_export_commands(evolved_persona_path: Path, tmp_path: Path):
    evolve_persona(evolved_persona_path, feedback="be less wordy")
    pending = runner.invoke(app, ["evolve", "pending", str(evolved_persona_path)])
    assert pending.exit_code == 0
    assert "Pending Evolution Candidates" in pending.output

    runner.invoke(app, ["evolve", "promote", str(evolved_persona_path), "--accept-all"])
    export_path = tmp_path / "out.yaml"
    exported = runner.invoke(
        app,
        ["evolve", "export", str(evolved_persona_path), "--output", str(export_path)],
    )
    assert exported.exit_code == 0
    assert export_path.exists()


def test_cli_enable_command(tmp_path: Path, minimal_path: Path):
    persona = _persona_copy(tmp_path, minimal_path)
    result = runner.invoke(app, ["evolve", "enable", str(persona), "--mode", "both"])
    assert result.exit_code == 0
    assert "Evolution enabled" in result.output


def test_load_identity_with_evolution_noop_without_state(minimal_path: Path):
    identity = IdentityResolver().resolve_file(minimal_path)
    evolved = apply_deltas(identity, None)
    assert evolved.metadata.name == identity.metadata.name
