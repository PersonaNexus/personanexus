"""Tests for the identity evaluation harness."""

import json
from pathlib import Path

from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.evals import IdentityEvaluationHarness

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
