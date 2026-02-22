"""Tests for the YAML parser."""

import pytest

from personanexus.parser import IdentityParser, ParseError


@pytest.fixture
def parser():
    return IdentityParser()


class TestParseYaml:
    def test_valid_yaml(self, parser):
        result = parser.parse_yaml("key: value\nlist:\n  - a\n  - b")
        assert result["key"] == "value"
        assert result["list"] == ["a", "b"]

    def test_invalid_yaml(self, parser):
        with pytest.raises(ParseError) as exc_info:
            parser.parse_yaml("key: [unclosed", source="test.yaml")
        assert "test.yaml" in str(exc_info.value)

    def test_non_mapping_rejected(self, parser):
        with pytest.raises(ParseError, match="mapping"):
            parser.parse_yaml("- just\n- a\n- list")

    def test_empty_yaml(self, parser):
        with pytest.raises(ParseError, match="mapping"):
            parser.parse_yaml("")

    def test_source_in_error(self, parser):
        with pytest.raises(ParseError) as exc_info:
            parser.parse_yaml("{bad: [yaml", source="myfile.yaml")
        assert "myfile.yaml" in str(exc_info.value)


class TestParseFile:
    def test_file_not_found(self, parser):
        with pytest.raises(ParseError, match="not found"):
            parser.parse_file("/nonexistent/file.yaml")

    def test_directory_rejected(self, parser, tmp_path):
        with pytest.raises(ParseError, match="Not a file"):
            parser.parse_file(tmp_path)

    def test_valid_file(self, parser, mira_path):
        data = parser.parse_file(mira_path)
        assert data["schema_version"] == "1.0"
        assert data["metadata"]["name"] == "Mira"

    def test_all_example_files_parse(self, parser, examples_dir):
        yaml_files = list(examples_dir.rglob("*.yaml"))
        assert len(yaml_files) >= 7, "Expected at least 7 example files"

        for path in yaml_files:
            data = parser.parse_file(path)
            assert isinstance(data, dict), f"{path} did not parse to a dict"
            assert "schema_version" in data, f"{path} missing schema_version"


class TestLoadIdentity:
    def test_load_ada(self, parser, mira_path):
        identity = parser.load_identity(mira_path)
        assert identity.metadata.name == "Mira"
        assert identity.metadata.id == "agt_mira_001"
        assert identity.personality.traits.rigor == 0.9

    def test_load_minimal(self, parser, minimal_path):
        identity = parser.load_identity(minimal_path)
        assert identity.metadata.name == "Pip"
        assert len(identity.principles) >= 1
        assert len(identity.guardrails.hard) >= 1

    def test_load_from_string(self, parser):
        yaml_str = """
schema_version: "1.0"
metadata:
  id: agt_inline_test
  name: Inline
  version: "1.0.0"
  description: Test
  created_at: "2026-01-01T00:00:00Z"
  updated_at: "2026-01-01T00:00:00Z"
  status: draft
role:
  title: Tester
  purpose: Test
  scope:
    primary: ["testing"]
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
    statement: Be good
guardrails:
  hard:
    - id: no_harm
      rule: No harm
      enforcement: output_filter
      severity: critical
"""
        identity = parser.load_identity_from_string(yaml_str)
        assert identity.metadata.name == "Inline"
