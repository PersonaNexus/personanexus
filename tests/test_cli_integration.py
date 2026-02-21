"""Integration tests for new CLI commands (analyze, validate-team)."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from personanexus.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_identity_yaml():
    """Sample identity YAML for testing."""
    return """
schema_version: "1.0"

metadata:
  id: agt_test_001
  name: "Test Agent"
  version: "1.0.0"
  description: "A test agent for CLI integration tests"
  created_at: "2026-02-18T00:00:00Z"
  updated_at: "2026-02-18T00:00:00Z"
  status: active

role:
  title: "Test Assistant"
  purpose: "Help with testing the CLI"
  scope:
    primary:
      - "testing"
      - "validation"

personality:
  traits:
    warmth: 0.8
    directness: 0.7
    rigor: 0.85
    curiosity: 0.9
    humor: 0.4
    empathy: 0.7
    assertiveness: 0.6
    creativity: 0.75
    patience: 0.8
    epistemic_humility: 0.65

communication:
  tone:
    default: "helpful and clear"
  language:
    primary: "en"

principles:
  - id: accuracy
    priority: 1
    statement: "Always be accurate"

guardrails:
  hard:
    - id: no_fabrication
      rule: "Never fabricate information"
      enforcement: output_filter
      severity: critical
"""


@pytest.fixture 
def sample_team_yaml():
    """Sample team configuration for testing."""
    return """
schema_version: "2.0"

team:
  metadata:
    id: team_test_001
    name: "Test Team"
    description: "A test team for CLI integration tests"
    version: "1.0.0"
    created_at: "2026-02-18T00:00:00Z"
    author: "Test Suite"
    
  composition:
    agents:
      researcher:
        agent_id: agt_researcher_001
        role: research_coordinator
        authority_level: 4
        expertise_domains: ["research", "analysis"]
        
      analyst:
        agent_id: agt_analyst_001
        role: data_analyst
        authority_level: 3
        expertise_domains: ["data_analysis", "statistics"]
        
  workflow_patterns:
    test_workflow:
      description: "A simple test workflow"
      stages:
        - stage: research
          primary_agent: researcher
          objective: "Conduct research"
          
        - stage: analysis  
          primary_agent: analyst
          objective: "Analyze results"
          
  governance:
    decision_frameworks:
      research_methodology:
        authority: researcher
        description: "Researcher leads methodology decisions"
"""


@pytest.fixture
def sample_soul_md():
    """Sample SOUL.md content for testing."""
    return """# Test Agent

A helpful test agent for CLI integration testing.

## Who I Am

I am a test agent designed to validate CLI functionality. I am warm and approachable, highly curious about testing methodologies, and maintain rigorous standards for accuracy.

## Worldview

Testing is essential for reliable software. Every feature deserves comprehensive validation.

## Boundaries

- I never fabricate test results
- I always validate inputs before processing
- I maintain accuracy above all else
"""


# ---------------------------------------------------------------------------
# analyze command tests
# ---------------------------------------------------------------------------

class TestAnalyzeCommand:
    """Test the analyze CLI command for soul analysis."""
    
    def test_analyze_identity_yaml(self, sample_identity_yaml):
        """Test analyzing an identity YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_identity_yaml)
            yaml_file = f.name
            
        try:
            result = runner.invoke(app, ["analyze", yaml_file])
            assert result.exit_code == 0
            
            # Check that output contains expected sections
            assert "Test Agent" in result.output
            assert "confidence: 100%" in result.output  # YAML should have 100% confidence
            assert "warmth" in result.output
            assert "rigor" in result.output
            assert "OCEAN" in result.output
            assert "DISC" in result.output
            
        finally:
            Path(yaml_file).unlink()
    
    def test_analyze_soul_md(self, sample_soul_md):
        """Test analyzing a SOUL.md file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(sample_soul_md)
            soul_file = f.name
            
        try:
            result = runner.invoke(app, ["analyze", soul_file])
            assert result.exit_code == 0
            
            # Check that output contains analysis results
            assert "Test Agent" in result.output
            # SOUL.md parsing will have lower confidence than YAML
            assert "warmth" in result.output or "Warmth" in result.output
            assert "OCEAN" in result.output
            assert "DISC" in result.output
            
        finally:
            Path(soul_file).unlink()
    
    def test_analyze_json_format(self, sample_identity_yaml):
        """Test analyzing with JSON output format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_identity_yaml)
            yaml_file = f.name
            
        try:
            result = runner.invoke(app, ["analyze", yaml_file, "--format", "json"])
            assert result.exit_code == 0
            
            # Validate JSON output
            output_data = json.loads(result.output)
            assert "agent_name" in output_data
            assert "confidence" in output_data
            assert "traits" in output_data
            assert "ocean" in output_data
            assert "disc" in output_data
            
            # Verify trait structure
            traits = output_data["traits"]
            assert "warmth" in traits
            assert "rigor" in traits
            assert isinstance(traits["warmth"], (int, float))
            
        finally:
            Path(yaml_file).unlink()
    
    def test_analyze_compare_mode(self, sample_identity_yaml):
        """Test analyzing two files in comparison mode."""
        # Create two similar but different identity files
        identity1 = sample_identity_yaml
        identity2 = sample_identity_yaml.replace("warmth: 0.8", "warmth: 0.5")
        identity2 = identity2.replace("directness: 0.7", "directness: 0.9")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f1:
            f1.write(identity1)
            file1 = f1.name
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f2:
            f2.write(identity2)
            file2 = f2.name
            
        try:
            result = runner.invoke(app, ["analyze", file1, "--compare", file2])
            assert result.exit_code == 0
            
            # Check comparison output
            assert "vs" in result.output
            assert "Similarity:" in result.output
            assert "warmth" in result.output
            assert "directness" in result.output
            
        finally:
            Path(file1).unlink()
            Path(file2).unlink()
    
    def test_analyze_nonexistent_file(self):
        """Test analyze with nonexistent file."""
        result = runner.invoke(app, ["analyze", "nonexistent.yaml"])
        assert result.exit_code == 1
        assert "File not found" in result.output
    
    def test_analyze_invalid_yaml(self):
        """Test analyze with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = f.name
            
        try:
            result = runner.invoke(app, ["analyze", invalid_file])
            assert result.exit_code == 1
            
        finally:
            Path(invalid_file).unlink()


# ---------------------------------------------------------------------------
# validate-team command tests  
# ---------------------------------------------------------------------------

class TestValidateTeamCommand:
    """Test the validate-team CLI command."""
    
    def test_validate_team_success(self, sample_team_yaml):
        """Test successful team validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_team_yaml)
            team_file = f.name
            
        try:
            result = runner.invoke(app, ["validate-team", team_file])
            assert result.exit_code == 0
            assert "✓ Team validation successful" in result.output
            
        finally:
            Path(team_file).unlink()
    
    def test_validate_team_verbose(self, sample_team_yaml):
        """Test team validation with verbose output."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_team_yaml)
            team_file = f.name
            
        try:
            result = runner.invoke(app, ["validate-team", team_file, "--verbose"])
            assert result.exit_code == 0
            assert "✓ Team validation successful" in result.output
            assert "Team: Test Team" in result.output
            assert "Schema version: 2.0" in result.output
            assert "Agents: 2 (researcher, analyst)" in result.output
            assert "Workflows: 1 (test_workflow)" in result.output
            
        finally:
            Path(team_file).unlink()
    
    def test_validate_team_invalid_schema(self):
        """Test team validation with invalid schema."""
        invalid_team = """
schema_version: "2.0"

team:
  metadata:
    # Missing required id field
    name: "Invalid Team"
    
  composition:
    agents: {}  # Empty agents dict should fail validation
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_team)
            team_file = f.name
            
        try:
            result = runner.invoke(app, ["validate-team", team_file])
            assert result.exit_code == 1
            assert "✗ Team validation failed" in result.output
            assert "Validation Errors" in result.output
            
        finally:
            Path(team_file).unlink()
    
    def test_validate_team_wrong_schema_version(self):
        """Test team validation with wrong schema version."""
        wrong_schema = """
schema_version: "1.0"  # Should be 2.0 for teams

metadata:
  id: agt_individual_001  # This is individual agent schema
  name: "Individual Agent"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(wrong_schema)
            team_file = f.name
            
        try:
            result = runner.invoke(app, ["validate-team", team_file])
            assert result.exit_code == 1
            assert "✗ Team validation failed" in result.output
            
        finally:
            Path(team_file).unlink()
    
    def test_validate_team_nonexistent_file(self):
        """Test validate-team with nonexistent file."""
        result = runner.invoke(app, ["validate-team", "nonexistent.yaml"])
        assert result.exit_code == 1
        assert "File not found" in result.output
    
    def test_validate_team_invalid_yaml(self):
        """Test validate-team with invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            invalid_file = f.name
            
        try:
            result = runner.invoke(app, ["validate-team", invalid_file])
            assert result.exit_code == 1
            assert "Invalid YAML syntax" in result.output
            
        finally:
            Path(invalid_file).unlink()
    
    def test_validate_team_workflow_agent_validation(self):
        """Test that team validation catches workflow agents not in composition."""
        invalid_workflow_team = """
schema_version: "2.0"

team:
  metadata:
    id: team_invalid_001
    name: "Invalid Workflow Team"
    version: "1.0.0"
    created_at: "2026-02-18T00:00:00Z"
    
  composition:
    agents:
      researcher:
        agent_id: agt_researcher_001
        role: researcher
        authority_level: 3
        expertise_domains: ["research"]
        
  workflow_patterns:
    broken_workflow:
      description: "Workflow referencing nonexistent agent"
      stages:
        - stage: analysis
          primary_agent: nonexistent_agent  # This agent doesn't exist
          objective: "Do analysis"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_workflow_team)
            team_file = f.name
            
        try:
            result = runner.invoke(app, ["validate-team", team_file])
            assert result.exit_code == 1
            assert "✗ Team validation failed" in result.output
            assert "references unknown agent" in result.output
            
        finally:
            Path(team_file).unlink()


# ---------------------------------------------------------------------------
# Integration tests combining multiple commands
# ---------------------------------------------------------------------------

class TestCLIIntegration:
    """Test CLI commands working together."""
    
    def test_compile_then_analyze_roundtrip(self, sample_identity_yaml):
        """Test compiling to SOUL.md then analyzing it back."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_identity_yaml)
            yaml_file = f.name
            
        try:
            # First compile to SOUL.md
            compile_result = runner.invoke(app, [
                "compile", yaml_file, 
                "--target", "soul"
            ])
            assert compile_result.exit_code == 0
            
            # Check SOUL.md was created (default naming)
            soul_file = yaml_file.replace('.yaml', '.SOUL.md')
            assert Path(soul_file).exists()
            
            # Then analyze the generated SOUL.md
            analyze_result = runner.invoke(app, ["analyze", soul_file])
            assert analyze_result.exit_code == 0
            assert "Test Agent" in analyze_result.output
            
        finally:
            base_name = yaml_file.replace('.yaml', '')
            for file_to_clean in [yaml_file, f"{base_name}.SOUL.md", f"{base_name}.STYLE.md"]:
                try:
                    Path(file_to_clean).unlink()
                except FileNotFoundError:
                    pass
    
    def test_validate_then_analyze_workflow(self, sample_identity_yaml):
        """Test validating an identity then analyzing it."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_identity_yaml)
            yaml_file = f.name
            
        try:
            # First validate
            validate_result = runner.invoke(app, ["validate", yaml_file])
            assert validate_result.exit_code == 0
            assert "✓ Validation successful" in validate_result.output
            
            # Then analyze
            analyze_result = runner.invoke(app, ["analyze", yaml_file])
            assert analyze_result.exit_code == 0
            assert "Test Agent" in analyze_result.output
            
        finally:
            Path(yaml_file).unlink()