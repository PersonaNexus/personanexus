"""Tests for the CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from personanexus.cli import app

runner = CliRunner()


class TestValidateCommand:
    def test_validate_valid_file(self, ada_path):
        result = runner.invoke(app, ["validate", str(ada_path)])
        assert result.exit_code == 0
        assert "Validation successful" in result.output

    def test_validate_minimal_file(self, minimal_path):
        result = runner.invoke(app, ["validate", str(minimal_path)])
        assert result.exit_code == 0

    def test_validate_nonexistent_file(self):
        result = runner.invoke(app, ["validate", "/nonexistent.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_validate_invalid_yaml(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: valid: yaml: [")
        result = runner.invoke(app, ["validate", str(bad_file)])
        assert result.exit_code == 1

    def test_validate_missing_fields(self, tmp_path):
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text('schema_version: "1.0"\nmetadata:\n  id: agt_test\n')
        result = runner.invoke(app, ["validate", str(incomplete)])
        assert result.exit_code == 1

    def test_validate_verbose(self, ada_path):
        result = runner.invoke(app, ["validate", str(ada_path), "--verbose"])
        assert result.exit_code == 0
        assert "Ada" in result.output

    def test_validate_all_examples(self, examples_dir):
        for path in examples_dir.rglob("*.yaml"):
            # Skip team definitions (different schema, not individual agents)
            if "teams" in path.parts:
                continue
            result = runner.invoke(app, ["validate", str(path)])
            assert result.exit_code == 0, f"{path.name} failed: {result.output}"


class TestResolveCommand:
    def test_resolve_minimal(self, minimal_path):
        result = runner.invoke(app, ["resolve", str(minimal_path)])
        assert result.exit_code == 0
        assert "Helper" in result.output

    def test_resolve_ada_with_search_path(self, ada_path, examples_dir):
        result = runner.invoke(
            app, ["resolve", str(ada_path), "--search-path", str(examples_dir)]
        )
        assert result.exit_code == 0
        assert "Ada" in result.output

    def test_resolve_json_output(self, minimal_path):
        result = runner.invoke(app, ["resolve", str(minimal_path), "--output", "json"])
        assert result.exit_code == 0
        assert '"name": "Helper"' in result.output

    def test_resolve_nonexistent(self):
        result = runner.invoke(app, ["resolve", "/nonexistent.yaml"])
        assert result.exit_code == 1


class TestInitCommand:
    def test_init_minimal(self, tmp_path):
        result = runner.invoke(
            app, ["init", "MyBot", "--type", "minimal", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output

        # Verify the file exists and is valid
        created_file = tmp_path / "mybot.yaml"
        assert created_file.exists()

        # Validate the created file
        validate_result = runner.invoke(app, ["validate", str(created_file)])
        assert validate_result.exit_code == 0

    def test_init_full(self, tmp_path):
        result = runner.invoke(
            app, ["init", "FullBot", "--type", "full", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        created_file = tmp_path / "fullbot.yaml"
        assert created_file.exists()

        validate_result = runner.invoke(app, ["validate", str(created_file)])
        assert validate_result.exit_code == 0

    def test_init_archetype(self, tmp_path):
        result = runner.invoke(
            app, ["init", "BaseAnalyst", "--type", "archetype", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 0

    def test_init_mixin(self, tmp_path):
        result = runner.invoke(
            app, ["init", "Formal", "--type", "mixin", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 0

    def test_init_with_extends(self, tmp_path):
        result = runner.invoke(
            app,
            [
                "init",
                "MyAnalyst",
                "--type",
                "minimal",
                "--output-dir",
                str(tmp_path),
                "--extends",
                "archetypes/analyst",
            ],
        )
        assert result.exit_code == 0
        content = (tmp_path / "myanalyst.yaml").read_text()
        assert "extends:" in content

    def test_init_invalid_type(self, tmp_path):
        result = runner.invoke(
            app, ["init", "Bad", "--type", "invalid", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 1


class TestMigrateCommand:
    def test_migrate_same_version(self, ada_path):
        result = runner.invoke(app, ["migrate", "1.0", "1.0", str(ada_path)])
        assert result.exit_code == 0
        assert "already" in result.output.lower()

    def test_migrate_unsupported_version(self, ada_path):
        result = runner.invoke(app, ["migrate", "1.0", "2.0", str(ada_path)])
        assert result.exit_code == 0  # Just shows info panel
        assert "not yet implemented" in result.output.lower()


class TestDiffCommand:
    def test_diff_identical(self, ada_path):
        result = runner.invoke(app, ["diff", str(ada_path), str(ada_path)])
        assert result.exit_code == 0
        assert "CHANGED FIELDS: (none)" in result.output

    def test_diff_different(self, ada_path, ada_ocean_path):
        result = runner.invoke(app, ["diff", str(ada_path), str(ada_ocean_path)])
        assert result.exit_code == 0
        assert "IDENTITY DIFF REPORT" in result.output

    def test_diff_json_format(self, ada_path, ada_ocean_path):
        result = runner.invoke(app, ["diff", str(ada_path), str(ada_ocean_path), "--format", "json"])
        assert result.exit_code == 0
        assert '"changed_fields"' in result.output

    def test_diff_markdown_format(self, ada_path, ada_ocean_path):
        result = runner.invoke(app, ["diff", str(ada_path), str(ada_ocean_path), "--format", "markdown"])
        assert result.exit_code == 0
        assert "IDENTITY DIFF" in result.output or "REPORT" in result.output

    def test_diff_nonexistent(self):
        result = runner.invoke(app, ["diff", "/nonexistent1.yaml", "/nonexistent2.yaml"])
        assert result.exit_code == 1


class TestCompatCommand:
    def test_compat_same_identity(self, ada_path):
        result = runner.invoke(app, ["compat", str(ada_path), str(ada_path)])
        assert result.exit_code == 0
        assert "100.0%" in result.output

    def test_compat_different_ocean(self, ada_ocean_path, ada_disc_path):
        result = runner.invoke(app, ["compat", str(ada_ocean_path), str(ada_disc_path)])
        assert result.exit_code == 0
        assert "Compatibility Score" in result.output

    def test_compat_nonexistent(self):
        result = runner.invoke(app, ["compat", "/nonexistent1.yaml", "/nonexistent2.yaml"])
        assert result.exit_code == 1
