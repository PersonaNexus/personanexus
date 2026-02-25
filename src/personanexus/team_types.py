"""Pydantic models for Multi-Agent Team Orchestration (PersonaNexus v2.0)."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums for Team Schema
# ---------------------------------------------------------------------------


class ConflictStrategy(enum.StrEnum):
    EVIDENCE_BASED_DECISION = "evidence_based_decision"
    AUTHORITY_HIERARCHY = "authority_hierarchy"
    CONSENSUS_WITH_FALLBACK = "consensus_with_fallback"
    CAPABILITY_MATRIX_LOOKUP = "capability_matrix_lookup"
    RISK_ASSESSMENT_MATRIX = "risk_assessment_matrix"


class WorkflowTriggerType(enum.StrEnum):
    COMPLETION = "completion"
    CONDITION = "condition"
    TIME_BASED = "time_based"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Team Metadata
# ---------------------------------------------------------------------------


class TeamMetadata(BaseModel):
    """Team-level metadata and identification."""

    id: str = Field(..., pattern=r"^team_\w+_\d{3}$")
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    created_at: datetime
    updated_at: datetime | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=50)
    source: str | None = None


# ---------------------------------------------------------------------------
# Agent Composition
# ---------------------------------------------------------------------------


class TeamAgent(BaseModel):
    """Agent definition within a team context."""

    agent_id: str = Field(..., pattern=r"^agt_[a-zA-Z0-9_]+$")
    role: str = Field(..., min_length=1)
    authority_level: int = Field(..., ge=1, le=5)
    expertise_domains: list[str] = Field(..., min_length=1, max_length=50)
    capabilities: list[str] = Field(default_factory=list, max_length=50)
    delegation_rights: list[str] = Field(default_factory=list, max_length=50)
    personality_summary: dict[str, float] = Field(default_factory=dict)

    # Optional full personality (if this agent is detailed in this team config)
    personality_traits: dict[str, float] | None = None
    personality_profile: dict[str, Any] | None = None
    behavioral_settings: dict[str, Any] | None = None


class TeamComposition(BaseModel):
    """Team composition and agent relationships."""

    agents: dict[str, TeamAgent] = Field(..., min_length=1)

    @field_validator("agents")
    @classmethod
    def validate_agent_composition(cls, v: dict[str, TeamAgent]) -> dict[str, TeamAgent]:
        """Validate team composition constraints."""
        if not v:
            raise ValueError("Team must have at least one agent")

        # Check authority levels are reasonable
        authority_levels = [agent.authority_level for agent in v.values()]
        if max(authority_levels) - min(authority_levels) > 3:
            raise ValueError("Authority level spread should not exceed 3 levels")

        return v


# ---------------------------------------------------------------------------
# Workflow Patterns
# ---------------------------------------------------------------------------


class WorkflowStage(BaseModel):
    """A single stage in a workflow pattern."""

    stage: str = Field(..., min_length=1)
    primary_agent: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    deliverables: list[str] = Field(default_factory=list, max_length=50)
    success_criteria: list[str] = Field(default_factory=list, max_length=50)
    trigger_conditions: list[str] = Field(default_factory=list, max_length=50)
    input_context: list[str] = Field(default_factory=list, max_length=50)
    max_duration: str | None = None


class WorkflowPattern(BaseModel):
    """A reusable workflow pattern for the team."""

    description: str = Field(..., min_length=1)
    estimated_duration: str | None = None
    success_rate: float | None = Field(None, ge=0.0, le=1.0)
    stages: list[WorkflowStage] = Field(..., min_length=1)

    @field_validator("stages")
    @classmethod
    def validate_stage_flow(cls, v: list[WorkflowStage]) -> list[WorkflowStage]:
        """Validate workflow stage dependencies."""
        stage_names = [stage.stage for stage in v]

        # Check for duplicate stage names
        if len(stage_names) != len(set(stage_names)):
            raise ValueError("Workflow stage names must be unique")

        return v


# ---------------------------------------------------------------------------
# Governance Framework
# ---------------------------------------------------------------------------


class DecisionFramework(BaseModel):
    """Framework for decision-making in a specific domain."""

    authority: str = Field(..., min_length=1)
    description: str | None = None
    consultation_required: list[str] = Field(default_factory=list, max_length=20)
    veto_rights: list[str] = Field(default_factory=list, max_length=20)
    escalation_criteria: list[str] = Field(default_factory=list, max_length=50)


class ConflictResolution(BaseModel):
    """Rules for resolving conflicts between agents."""

    description: str | None = None
    strategy: ConflictStrategy
    process: list[str] = Field(default_factory=list, max_length=50)
    criteria: list[str] = Field(default_factory=list, max_length=50)
    fallback: str | None = None
    escalation: str | None = None
    fallback_authority: str | None = None


class TeamGovernance(BaseModel):
    """Governance structure for multi-agent team."""

    decision_frameworks: dict[str, DecisionFramework] = Field(default_factory=dict)
    conflict_resolution: dict[str, ConflictResolution] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Performance Metrics
# ---------------------------------------------------------------------------


class PerformanceMetric(BaseModel):
    """A measurable performance indicator for the team."""

    metric: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    measurement: str = Field(..., min_length=1)
    review_frequency: str | None = None


class TeamPerformanceMetrics(BaseModel):
    """Performance measurement framework for the team."""

    team_effectiveness: list[PerformanceMetric] = Field(default_factory=list, max_length=50)
    individual_contributions: dict[str, list[PerformanceMetric]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Collaboration Protocols
# ---------------------------------------------------------------------------


class HandoffStandards(BaseModel):
    """Standards for agent-to-agent handoffs."""

    context_transfer: dict[str, Any] = Field(default_factory=dict)
    validation: str | None = None
    timeout: str | None = None


class QualityGate(BaseModel):
    """Quality gates for workflow stages."""

    gate: str = Field(..., min_length=1)
    enforced_by: str = Field(..., min_length=1)
    criteria: list[str] = Field(..., min_length=1, max_length=20)
    auto_check: bool = False


class CollaborationProtocols(BaseModel):
    """Protocols for agent collaboration."""

    handoff_standards: HandoffStandards = Field(default_factory=HandoffStandards)
    quality_gates: list[QualityGate] = Field(default_factory=list, max_length=50)
    status_updates: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Adaptation Rules
# ---------------------------------------------------------------------------


class AdaptationTrigger(BaseModel):
    """Trigger for team adaptation."""

    condition: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)


class AdaptationRules(BaseModel):
    """Rules for team self-optimization."""

    workflow_optimization: dict[str, Any] = Field(default_factory=dict)
    team_composition_insights: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Operations Configuration
# ---------------------------------------------------------------------------


class OperationsConfig(BaseModel):
    """Operational parameters for the team."""

    working_hours: dict[str, Any] = Field(default_factory=dict)
    resource_limits: dict[str, Any] = Field(default_factory=dict)
    monitoring: dict[str, Any] = Field(default_factory=dict)
    integration: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-Level Team Configuration
# ---------------------------------------------------------------------------


class TeamConfiguration(BaseModel):
    """Complete multi-agent team configuration."""

    schema_version: str = Field("2.0", pattern=r"^\d+\.\d+$")

    team: TeamSpec


class TeamSpec(BaseModel):
    """Team specification section."""

    metadata: TeamMetadata
    composition: TeamComposition
    workflow_patterns: dict[str, WorkflowPattern] = Field(default_factory=dict)
    governance: TeamGovernance = Field(default_factory=TeamGovernance)
    collaboration_protocols: CollaborationProtocols = Field(default_factory=CollaborationProtocols)
    performance_metrics: TeamPerformanceMetrics = Field(default_factory=TeamPerformanceMetrics)
    adaptation_rules: AdaptationRules = Field(default_factory=AdaptationRules)
    operations: OperationsConfig = Field(default_factory=OperationsConfig)

    @field_validator("composition")
    @classmethod
    def validate_team_size(cls, v: TeamComposition) -> TeamComposition:
        """Validate reasonable team size."""
        if len(v.agents) > 20:
            raise ValueError("Teams should not exceed 20 agents for effective coordination")
        return v

    @field_validator("workflow_patterns")
    @classmethod
    def validate_workflow_agents(
        cls,
        v: dict[str, WorkflowPattern],
        info,
    ) -> dict[str, WorkflowPattern]:
        """Validate that workflow agents exist in team composition."""
        if not info.data:
            return v

        composition = info.data.get("composition")
        if not composition or not hasattr(composition, "agents"):
            return v

        agent_names = set(composition.agents.keys())

        for workflow_name, pattern in v.items():
            for stage in pattern.stages:
                if stage.primary_agent not in agent_names:
                    raise ValueError(
                        f"Workflow '{workflow_name}' stage '{stage.stage}' references "
                        f"unknown agent '{stage.primary_agent}'"
                    )

        return v

    @model_validator(mode="after")
    def validate_agent_references(self) -> TeamSpec:
        """Validate that agent references in governance and collaboration exist in composition."""
        agent_names = set(self.composition.agents.keys())
        errors: list[str] = []

        # Check governance decision framework references
        for domain, framework in self.governance.decision_frameworks.items():
            if framework.authority not in agent_names:
                errors.append(
                    f"Governance decision framework '{domain}' references "
                    f"unknown authority agent '{framework.authority}'"
                )
            for agent in framework.consultation_required:
                if agent not in agent_names:
                    errors.append(
                        f"Governance decision framework '{domain}' references "
                        f"unknown consultation agent '{agent}'"
                    )
            for agent in framework.veto_rights:
                if agent not in agent_names:
                    errors.append(
                        f"Governance decision framework '{domain}' references "
                        f"unknown veto agent '{agent}'"
                    )

        # Check quality gate enforced_by references
        for gate in self.collaboration_protocols.quality_gates:
            if gate.enforced_by not in agent_names:
                errors.append(
                    f"Quality gate '{gate.gate}' references "
                    f"unknown enforcer agent '{gate.enforced_by}'"
                )

        # Check conflict resolution fallback_authority references
        for domain, resolution in self.governance.conflict_resolution.items():
            if resolution.fallback_authority and resolution.fallback_authority not in agent_names:
                errors.append(
                    f"Conflict resolution '{domain}' references "
                    f"unknown fallback authority '{resolution.fallback_authority}'"
                )

        if errors:
            raise ValueError(
                "Invalid agent references in team configuration:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        return self


# ---------------------------------------------------------------------------
# Update forward references
# ---------------------------------------------------------------------------

TeamConfiguration.model_rebuild()
