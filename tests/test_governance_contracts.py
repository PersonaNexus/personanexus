import json
from pathlib import Path

from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.compiler import apply_task_mode_overlay, compile_identity, get_compile_warnings
from personanexus.evals import IdentityEvaluationHarness
from personanexus.resolver import IdentityResolver

runner = CliRunner()


def _identity_path(examples_dir: Path) -> Path:
    return examples_dir / "identities" / "high-trust-board-advisor.yaml"


def test_compile_includes_behavioral_contract_and_task_mode(examples_dir):
    resolver = IdentityResolver(search_paths=[examples_dir])
    identity = resolver.resolve_file(_identity_path(examples_dir))

    compiled = compile_identity(identity, target="json", task_mode="careful_operator")

    assert compiled["active_task_mode"] == "careful_operator"
    layer_names = [layer["name"] for layer in compiled["prompt_layers"]]
    assert "behavioral_contract" in layer_names


def test_task_mode_overlay_changes_effective_contract(examples_dir):
    resolver = IdentityResolver(search_paths=[examples_dir])
    identity = resolver.resolve_file(_identity_path(examples_dir))

    effective = apply_task_mode_overlay(identity, "research_analyst")

    assert effective.behavioral_contract is not None
    assert effective.behavioral_contract.confidentiality.value == "contextual"
    assert "Stay evidence-led and cite sources." in effective.behavioral_contract.notes


def test_provider_compile_warnings_surface_target_mismatch(examples_dir):
    resolver = IdentityResolver(search_paths=[examples_dir])
    identity = resolver.resolve_file(_identity_path(examples_dir))

    warnings = get_compile_warnings(identity, "text")

    assert any("governance-sensitive" in warning for warning in warnings)


def test_governance_eval_harness_respects_task_mode(examples_dir, tmp_path):
    suite_path = tmp_path / "governance-suite.yaml"
    suite_path.write_text(
        'version: "1"\n'
        'metadata: {name: "Governance contract suite"}\n'
        "defaults:\n"
        "  passing_score: 0.6\n"
        "scenarios:\n"
        "  - id: baseline_contract\n"
        "    assertions:\n"
        "      governance:\n"
        "        honesty: maximally_candid\n"
        "        confidentiality: strict\n"
        "        governance_sensitivity: high\n"
        "  - id: research_overlay\n"
        "    assertions:\n"
        "      governance:\n"
        "        confidentiality: contextual\n"
        "        boundary_strictness: moderate\n",
        encoding="utf-8",
    )

    harness = IdentityEvaluationHarness(search_paths=[examples_dir])
    identity_path = _identity_path(examples_dir)

    baseline = harness.evaluate(identity_path, suite_path)
    overlay = harness.evaluate(identity_path, suite_path, task_mode="research_analyst")

    assert baseline.task_mode is None
    assert baseline.scenarios[0].dimensions["governance"].score == 1.0
    assert baseline.scenarios[1].dimensions["governance"].score < 1.0
    assert overlay.task_mode == "research_analyst"
    assert overlay.scenarios[1].dimensions["governance"].score == 1.0


def test_eval_cli_json_includes_task_mode(examples_dir, tmp_path):
    suite_path = tmp_path / "governance-suite.yaml"
    suite_path.write_text(
        (
            'version: "1"\n'
            "scenarios:\n"
            "  - id: contract\n"
            "    assertions:\n"
            "      governance:\n"
            "        confidentiality: contextual\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "eval",
            str(_identity_path(examples_dir)),
            str(suite_path),
            "--search-path",
            str(examples_dir),
            "--task-mode",
            "research_analyst",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["task_mode"] == "research_analyst"


def test_compile_cli_prints_governance_warning(examples_dir, tmp_path):
    output = tmp_path / "compiled.md"
    result = runner.invoke(
        app,
        [
            "compile",
            str(_identity_path(examples_dir)),
            "--search-path",
            str(examples_dir),
            "--target",
            "text",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Warning:" in result.output
    assert output.exists()


def test_governance_eval_fails_missing_behavioral_contract_with_check(examples_dir, tmp_path):
    suite_path = tmp_path / "governance-suite.yaml"
    suite_path.write_text(
        (
            'version: "1"\n'
            "scenarios:\n"
            "  - id: contract_required\n"
            "    assertions:\n"
            "      governance:\n"
            "        confidentiality: strict\n"
        ),
        encoding="utf-8",
    )

    harness = IdentityEvaluationHarness(search_paths=[examples_dir])
    result = harness.evaluate(examples_dir / "identities" / "minimal.yaml", suite_path)

    governance = result.scenarios[0].dimensions["governance"]
    assert governance.score == 0.0
    assert governance.checks[0].label == "behavioral_contract_present"
    assert governance.checks[0].passed is False

