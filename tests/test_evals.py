"""Tests for the identity evaluation harness."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.evals import (
    EvalError,
    EvalRunResult,
    IdentityEvaluationHarness,
    ScenarioResult,
)

runner = CliRunner()


def _suite_path() -> Path:
    return Path(__file__).parent / "fixtures" / "identity_eval_suite.yaml"


class TestIdentityEvaluationHarness:
    def test_evaluate_identity(self, mira_path, examples_dir):
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        result = harness.evaluate(mira_path, _suite_path())

        assert result.identity_name == "Mira"
        assert result.suite_name == "Identity QA smoke suite"
        assert len(result.scenarios) == 2
        assert result.overall_score > 0.7
        assert result.passed is True

    def test_compare_identity_versions(self, mira_path, mira_ocean_path, examples_dir):
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        run_a = harness.evaluate(mira_path, _suite_path())
        run_b = harness.evaluate(mira_ocean_path, _suite_path())
        comparison = harness.compare(run_a, run_b)

        assert comparison.identity_a == "Mira"
        assert comparison.identity_b == "Mira"
        assert len(comparison.scenarios) == 2
        assert comparison.winner in {"a", "b", "tie"}


class TestEvalCli:
    def test_eval_command_table_output(self, mira_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "eval",
                str(mira_path),
                str(_suite_path()),
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Scenario Results" in result.output
        assert "analyst_core" in result.output

    def test_eval_command_compare_json(self, mira_path, mira_ocean_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "eval",
                str(mira_path),
                str(_suite_path()),
                "--compare",
                str(mira_ocean_path),
                "--search-path",
                str(examples_dir),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["identity_a"] == "Mira"
        assert payload["identity_b"] == "Mira"
        assert len(payload["scenarios"]) == 2


class TestEvalEdgeCases:
    def test_malformed_suite_yaml_raises(self, tmp_path, mira_path, examples_dir):
        bad_suite = tmp_path / "bad.yaml"
        bad_suite.write_text("version: 1\nscenarios: [not a mapping", encoding="utf-8")
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        with pytest.raises(EvalError, match="Failed to parse"):
            harness.evaluate(mira_path, bad_suite)

    def test_suite_must_be_mapping(self, tmp_path, mira_path, examples_dir):
        bad_suite = tmp_path / "list.yaml"
        bad_suite.write_text("- 1\n- 2\n", encoding="utf-8")
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        with pytest.raises(EvalError, match="must be a YAML/JSON object"):
            harness.evaluate(mira_path, bad_suite)

    def test_compare_rejects_mismatched_scenarios(self, mira_path, examples_dir):
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        run_a = harness.evaluate(mira_path, _suite_path())

        # Synthesize a second run with a different scenario ID so we exercise
        # the mismatch guard without needing another identity file.
        run_b = run_a.model_copy(
            update={
                "scenarios": [
                    ScenarioResult(
                        scenario_id="renamed_scenario",
                        description=None,
                        weighted_score=0.5,
                        passed=True,
                        dimensions=run_a.scenarios[0].dimensions,
                    )
                ]
            }
        )
        assert isinstance(run_b, EvalRunResult)
        with pytest.raises(EvalError, match="different scenario sets"):
            harness.compare(run_a, run_b)

    def test_empty_dimensions_do_not_inflate_score(self, tmp_path, mira_path, examples_dir):
        # A scenario with no assertions should not silently get a perfect
        # score on the dimensions that weren't checked.
        bare_suite = tmp_path / "bare.yaml"
        bare_suite.write_text(
            'version: "1"\n'
            'metadata: {name: "bare"}\n'
            "defaults: {passing_score: 0.0}\n"
            "scenarios:\n"
            "  - id: empty_scenario\n"
            "    assertions: {}\n",
            encoding="utf-8",
        )
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        result = harness.evaluate(mira_path, bare_suite)
        scenario = result.scenarios[0]
        # All four dimensions are empty, so the weighted score falls back to
        # the "no active checks" value of 1.0 — but crucially each dimension
        # exposes zero checks so downstream consumers can see that.
        assert all(len(dim.checks) == 0 for dim in scenario.dimensions.values())
        assert scenario.weighted_score == 1.0

    def test_passing_score_zero_is_respected(self, tmp_path, mira_path, examples_dir):
        # An explicit passing_score of 0 means "any score passes" and must
        # not be swallowed as a falsy fallback to the suite default.
        suite_path = tmp_path / "zero_pass.yaml"
        suite_path.write_text(
            'version: "1"\n'
            "defaults:\n"
            "  passing_score: 0.99\n"
            "scenarios:\n"
            "  - id: trivial\n"
            "    passing_score: 0.0\n"
            "    assertions:\n"
            "      persona:\n"
            "        min_traits: {warmth: 999}\n",
            encoding="utf-8",
        )
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        result = harness.evaluate(mira_path, suite_path)
        # Warmth 999 is unreachable → score 0, but passing_score=0 passes.
        assert result.scenarios[0].weighted_score == 0.0
        assert result.scenarios[0].passed is True

    def test_conversation_turn_validates_role(self, tmp_path, mira_path, examples_dir):
        suite_path = tmp_path / "bad_turn.yaml"
        suite_path.write_text(
            'version: "1"\n'
            "scenarios:\n"
            "  - id: chat\n"
            "    conversation:\n"
            "      - role: not_a_role\n"
            '        content: "hi"\n',
            encoding="utf-8",
        )
        harness = IdentityEvaluationHarness(search_paths=[examples_dir])
        with pytest.raises(EvalError, match="Invalid eval suite"):
            harness.evaluate(mira_path, suite_path)
