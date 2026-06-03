"""Tests for compiled-prompt diff mode (issue #25)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.diff import (
    _SUPPORTED_COMPILE_TARGETS,
    diff_compiled_prompts,
    format_compiled_diff,
)


def _minimal_identity(name: str, warmth: float, directness: float = 0.5) -> dict:
    """Build a self-contained identity dict for compile-diff tests."""
    return {
        "schema_version": "1.0",
        "metadata": {
            "id": f"agt_{name.lower()}_001",
            "name": name,
            "version": "1.0.0",
            "description": "Test identity for compiled-diff coverage",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "active",
        },
        "role": {
            "title": "Helper",
            "purpose": "Assist with tests",
            "scope": {"primary": ["testing"]},
        },
        "personality": {
            "traits": {
                "warmth": warmth,
                "directness": directness,
                "verbosity": 0.5,
            },
        },
        "communication": {
            "tone": {"default": "neutral"},
            "language": {"primary": "en"},
        },
        "principles": [
            {
                "id": "be_helpful",
                "priority": 1,
                "statement": "Always prioritize being genuinely helpful",
            }
        ],
        "guardrails": {
            "hard": [
                {
                    "id": "no_harmful_content",
                    "rule": "Never generate harmful content",
                    "enforcement": "output_filter",
                    "severity": "critical",
                }
            ]
        },
    }


@pytest.fixture
def two_identities(tmp_path: Path) -> tuple[Path, Path]:
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text(yaml.safe_dump(_minimal_identity("Alpha", warmth=0.2)))
    b.write_text(yaml.safe_dump(_minimal_identity("Beta", warmth=0.9, directness=0.9)))
    return a, b


@pytest.fixture
def same_identity_twice(tmp_path: Path) -> tuple[Path, Path]:
    payload = yaml.safe_dump(_minimal_identity("Alpha", warmth=0.2))
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text(payload)
    b.write_text(payload)
    return a, b


class TestDiffCompiledPrompts:
    def test_supported_targets_include_text_and_anthropic(self):
        assert "text" in _SUPPORTED_COMPILE_TARGETS
        assert "anthropic" in _SUPPORTED_COMPILE_TARGETS

    def test_default_target_is_text(self, two_identities):
        a, b = two_identities
        result = diff_compiled_prompts(str(a), str(b))
        assert "text" in result["targets"]
        entry = result["targets"]["text"]
        assert entry["error"] is None
        assert entry["identical"] is False
        assert entry["unified_diff"]
        # Both sides should have non-empty compiled output.
        assert entry["left"]
        assert entry["right"]

    def test_identical_inputs_are_marked_identical(self, same_identity_twice):
        a, b = same_identity_twice
        result = diff_compiled_prompts(str(a), str(b), targets=["text"])
        assert result["targets"]["text"]["identical"] is True
        assert result["targets"]["text"]["unified_diff"] == ""

    def test_multiple_targets(self, two_identities):
        a, b = two_identities
        result = diff_compiled_prompts(str(a), str(b), targets=["text", "anthropic", "openclaw"])
        assert set(result["targets"].keys()) == {"text", "anthropic", "openclaw"}
        for tgt in ("text", "anthropic", "openclaw"):
            assert result["targets"][tgt]["error"] is None

    def test_unsupported_target_raises(self, two_identities):
        a, b = two_identities
        with pytest.raises(ValueError, match="Unsupported compile target"):
            diff_compiled_prompts(str(a), str(b), targets=["not-a-real-target"])

    def test_likely_drivers_surface_personality_changes(self, two_identities):
        a, b = two_identities
        result = diff_compiled_prompts(str(a), str(b))
        drivers = result["likely_drivers"]
        # metadata.name differs and personality traits differ.
        all_fields = [f for fields in drivers.values() for f in fields]
        assert any("personality.traits" in f for f in all_fields)
        assert any("metadata.name" in f for f in all_fields)

    def test_identity_diff_is_embedded(self, two_identities):
        a, b = two_identities
        result = diff_compiled_prompts(str(a), str(b))
        assert "changed_fields" in result["identity_diff"]
        assert result["identity_diff"]["changed_fields"]


class TestFormatCompiledDiff:
    def test_text_format(self, two_identities):
        a, b = two_identities
        result = diff_compiled_prompts(str(a), str(b))
        out = format_compiled_diff(result, fmt="text")
        assert "COMPILED PROMPT DIFF REPORT" in out
        assert "Target: text" in out
        assert "LIKELY DRIVERS" in out

    def test_markdown_format(self, two_identities):
        a, b = two_identities
        result = diff_compiled_prompts(str(a), str(b))
        out = format_compiled_diff(result, fmt="markdown")
        assert "# Compiled Prompt Diff Report" in out
        assert "## Target: `text`" in out
        assert "```diff" in out

    def test_json_format_is_valid_json(self, two_identities):
        a, b = two_identities
        result = diff_compiled_prompts(str(a), str(b))
        out = format_compiled_diff(result, fmt="json")
        parsed = json.loads(out)
        assert "targets" in parsed
        assert "likely_drivers" in parsed

    def test_identical_text_format_notes_match(self, same_identity_twice):
        a, b = same_identity_twice
        result = diff_compiled_prompts(str(a), str(b))
        out = format_compiled_diff(result, fmt="text")
        assert "identical" in out.lower()


class TestDiffCliCompiledFlag:
    def test_cli_compiled_flag(self, two_identities):
        a, b = two_identities
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["diff", str(a), str(b), "--compiled", "--target", "text,anthropic"],
        )
        assert result.exit_code == 0, result.output
        assert "Target: text" in result.output
        assert "Target: anthropic" in result.output

    def test_cli_compiled_json_format(self, two_identities):
        a, b = two_identities
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "diff",
                str(a),
                str(b),
                "--compiled",
                "--target",
                "text",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        # Output is rendered through rich's print_json; parse with relaxed bounds.
        # Just confirm 'targets' key appears.
        assert "targets" in result.output

    def test_cli_default_still_identity_diff(self, two_identities):
        a, b = two_identities
        runner = CliRunner()
        result = runner.invoke(app, ["diff", str(a), str(b)])
        assert result.exit_code == 0, result.output
        assert "IDENTITY DIFF REPORT" in result.output
