"""Extended validation tests for untested code paths in team_types.py and validator.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from personanexus.team_types import (
    CollaborationProtocols,
    ConflictResolution,
    ConflictStrategy,
    DecisionFramework,
    QualityGate,
    TeamAgent,
    TeamComposition,
    TeamConfiguration,
    TeamGovernance,
    TeamMetadata,
    TeamSpec,
    WorkflowPattern,
    WorkflowStage,
)
from personanexus.types import AgentIdentity
from personanexus.validator import IdentityValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=UTC)


def _make_agent(agent_id: str, *, authority_level: int = 3) -> TeamAgent:
    """Build a minimal TeamAgent."""
    return TeamAgent(
        agent_id=agent_id,
        role="worker",
        authority_level=authority_level,
        expertise_domains=["general"],
    )


def _make_metadata(team_id: str = "team_test_001") -> TeamMetadata:
    """Build a minimal TeamMetadata."""
    return TeamMetadata(
        id=team_id,
        name="Test Team",
        created_at=_NOW,
    )


def _make_team_spec(
    agents: dict[str, TeamAgent],
    *,
    workflow_patterns: dict[str, WorkflowPattern] | None = None,
    governance: TeamGovernance | None = None,
    collaboration_protocols: CollaborationProtocols | None = None,
) -> TeamSpec:
    """Build a TeamSpec with the given agents and optional extras."""
    kwargs: dict = {
        "metadata": _make_metadata(),
        "composition": TeamComposition(agents=agents),
    }
    if workflow_patterns is not None:
        kwargs["workflow_patterns"] = workflow_patterns
    if governance is not None:
        kwargs["governance"] = governance
    if collaboration_protocols is not None:
        kwargs["collaboration_protocols"] = collaboration_protocols
    return TeamSpec(**kwargs)


def _minimal_identity_data(**overrides) -> dict:
    """Build a minimal valid AgentIdentity dict with optional overrides."""
    data: dict = {
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


# ===================================================================
# team_types.py tests
# ===================================================================


class TestValidateAgentComposition:
    """Tests for TeamComposition.validate_agent_composition — authority level spread."""

    def test_valid_authority_spread(self):
        """Authority spread of exactly 3 is acceptable."""
        agents = {
            "agt_lead": _make_agent("agt_lead", authority_level=5),
            "agt_mid": _make_agent("agt_mid", authority_level=3),
            "agt_junior": _make_agent("agt_junior", authority_level=2),
        }
        comp = TeamComposition(agents=agents)
        assert len(comp.agents) == 3

    def test_authority_spread_exceeds_three(self):
        """Authority spread > 3 should raise a ValidationError."""
        agents = {
            "agt_top": _make_agent("agt_top", authority_level=5),
            "agt_bottom": _make_agent("agt_bottom", authority_level=1),
        }
        with pytest.raises(ValidationError, match="Authority level spread"):
            TeamComposition(agents=agents)

    def test_authority_spread_exactly_four(self):
        """Spread of exactly 4 is > 3 and should fail."""
        agents = {
            "agt_top": _make_agent("agt_top", authority_level=5),
            "agt_bottom": _make_agent("agt_bottom", authority_level=1),
        }
        with pytest.raises(ValidationError, match="Authority level spread"):
            TeamComposition(agents=agents)

    def test_single_agent_no_spread(self):
        """A single agent has spread 0, should be valid."""
        agents = {"agt_solo": _make_agent("agt_solo", authority_level=3)}
        comp = TeamComposition(agents=agents)
        assert len(comp.agents) == 1

    def test_all_same_level(self):
        """All agents at the same level means spread 0 — valid."""
        agents = {
            f"agt_peer_{i}": _make_agent(f"agt_peer_{i}", authority_level=3) for i in range(5)
        }
        comp = TeamComposition(agents=agents)
        assert len(comp.agents) == 5


class TestValidateStageFlow:
    """Tests for WorkflowPattern.validate_stage_flow — duplicate stage names."""

    def test_unique_stage_names(self):
        """All unique stage names should be accepted."""
        pattern = WorkflowPattern(
            description="Test workflow",
            stages=[
                WorkflowStage(stage="plan", primary_agent="lead", objective="Plan"),
                WorkflowStage(stage="execute", primary_agent="worker", objective="Execute"),
            ],
        )
        assert len(pattern.stages) == 2

    def test_duplicate_stage_names_rejected(self):
        """Duplicate stage names should raise a ValidationError."""
        with pytest.raises(ValidationError, match="stage names must be unique"):
            WorkflowPattern(
                description="Test workflow",
                stages=[
                    WorkflowStage(stage="plan", primary_agent="lead", objective="Plan"),
                    WorkflowStage(stage="plan", primary_agent="worker", objective="Also plan"),
                ],
            )

    def test_single_stage(self):
        """A single stage is always valid (no duplicates possible)."""
        pattern = WorkflowPattern(
            description="Single stage",
            stages=[
                WorkflowStage(stage="only", primary_agent="lead", objective="Do it"),
            ],
        )
        assert len(pattern.stages) == 1


class TestValidateAgentReferences:
    """Tests for TeamSpec.validate_agent_references — governance & collaboration refs."""

    def test_valid_governance_references(self):
        """Valid governance decision framework references should pass."""
        agents = {
            "agt_lead": _make_agent("agt_lead"),
            "agt_reviewer": _make_agent("agt_reviewer"),
        }
        governance = TeamGovernance(
            decision_frameworks={
                "technical": DecisionFramework(
                    authority="agt_lead",
                    consultation_required=["agt_reviewer"],
                ),
            },
        )
        spec = _make_team_spec(agents, governance=governance)
        assert spec.governance.decision_frameworks["technical"].authority == "agt_lead"

    def test_unknown_authority_agent(self):
        """An authority agent not in composition should raise ValueError."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        governance = TeamGovernance(
            decision_frameworks={
                "technical": DecisionFramework(authority="agt_unknown"),
            },
        )
        with pytest.raises(ValidationError, match="unknown authority agent"):
            _make_team_spec(agents, governance=governance)

    def test_unknown_consultation_agent(self):
        """A consultation agent not in composition should raise ValueError."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        governance = TeamGovernance(
            decision_frameworks={
                "technical": DecisionFramework(
                    authority="agt_lead",
                    consultation_required=["agt_ghost"],
                ),
            },
        )
        with pytest.raises(ValidationError, match="unknown consultation agent"):
            _make_team_spec(agents, governance=governance)

    def test_unknown_veto_agent(self):
        """A veto agent not in composition should raise ValueError."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        governance = TeamGovernance(
            decision_frameworks={
                "technical": DecisionFramework(
                    authority="agt_lead",
                    veto_rights=["agt_phantom"],
                ),
            },
        )
        with pytest.raises(ValidationError, match="unknown veto agent"):
            _make_team_spec(agents, governance=governance)

    def test_unknown_quality_gate_enforcer(self):
        """A quality gate enforced_by agent not in composition should raise."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        collaboration = CollaborationProtocols(
            quality_gates=[
                QualityGate(
                    gate="code_review",
                    enforced_by="agt_missing",
                    criteria=["passes tests"],
                ),
            ],
        )
        with pytest.raises(ValidationError, match="unknown enforcer agent"):
            _make_team_spec(agents, collaboration_protocols=collaboration)

    def test_unknown_fallback_authority(self):
        """A conflict resolution fallback_authority not in composition should raise."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        governance = TeamGovernance(
            conflict_resolution={
                "priority": ConflictResolution(
                    strategy=ConflictStrategy.AUTHORITY_HIERARCHY,
                    fallback_authority="agt_nonexistent",
                ),
            },
        )
        with pytest.raises(ValidationError, match="unknown fallback authority"):
            _make_team_spec(agents, governance=governance)

    def test_valid_quality_gate_and_conflict(self):
        """Valid quality gate enforcer and conflict fallback should pass."""
        agents = {
            "agt_lead": _make_agent("agt_lead"),
            "agt_reviewer": _make_agent("agt_reviewer"),
        }
        governance = TeamGovernance(
            conflict_resolution={
                "priority": ConflictResolution(
                    strategy=ConflictStrategy.AUTHORITY_HIERARCHY,
                    fallback_authority="agt_lead",
                ),
            },
        )
        collaboration = CollaborationProtocols(
            quality_gates=[
                QualityGate(
                    gate="code_review",
                    enforced_by="agt_reviewer",
                    criteria=["passes tests"],
                ),
            ],
        )
        spec = _make_team_spec(agents, governance=governance, collaboration_protocols=collaboration)
        assert spec.collaboration_protocols.quality_gates[0].enforced_by == "agt_reviewer"

    def test_multiple_errors_reported(self):
        """Multiple invalid references should all be listed in the error."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        governance = TeamGovernance(
            decision_frameworks={
                "technical": DecisionFramework(
                    authority="agt_ghost1",
                    consultation_required=["agt_ghost2"],
                ),
            },
        )
        with pytest.raises(ValidationError, match="agt_ghost1"):
            _make_team_spec(agents, governance=governance)


class TestValidateWorkflowAgents:
    """Tests for TeamSpec.validate_workflow_agents — workflows referencing unknown agents."""

    def test_valid_workflow_agents(self):
        """Workflows referencing existing agents should pass."""
        agents = {
            "agt_lead": _make_agent("agt_lead"),
            "agt_worker": _make_agent("agt_worker"),
        }
        workflows = {
            "standard": WorkflowPattern(
                description="Standard",
                stages=[
                    WorkflowStage(stage="plan", primary_agent="agt_lead", objective="Plan"),
                    WorkflowStage(stage="execute", primary_agent="agt_worker", objective="Build"),
                ],
            ),
        }
        spec = _make_team_spec(agents, workflow_patterns=workflows)
        assert "standard" in spec.workflow_patterns

    def test_workflow_references_unknown_agent(self):
        """A workflow stage referencing an unknown agent should raise."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        workflows = {
            "standard": WorkflowPattern(
                description="Standard",
                stages=[
                    WorkflowStage(
                        stage="execute",
                        primary_agent="agt_missing",
                        objective="Build",
                    ),
                ],
            ),
        }
        with pytest.raises(ValidationError, match="unknown agent 'agt_missing'"):
            _make_team_spec(agents, workflow_patterns=workflows)

    def test_workflow_error_includes_workflow_and_stage_names(self):
        """The error message should identify the workflow and stage names."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        workflows = {
            "deploy_flow": WorkflowPattern(
                description="Deploy",
                stages=[
                    WorkflowStage(
                        stage="deploy_step",
                        primary_agent="agt_deployer",
                        objective="Deploy",
                    ),
                ],
            ),
        }
        with pytest.raises(ValidationError, match="Workflow 'deploy_flow' stage 'deploy_step'"):
            _make_team_spec(agents, workflow_patterns=workflows)


class TestValidateTeamSize:
    """Tests for TeamSpec.validate_team_size — max 20 agents."""

    def test_twenty_agents_allowed(self):
        """Exactly 20 agents should be allowed."""
        agents = {f"agt_agent{i:02d}": _make_agent(f"agt_agent{i:02d}") for i in range(20)}
        spec = _make_team_spec(agents)
        assert len(spec.composition.agents) == 20

    def test_twentyone_agents_rejected(self):
        """More than 20 agents should raise a ValidationError."""
        agents = {f"agt_agent{i:02d}": _make_agent(f"agt_agent{i:02d}") for i in range(21)}
        with pytest.raises(ValidationError, match="should not exceed 20"):
            _make_team_spec(agents)

    def test_one_agent_allowed(self):
        """A team with just 1 agent is valid."""
        agents = {"agt_solo": _make_agent("agt_solo")}
        spec = _make_team_spec(agents)
        assert len(spec.composition.agents) == 1


class TestTeamConfigurationTopLevel:
    """Tests for the top-level TeamConfiguration model."""

    def test_valid_team_configuration(self):
        """Constructing a valid TeamConfiguration should succeed."""
        agents = {"agt_lead": _make_agent("agt_lead")}
        spec = _make_team_spec(agents)
        config = TeamConfiguration(team=spec)
        assert config.schema_version == "2.0"


# ===================================================================
# validator.py tests
# ===================================================================


@pytest.fixture
def validator():
    return IdentityValidator()


class TestOceanNeuroticism:
    """OCEAN neuroticism > 0.6 should produce a warning."""

    def test_high_neuroticism_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "ocean",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.8,
                },
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        pp_warnings = [w for w in result.warnings if w.type == "personality_profile"]
        neuroticism_warnings = [w for w in pp_warnings if "neuroticism" in w.message]
        assert len(neuroticism_warnings) == 1
        assert "0.8" in neuroticism_warnings[0].message
        assert neuroticism_warnings[0].severity == "medium"

    def test_low_neuroticism_no_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "ocean",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.3,
                },
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        neuroticism_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "neuroticism" in w.message
        ]
        assert len(neuroticism_warnings) == 0

    def test_neuroticism_exactly_0_6_no_warning(self, validator):
        """Exactly 0.6 is not > 0.6, so no warning should be emitted."""
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "ocean",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.6,
                },
            },
        }
        result = validator.validate_dict(data)
        neuroticism_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "neuroticism" in w.message
        ]
        assert len(neuroticism_warnings) == 0

    def test_hybrid_mode_neuroticism_warning(self, validator):
        """Hybrid mode with OCEAN should also trigger the neuroticism warning."""
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "hybrid",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.9,
                },
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        neuroticism_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "neuroticism" in w.message
        ]
        assert len(neuroticism_warnings) == 1


class TestOceanConscientiousnessAgreeableness:
    """OCEAN conscientiousness + agreeableness < 0.8 should produce a warning."""

    def test_low_combined_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "ocean",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.2,
                    "extraversion": 0.5,
                    "agreeableness": 0.2,
                    "neuroticism": 0.3,
                },
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        combined_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "conscientiousness + agreeableness" in w.message
        ]
        assert len(combined_warnings) == 1
        assert "0.40" in combined_warnings[0].message
        assert combined_warnings[0].severity == "low"

    def test_high_combined_no_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "ocean",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.3,
                },
            },
        }
        result = validator.validate_dict(data)
        combined_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "conscientiousness + agreeableness" in w.message
        ]
        assert len(combined_warnings) == 0

    def test_exactly_0_8_no_warning(self, validator):
        """Exactly 0.8 combined is not < 0.8, so no warning."""
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "ocean",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.4,
                    "extraversion": 0.5,
                    "agreeableness": 0.4,
                    "neuroticism": 0.3,
                },
            },
        }
        result = validator.validate_dict(data)
        combined_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "conscientiousness + agreeableness" in w.message
        ]
        assert len(combined_warnings) == 0

    def test_hybrid_mode_combined_warning(self, validator):
        """Hybrid mode with OCEAN should also trigger the combined warning."""
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "hybrid",
                "ocean": {
                    "openness": 0.5,
                    "conscientiousness": 0.1,
                    "extraversion": 0.5,
                    "agreeableness": 0.1,
                    "neuroticism": 0.3,
                },
            },
        }
        result = validator.validate_dict(data)
        combined_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "conscientiousness + agreeableness" in w.message
        ]
        assert len(combined_warnings) == 1


class TestDiscPresetValidation:
    """Unknown DISC preset should produce a warning."""

    def test_unknown_disc_preset_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "disc",
                "disc_preset": "totally_made_up",
                "disc": {
                    "dominance": 0.5,
                    "influence": 0.5,
                    "steadiness": 0.5,
                    "conscientiousness": 0.5,
                },
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        disc_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "DISC preset" in w.message
        ]
        assert len(disc_warnings) == 1
        assert "totally_made_up" in disc_warnings[0].message
        assert disc_warnings[0].severity == "high"
        assert disc_warnings[0].path == "personality.profile.disc_preset"

    def test_known_disc_preset_no_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "disc",
                "disc_preset": "the_commander",
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        disc_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "DISC preset" in w.message
        ]
        assert len(disc_warnings) == 0

    def test_no_disc_preset_no_warning(self, validator):
        """When disc_preset is None, no DISC preset warning should appear."""
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "disc",
                "disc": {
                    "dominance": 0.5,
                    "influence": 0.5,
                    "steadiness": 0.5,
                    "conscientiousness": 0.5,
                },
            },
        }
        result = validator.validate_dict(data)
        disc_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "DISC preset" in w.message
        ]
        assert len(disc_warnings) == 0


class TestJungianPresetValidation:
    """Unknown Jungian preset should produce a warning."""

    def test_unknown_jungian_preset_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "jungian",
                "jungian_preset": "zzzz",
                "jungian": {"ei": 0.5, "sn": 0.5, "tf": 0.5, "jp": 0.5},
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        jungian_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "Jungian preset" in w.message
        ]
        assert len(jungian_warnings) == 1
        assert "zzzz" in jungian_warnings[0].message
        assert jungian_warnings[0].severity == "high"
        assert jungian_warnings[0].path == "personality.profile.jungian_preset"

    def test_known_jungian_preset_no_warning(self, validator):
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "jungian",
                "jungian_preset": "intj",
            },
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        jungian_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "Jungian preset" in w.message
        ]
        assert len(jungian_warnings) == 0

    def test_no_jungian_preset_no_warning(self, validator):
        """When jungian_preset is None, no Jungian preset warning should appear."""
        data = _minimal_identity_data()
        data["personality"] = {
            "traits": {"warmth": 0.5, "rigor": 0.5},
            "profile": {
                "mode": "jungian",
                "jungian": {"ei": 0.5, "sn": 0.5, "tf": 0.5, "jp": 0.5},
            },
        }
        result = validator.validate_dict(data)
        jungian_warnings = [
            w
            for w in result.warnings
            if w.type == "personality_profile" and "Jungian preset" in w.message
        ]
        assert len(jungian_warnings) == 0


class TestScopeOverlapWarnings:
    """Tests for primary/secondary/out_of_scope overlap warnings."""

    def test_primary_and_out_of_scope_overlap(self, validator):
        data = _minimal_identity_data()
        data["role"]["scope"] = {
            "primary": ["testing", "coding"],
            "out_of_scope": ["testing"],
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        overlap_warnings = [
            w
            for w in result.warnings
            if w.type == "scope_overlap" and "primary" in w.message and "out_of_scope" in w.message
        ]
        assert len(overlap_warnings) == 1
        assert overlap_warnings[0].severity == "high"
        assert "testing" in overlap_warnings[0].message

    def test_secondary_and_out_of_scope_overlap(self, validator):
        data = _minimal_identity_data()
        data["role"]["scope"] = {
            "primary": ["coding"],
            "secondary": ["testing", "docs"],
            "out_of_scope": ["docs"],
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        overlap_warnings = [
            w
            for w in result.warnings
            if w.type == "scope_overlap"
            and "secondary" in w.message
            and "out_of_scope" in w.message
        ]
        assert len(overlap_warnings) == 1
        assert overlap_warnings[0].severity == "high"
        assert "docs" in overlap_warnings[0].message

    def test_primary_and_secondary_overlap(self, validator):
        data = _minimal_identity_data()
        data["role"]["scope"] = {
            "primary": ["testing"],
            "secondary": ["testing"],
        }
        result = validator.validate_dict(data)
        assert result.valid is True
        overlap_warnings = [
            w
            for w in result.warnings
            if w.type == "scope_overlap" and "primary" in w.message and "secondary" in w.message
        ]
        assert len(overlap_warnings) == 1
        assert overlap_warnings[0].severity == "low"

    def test_no_overlap_no_warning(self, validator):
        data = _minimal_identity_data()
        data["role"]["scope"] = {
            "primary": ["coding"],
            "secondary": ["testing"],
            "out_of_scope": ["legal"],
        }
        result = validator.validate_dict(data)
        overlap_warnings = [w for w in result.warnings if w.type == "scope_overlap"]
        assert len(overlap_warnings) == 0

    def test_all_three_overlaps_at_once(self, validator):
        """When the same item is in all three scopes, multiple warnings fire."""
        data = _minimal_identity_data()
        data["role"]["scope"] = {
            "primary": ["everything"],
            "secondary": ["everything"],
            "out_of_scope": ["everything"],
        }
        result = validator.validate_dict(data)
        overlap_warnings = [w for w in result.warnings if w.type == "scope_overlap"]
        # primary & secondary, primary & out_of_scope, secondary & out_of_scope
        assert len(overlap_warnings) == 3


class TestPrincipleOrderingWarning:
    """Tests for principle ordering warning (not just the existing tests)."""

    def test_three_principles_wrong_order(self, validator):
        data = _minimal_identity_data()
        data["principles"] = [
            {"id": "p3", "priority": 3, "statement": "Third"},
            {"id": "p1", "priority": 1, "statement": "First"},
            {"id": "p2", "priority": 2, "statement": "Second"},
        ]
        result = validator.validate_dict(data)
        assert result.valid is True
        ordering_warnings = [w for w in result.warnings if w.type == "ordering"]
        assert len(ordering_warnings) == 1
        assert ordering_warnings[0].severity == "low"
        assert ordering_warnings[0].path == "principles"

    def test_single_principle_always_ordered(self, validator):
        data = _minimal_identity_data()
        data["principles"] = [
            {"id": "p1", "priority": 1, "statement": "Only"},
        ]
        result = validator.validate_dict(data)
        ordering_warnings = [w for w in result.warnings if w.type == "ordering"]
        assert len(ordering_warnings) == 0


class TestTraitTensionWarnings:
    """Extended tests for trait tension warnings including all configured pairs."""

    def test_verbosity_patience_tension(self, validator):
        """Verbosity vs patience with threshold 0.6 — diff > 0.6 triggers warning."""
        data = _minimal_identity_data()
        data["personality"]["traits"] = {"verbosity": 0.9, "patience": 0.1}
        result = validator.validate_dict(data)
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        matching = [
            w for w in tension_warnings if "verbosity" in w.message and "patience" in w.message
        ]
        assert len(matching) == 1

    def test_humor_rigor_tension(self, validator):
        """Humor vs rigor with threshold 0.7."""
        data = _minimal_identity_data()
        data["personality"]["traits"] = {"humor": 0.95, "rigor": 0.1}
        result = validator.validate_dict(data)
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        matching = [w for w in tension_warnings if "humor" in w.message and "rigor" in w.message]
        assert len(matching) == 1

    def test_empathy_directness_tension(self, validator):
        """Empathy vs directness with threshold 0.7."""
        data = _minimal_identity_data()
        data["personality"]["traits"] = {"empathy": 0.95, "directness": 0.1}
        result = validator.validate_dict(data)
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        matching = [
            w for w in tension_warnings if "empathy" in w.message and "directness" in w.message
        ]
        assert len(matching) == 1

    def test_no_tension_just_below_threshold(self, validator):
        """Diff exactly at threshold should NOT trigger warning (not strictly greater)."""
        # warmth vs directness threshold = 0.7
        # warmth=0.85 directness=0.15 => diff=0.70 => NOT > 0.7
        data = _minimal_identity_data()
        data["personality"]["traits"] = {"warmth": 0.85, "directness": 0.15}
        result = validator.validate_dict(data)
        tension_warnings = [
            w
            for w in result.warnings
            if w.type == "trait_tension" and "warmth" in w.message and "directness" in w.message
        ]
        assert len(tension_warnings) == 0

    def test_multiple_tensions_at_once(self, validator):
        """Multiple trait pairs can be in tension simultaneously."""
        data = _minimal_identity_data()
        data["personality"]["traits"] = {
            "warmth": 0.95,
            "directness": 0.05,
            "rigor": 0.95,
            "creativity": 0.05,
        }
        result = validator.validate_dict(data)
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        # warmth vs directness, rigor vs creativity
        assert len(tension_warnings) >= 2

    def test_tension_message_includes_values(self, validator):
        """The warning message should include the actual trait values."""
        data = _minimal_identity_data()
        data["personality"]["traits"] = {"warmth": 0.9, "directness": 0.1}
        result = validator.validate_dict(data)
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        assert len(tension_warnings) == 1
        assert "0.9" in tension_warnings[0].message
        assert "0.1" in tension_warnings[0].message


class TestValidateIdentityMethod:
    """Tests for IdentityValidator.validate_identity (accepts constructed AgentIdentity)."""

    def test_validate_identity_returns_warnings(self, validator):
        """validate_identity should return warnings for an already-constructed identity."""
        data = _minimal_identity_data()
        data["personality"]["traits"] = {"warmth": 0.95, "directness": 0.05}
        identity = AgentIdentity.model_validate(data)
        result = validator.validate_identity(identity)
        assert result.valid is True
        tension_warnings = [w for w in result.warnings if w.type == "trait_tension"]
        assert len(tension_warnings) >= 1
