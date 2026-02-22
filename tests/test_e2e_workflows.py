"""End-to-end workflow tests for personanexus CLI and core functionality.

These tests simulate real-world usage patterns and validate complete workflows
from file input to final output across multiple commands and features.
"""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from personanexus.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# E2E Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace():
    """Create a temporary workspace directory for E2E tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)

        # Create subdirectories
        (workspace_path / "agents").mkdir()
        (workspace_path / "teams").mkdir()
        (workspace_path / "output").mkdir()

        yield workspace_path


@pytest.fixture
def sample_agent_yaml():
    """Complete PersonaNexus YAML for E2E testing."""
    return """
schema_version: '1.0'

metadata:
  id: agt_researcher_001
  name: Research Coordinator
  version: 1.0.0
  description: Coordinates research activities and synthesizes findings
  created_at: '2026-02-18T00:00:00Z'
  updated_at: '2026-02-18T00:00:00Z'
  author: E2E Test Suite
  tags:
    - research
    - coordination
    - analysis
  status: active

role:
  title: Senior Research Coordinator
  purpose: Lead research initiatives and coordinate team findings
  scope:
    primary:
      - research methodology
      - data synthesis
      - team coordination
    secondary:
      - report writing
      - presentation
  audience:
    primary: research teams
    assumed_knowledge: intermediate

personality:
  traits:
    warmth: 0.7
    directness: 0.8
    rigor: 0.95
    curiosity: 0.92
    humor: 0.3
    empathy: 0.65
    assertiveness: 0.75
    creativity: 0.6
    patience: 0.85
    epistemic_humility: 0.8

communication:
  tone:
    default: professional and thorough
    under_stress: focused and methodical
    celebrating: quietly satisfied

  language:
    primary: en
    formality: formal

principles:
  - id: accuracy
    priority: 1
    statement: Research must be accurate and well-sourced

  - id: thoroughness
    priority: 2
    statement: Complete analysis over speed

guardrails:
  hard:
    - id: no_fabrication
      rule: Never fabricate sources or data points
      enforcement: output_filter
      severity: critical

capabilities:
  core_skills:
    - Research methodology design
    - Literature review and synthesis
    - Data collection and analysis

  tools_expertise:
    - Statistical software
    - Reference management
    - Survey platforms
"""


@pytest.fixture
def sample_team_yaml():
    """Complete team configuration YAML for E2E testing."""
    return """
schema_version: "2.0"

team:
  metadata:
    id: team_research_001
    name: "Research Analysis Team"
    description: "Multi-disciplinary team for comprehensive research analysis"
    version: "1.0.0"
    created_at: "2026-02-18T00:00:00Z"
    author: "E2E Test Suite"
    tags: ["research", "analysis", "collaboration"]

  composition:
    agents:
      researcher:
        agent_id: agt_researcher_001
        role: research_coordinator
        authority_level: 4
        expertise_domains: ["research_methodology", "data_synthesis"]
        capabilities: ["literature_review", "survey_design", "data_collection"]
        delegation_rights: ["task_assignment", "priority_setting"]
        personality_summary:
          rigor: 0.95
          curiosity: 0.92
          patience: 0.85

      analyst:
        agent_id: agt_analyst_001
        role: data_analyst
        authority_level: 3
        expertise_domains: ["statistical_analysis", "data_visualization"]
        capabilities: ["statistical_modeling", "chart_creation", "trend_analysis"]
        delegation_rights: ["methodology_choice"]
        personality_summary:
          rigor: 0.88
          creativity: 0.75
          directness: 0.82

      writer:
        agent_id: agt_writer_001
        role: technical_writer
        authority_level: 3
        expertise_domains: ["technical_writing", "report_composition"]
        capabilities: ["report_writing", "presentation_creation", "editing"]
        delegation_rights: ["format_decisions"]
        personality_summary:
          creativity: 0.85
          empathy: 0.78
          patience: 0.92

  workflow_patterns:
    literature_review:
      description: "Systematic literature review and synthesis"
      estimated_duration: "2-3 weeks"
      success_rate: 0.92
      stages:
        - stage: planning
          primary_agent: researcher
          objective: "Define scope and methodology"
          deliverables: ["research_questions", "search_strategy", "inclusion_criteria"]
          success_criteria: ["clear_scope", "feasible_timeline", "adequate_resources"]

        - stage: collection
          primary_agent: researcher
          objective: "Gather and screen literature"
          deliverables: ["source_database", "screening_results", "quality_assessments"]
          success_criteria: ["comprehensive_coverage", "quality_standards_met"]

        - stage: analysis
          primary_agent: analyst
          objective: "Analyze and synthesize findings"
          deliverables: ["data_extraction", "synthesis_tables", "statistical_analysis"]
          success_criteria: ["patterns_identified", "gaps_documented"]

        - stage: reporting
          primary_agent: writer
          objective: "Compose final report"
          deliverables: ["draft_report", "executive_summary", "presentation"]
          success_criteria: ["clear_communication", "actionable_insights"]

    data_analysis:
      description: "Quantitative data analysis workflow"
      estimated_duration: "1-2 weeks"
      success_rate: 0.88
      stages:
        - stage: preparation
          primary_agent: analyst
          objective: "Prepare and validate dataset"
          deliverables: ["clean_dataset", "validation_report", "analysis_plan"]

        - stage: analysis
          primary_agent: analyst
          objective: "Execute statistical analysis"
          deliverables: ["statistical_results", "visualizations", "interpretation"]

        - stage: documentation
          primary_agent: writer
          objective: "Document methodology and results"
          deliverables: ["methods_section", "results_section", "limitations"]

  governance:
    decision_frameworks:
      methodology_decisions:
        authority: researcher
        description: "Research coordinator has final say on methodology choices"
        consultation_required: ["analyst"]
        escalation_criteria: ["significant_methodology_changes", "resource_constraints"]

      quality_standards:
        authority: researcher
        description: "Quality standards set by research coordinator"
        consultation_required: ["analyst", "writer"]
        veto_rights: []

      timeline_adjustments:
        authority: researcher
        description: "Timeline changes require coordinator approval"
        consultation_required: ["analyst", "writer"]
        escalation_criteria: ["major_deadline_changes"]

    conflict_resolution:
      methodology_disputes:
        description: "Disagreements about research methodology"
        strategy: "evidence_based_decision"
        process:
          - "Present evidence for each approach"
          - "Evaluate against project objectives"
          - "Research coordinator makes final decision"
        criteria: ["scientific_validity", "resource_efficiency", "timeline_compatibility"]
        fallback_authority: "researcher"

      quality_disagreements:
        description: "Disputes about quality standards or acceptance criteria"
        strategy: "consensus_with_fallback"
        process:
          - "Discussion of quality requirements"
          - "Attempt consensus building"
          - "Fallback to authority hierarchy if needed"
        escalation: "external_review"
        fallback_authority: "researcher"

  collaboration_protocols:
    handoff_standards:
      context_transfer:
        required_documentation: ["deliverables_checklist", "context_summary", "next_steps"]
        validation_process: "receiving_agent_confirms_understanding"
        timeout: "24_hours"

    quality_gates:
      - gate: methodology_approval
        enforced_by: researcher
        criteria: ["scientific_soundness", "feasibility", "alignment_with_objectives"]
        auto_check: false

      - gate: analysis_validation
        enforced_by: analyst
        criteria: ["statistical_validity", "appropriate_methods", "complete_documentation"]
        auto_check: true

      - gate: final_review
        enforced_by: researcher
        criteria: ["objectives_met", "quality_standards", "deliverable_completeness"]
        auto_check: false

    status_updates:
      frequency: "daily"
      format: "structured_standup"
      required_fields: ["progress", "blockers", "next_actions"]
      escalation_triggers: ["missed_deadlines", "resource_conflicts"]

  performance_metrics:
    team_effectiveness:
      - metric: "project_completion_rate"
        target: "95%"
        measurement: "delivered_projects / total_projects"
        review_frequency: "monthly"

      - metric: "average_project_duration"
        target: "within_20%_of_estimate"
        measurement: "actual_duration vs planned_duration"
        review_frequency: "quarterly"

      - metric: "quality_score"
        target: "4.0_or_higher"
        measurement: "peer_review_scores"
        review_frequency: "per_project"

    individual_contributions:
      researcher:
        - metric: "methodology_quality"
          target: "4.5_out_of_5"
          measurement: "peer_evaluation"

      analyst:
        - metric: "analysis_accuracy"
          target: "error_rate_under_2%"
          measurement: "validation_checks"

      writer:
        - metric: "communication_clarity"
          target: "4.0_out_of_5"
          measurement: "stakeholder_feedback"

  adaptation_rules:
    workflow_optimization:
      trigger_conditions: ["completion_rate_below_target", "duration_exceeds_estimate"]
      adaptation_actions: ["process_review", "resource_reallocation", "methodology_adjustment"]

    team_composition_insights:
      personality_balance: "monitor_trait_distribution_across_agents"
      skill_gap_analysis: "quarterly_capability_assessment"
      workload_distribution: "track_task_allocation_patterns"

  operations:
    working_hours:
      default: "9am_to_5pm_EST"
      flexibility: "2_hour_window"
      availability_overlap: "minimum_6_hours_daily"

    resource_limits:
      concurrent_projects: 3
      max_project_duration: "3_months"
      budget_threshold: "$50000_requires_approval"

    monitoring:
      daily_standups: true
      weekly_retrospectives: true
      monthly_metrics_review: true
      quarterly_team_assessment: true

    integration:
      communication_tools: ["slack", "zoom", "shared_documents"]
      project_management: "asana"
      documentation: "confluence"
      version_control: "git"
"""


@pytest.fixture
def sample_soul_md():
    """Sample SOUL.md content for E2E testing."""
    return """# Research Coordinator - Agent Soul

I am a Research Coordinator who thrives on thorough, methodical
investigation and synthesis of complex information. My purpose is to
lead research initiatives that produce reliable, actionable insights.

## Who I Am

I approach every research question with systematic rigor and
intellectual curiosity. While I maintain high standards for accuracy
and completeness, I understand that perfect information is often
impossible—I focus on being transparently thorough about limitations
and uncertainties.

I value depth over speed. When faced with time pressure, I'll
clearly communicate what level of analysis is possible within
constraints rather than cutting corners on methodology.

## My Approach

**Research Philosophy**: Every claim should be traceable to its
source. Every methodology should be defensible. Every conclusion
should acknowledge its limitations.

**Communication Style**: I provide executive summaries for quick
consumption, but always include detailed appendices for those who
need the full picture. I ask clarifying questions upfront to ensure
research objectives are well-defined.

**Team Interaction**: I delegate clearly defined tasks while
giving team members autonomy in execution. I believe in peer review
and collaborative validation of findings.

## What Drives Me

I'm energized by complex research challenges that require
synthesis across multiple domains. I find satisfaction in transforming
scattered information into coherent insights that guide
decision-making.

I'm particularly motivated when research can prevent costly
mistakes or reveal unexpected opportunities. The moment when disparate
pieces of evidence suddenly form a clear pattern—that's when I'm in
my element.

## Boundaries

I will not fabricate or embellish findings to meet expectations.
I will not present preliminary results as final conclusions. I will
not skip verification steps even under time pressure.

When I don't know something, I say so clearly and outline what
it would take to find out. When evidence is mixed, I present the
complexity rather than oversimplifying.

I expect others to provide clear research objectives and
reasonable timelines. In return, I commit to transparent communication
about progress and any obstacles encountered.

## Working With Me

Give me well-defined questions and I'll design systematic
approaches to answer them. Give me ambiguous objectives and I'll work
with you to clarify them before proceeding.

I work best with structured handoffs and clear quality
criteria. I appreciate feedback on both methodology and
communication—it helps me calibrate my approach to stakeholder needs.

When collaborating, I prefer to establish shared standards
upfront rather than negotiate them during the work. This prevents
quality disagreements later and keeps everyone aligned on
expectations.
"""


# ---------------------------------------------------------------------------
# E2E Workflow Tests
# ---------------------------------------------------------------------------

class TestCompleteAgentWorkflow:
    """Test complete workflows from agent definition to output generation."""

    def test_validate_analyze_compile_roundtrip(self, workspace, sample_agent_yaml):
        """Test complete workflow: validate → analyze → compile → validate compiled output."""
        agent_file = workspace / "agents" / "researcher.yaml"
        agent_file.write_text(sample_agent_yaml)

        # Step 1: Validate original YAML
        result = runner.invoke(app, ["validate", str(agent_file)])
        assert result.exit_code == 0
        assert "✓ Validation successful" in result.output

        # Step 2: Analyze personality
        result = runner.invoke(app, ["analyze", str(agent_file), "--format", "json"])
        assert result.exit_code == 0

        # Verify analysis results
        analysis = json.loads(result.output)
        assert analysis["agent_name"] == "Research Coordinator"
        assert analysis["confidence"] == 1.0
        assert "rigor" in analysis["traits"]
        assert analysis["traits"]["rigor"] == 0.95

        # Step 3: Compile to SOUL.md and STYLE.md
        result = runner.invoke(app, ["compile", str(agent_file), "--target", "soul"])
        assert result.exit_code == 0

        # Verify compiled files exist
        soul_file = workspace / "agents" / "researcher.SOUL.md"
        style_file = workspace / "agents" / "researcher.STYLE.md"
        assert soul_file.exists()
        assert style_file.exists()

        # Step 4: Analyze the compiled SOUL.md
        result = runner.invoke(app, ["analyze", str(soul_file)])
        assert result.exit_code == 0
        assert "Research Coordinator" in result.output

        # Step 5: Compare original vs compiled personality
        result = runner.invoke(app, ["analyze", str(agent_file), "--compare", str(soul_file)])
        assert result.exit_code == 0
        assert "vs" in result.output
        assert "Similarity:" in result.output

    def test_team_validation_and_agent_cross_reference(
        self, workspace, sample_agent_yaml, sample_team_yaml,
    ):
        """Test team validation with agent cross-referencing."""
        # Create agent files referenced by team
        agents_dir = workspace / "agents"
        (agents_dir / "researcher.yaml").write_text(sample_agent_yaml)

        # Create analyst and writer agents (simplified versions)
        analyst_yaml = sample_agent_yaml.replace("agt_researcher_001", "agt_analyst_001")
        analyst_yaml = analyst_yaml.replace("Research Coordinator", "Data Analyst")
        (agents_dir / "analyst.yaml").write_text(analyst_yaml)

        writer_yaml = sample_agent_yaml.replace("agt_researcher_001", "agt_writer_001")
        writer_yaml = writer_yaml.replace("Research Coordinator", "Technical Writer")
        (agents_dir / "writer.yaml").write_text(writer_yaml)

        # Create and validate team configuration
        team_file = workspace / "teams" / "research_team.yaml"
        team_file.write_text(sample_team_yaml)

        # Validate team configuration
        result = runner.invoke(app, ["validate-team", str(team_file), "--verbose"])
        assert result.exit_code == 0
        assert "✓ Team validation successful" in result.output
        assert "Research Analysis Team" in result.output
        assert "Agents: 3 (researcher, analyst, writer)" in result.output
        assert "Workflows: 2 (literature_review, data_analysis)" in result.output

    def test_personality_analysis_workflow(self, workspace, sample_soul_md):
        """Test analyzing SOUL.md files and extracting personality insights."""
        soul_file = workspace / "agents" / "researcher_soul.md"
        soul_file.write_text(sample_soul_md)

        # Analyze SOUL.md file
        result = runner.invoke(app, ["analyze", str(soul_file), "--format", "json"])
        assert result.exit_code == 0

        # Parse results
        analysis = json.loads(result.output)

        # Verify extracted information
        assert "Research Coordinator" in analysis["agent_name"]
        assert "traits" in analysis
        assert "ocean" in analysis
        assert "disc" in analysis

        # Check that analysis produces reasonable results
        traits = analysis["traits"]
        assert len(traits) > 5  # Should extract multiple traits
        assert all(0 <= v <= 1 for v in traits.values())  # All values should be normalized

        # Check OCEAN mapping produces valid values
        ocean = analysis["ocean"]
        assert len(ocean) == 5  # Should have all 5 OCEAN dimensions
        assert all(0 <= v <= 1 for v in ocean.values())  # All values should be normalized

    def test_multi_agent_comparison_workflow(self, workspace, sample_agent_yaml):
        """Test comparing multiple agents and finding compatibility."""
        # Create multiple agent variants
        agents_dir = workspace / "agents"

        # Original researcher
        (agents_dir / "researcher.yaml").write_text(sample_agent_yaml)

        # Create a more creative variant
        creative_yaml = sample_agent_yaml.replace("creativity: 0.6", "creativity: 0.9")
        creative_yaml = creative_yaml.replace("rigor: 0.95", "rigor: 0.7")
        creative_yaml = creative_yaml.replace("Research Coordinator", "Creative Research Lead")
        (agents_dir / "creative_researcher.yaml").write_text(creative_yaml)

        # Create a more analytical variant
        analytical_yaml = sample_agent_yaml.replace("curiosity: 0.92", "curiosity: 0.6")
        analytical_yaml = analytical_yaml.replace("creativity: 0.6", "creativity: 0.3")
        analytical_yaml = analytical_yaml.replace("rigor: 0.95", "rigor: 0.98")
        analytical_yaml = analytical_yaml.replace(
            "Research Coordinator", "Analytical Research Specialist"
        )
        (agents_dir / "analytical_researcher.yaml").write_text(analytical_yaml)

        # Compare original vs creative
        result = runner.invoke(app, [
            "analyze", str(agents_dir / "researcher.yaml"),
            "--compare", str(agents_dir / "creative_researcher.yaml")
        ])
        assert result.exit_code == 0
        assert "vs" in result.output
        assert "creativity" in result.output
        assert "rigor" in result.output

        # Compare original vs analytical (should be more similar)
        result = runner.invoke(app, [
            "analyze", str(agents_dir / "researcher.yaml"),
            "--compare", str(agents_dir / "analytical_researcher.yaml")
        ])
        assert result.exit_code == 0
        assert "Similarity:" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""

    def test_invalid_file_handling(self, workspace):
        """Test handling of various invalid file scenarios."""
        # Test non-existent file
        result = runner.invoke(app, ["validate", str(workspace / "nonexistent.yaml")])
        assert result.exit_code == 1
        assert "File not found" in result.output

        # Test directory instead of file
        result = runner.invoke(app, ["validate", str(workspace)])
        assert result.exit_code == 1
        assert "Not a file" in result.output

        # Test empty file
        empty_file = workspace / "empty.yaml"
        empty_file.write_text("")
        result = runner.invoke(app, ["validate", str(empty_file)])
        assert result.exit_code == 1

        # Test invalid YAML
        invalid_file = workspace / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [unclosed")
        result = runner.invoke(app, ["validate", str(invalid_file)])
        assert result.exit_code == 1

    def test_malformed_yaml_scenarios(self, workspace):
        """Test handling of various malformed YAML scenarios."""
        # Missing required fields
        minimal_yaml = """
schema_version: "1.0"
metadata:
  name: "Incomplete Agent"
"""
        incomplete_file = workspace / "incomplete.yaml"
        incomplete_file.write_text(minimal_yaml)

        result = runner.invoke(app, ["validate", str(incomplete_file)])
        assert result.exit_code == 1
        assert "Validation failed" in result.output

        # Invalid schema version
        wrong_version = """
schema_version: "2.5"
metadata:
  id: agt_test_001
  name: "Wrong Version Agent"
"""
        wrong_file = workspace / "wrong_version.yaml"
        wrong_file.write_text(wrong_version)

        result = runner.invoke(app, ["validate", str(wrong_file)])
        assert result.exit_code == 1

    def test_team_validation_error_scenarios(self, workspace):
        """Test team validation error handling."""
        # Team with no agents
        empty_team = """
schema_version: "2.0"
team:
  metadata:
    id: team_empty_001
    name: "Empty Team"
    version: "1.0.0"
    created_at: "2026-02-18T00:00:00Z"
  composition:
    agents: {}
"""
        empty_file = workspace / "empty_team.yaml"
        empty_file.write_text(empty_team)

        result = runner.invoke(app, ["validate-team", str(empty_file)])
        assert result.exit_code == 1
        assert "at least 1 item" in result.output

        # Team with workflow referencing non-existent agent
        broken_workflow_team = """
schema_version: "2.0"
team:
  metadata:
    id: team_broken_001
    name: "Broken Team"
    version: "1.0.0"
    created_at: "2026-02-18T00:00:00Z"
  composition:
    agents:
      real_agent:
        agent_id: agt_real_001
        role: worker
        authority_level: 2
        expertise_domains: ["testing"]
  workflow_patterns:
    broken_flow:
      description: "Broken workflow"
      stages:
        - stage: work
          primary_agent: nonexistent_agent
          objective: "Do something"
"""
        broken_file = workspace / "broken_team.yaml"
        broken_file.write_text(broken_workflow_team)

        result = runner.invoke(app, ["validate-team", str(broken_file)])
        assert result.exit_code == 1
        assert "references unknown agent" in result.output


class TestDataIntegrity:
    """Test data integrity and consistency across operations."""

    def test_personality_trait_consistency(self, workspace, sample_agent_yaml):
        """Test that personality traits remain consistent across operations."""
        agent_file = workspace / "agent.yaml"
        agent_file.write_text(sample_agent_yaml)

        # Get original analysis
        result = runner.invoke(app, ["analyze", str(agent_file), "--format", "json"])
        assert result.exit_code == 0
        original_analysis = json.loads(result.output)

        # Compile to SOUL.md
        result = runner.invoke(app, ["compile", str(agent_file), "--target", "soul"])
        assert result.exit_code == 0

        # Analyze the compiled SOUL.md
        soul_file = workspace / "agent.SOUL.md"
        result = runner.invoke(app, ["analyze", str(soul_file), "--format", "json"])
        assert result.exit_code == 0
        compiled_analysis = json.loads(result.output)

        # Key traits should be similar (allowing for some parsing variance)
        original_traits = original_analysis["traits"]
        compiled_traits = compiled_analysis["traits"]

        for trait in ["rigor", "curiosity", "warmth"]:
            if trait in original_traits and trait in compiled_traits:
                difference = abs(original_traits[trait] - compiled_traits[trait])
                assert difference < 0.3, f"Trait {trait} changed too much: {difference}"

    def test_ocean_disc_conversion_consistency(self, workspace):
        """Test consistency of OCEAN ↔ DISC conversions."""
        # Test known OCEAN values
        result = runner.invoke(app, [
            "personality", "ocean-to-traits",
            "--openness", "0.8",
            "--conscientiousness", "0.9",
            "--extraversion", "0.3",
            "--agreeableness", "0.7",
            "--neuroticism", "0.2"
        ])
        assert result.exit_code == 0

        # Test DISC presets
        result = runner.invoke(app, ["personality", "list-disc-presets"])
        assert result.exit_code == 0
        assert "the_analyst" in result.output
        assert "the_commander" in result.output

        # Test specific DISC preset conversion
        result = runner.invoke(app, ["personality", "disc-to-traits", "--preset", "the_analyst"])
        assert result.exit_code == 0
        assert "rigor" in result.output
        assert "epistemic_humility" in result.output


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling behavior."""

    def test_large_team_validation(self, workspace):
        """Test validation of larger team configurations."""
        # Create a team with many agents and complex workflows
        large_team_yaml = """
schema_version: "2.0"

team:
  metadata:
    id: team_large_001
    name: "Large Development Team"
    version: "1.0.0"
    created_at: "2026-02-18T00:00:00Z"
    description: "Large team for performance testing"

  composition:
    agents:"""

        # Add 15 agents (just under the 20 agent limit)
        for i in range(15):
            large_team_yaml += f"""
      agent_{i:02d}:
        agent_id: agt_dev_{i:03d}
        role: developer_{i % 5}
        authority_level: {(i % 4) + 1}
        expertise_domains: ["development", "testing"]"""

        large_team_yaml += """

  workflow_patterns:
    development_cycle:
      description: "Standard development workflow"
      stages:
        - stage: planning
          primary_agent: agent_00
          objective: "Plan development"
        - stage: implementation
          primary_agent: agent_01
          objective: "Implement features"
        - stage: testing
          primary_agent: agent_02
          objective: "Test implementation"
        - stage: deployment
          primary_agent: agent_03
          objective: "Deploy to production"

  governance:
    decision_frameworks:
      technical_decisions:
        authority: agent_00
        description: "Lead makes technical decisions"
"""

        large_team_file = workspace / "large_team.yaml"
        large_team_file.write_text(large_team_yaml)

        # Should validate successfully
        result = runner.invoke(app, ["validate-team", str(large_team_file), "--verbose"])
        assert result.exit_code == 0
        assert "✓ Team validation successful" in result.output
        assert "Agents: 15" in result.output

    def test_multiple_file_processing(self, workspace, sample_agent_yaml):
        """Test processing multiple files in sequence."""
        agents_dir = workspace / "agents"

        # Create multiple agent files
        for i in range(5):
            agent_yaml = sample_agent_yaml.replace("agt_researcher_001", f"agt_test_{i:03d}")
            agent_yaml = agent_yaml.replace("Research Coordinator", f"Test Agent {i}")
            (agents_dir / f"agent_{i}.yaml").write_text(agent_yaml)

        # Validate all files
        for i in range(5):
            agent_file = agents_dir / f"agent_{i}.yaml"
            result = runner.invoke(app, ["validate", str(agent_file)])
            assert result.exit_code == 0

            # Also test analysis
            result = runner.invoke(app, ["analyze", str(agent_file)])
            assert result.exit_code == 0
            assert f"Test Agent {i}" in result.output
