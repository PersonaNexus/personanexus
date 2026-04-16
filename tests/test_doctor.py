"""Tests for repo-wide doctor checks."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.doctor import PersonaDoctor

runner = CliRunner()


def _write_identity(path: Path, *, extends: str | None = None) -> None:
    extends_block = f'extends: "{extends}"\n' if extends else ""
    path.write_text(
        (
            'schema_version: "1.0"\n\n'
            f"{extends_block}"
            "metadata:\n"
            '  id: "agt_test_001"\n'
            '  name: "Test Agent"\n'
            '  version: "1.0.0"\n'
            '  description: "A test identity"\n'
            '  created_at: "2026-01-01T00:00:00Z"\n'
            '  updated_at: "2026-01-01T00:00:00Z"\n'
            '  status: "active"\n\n'
            "role:\n"
            '  title: "Assistant"\n'
            '  purpose: "Help users"\n'
            "  scope:\n"
            '    primary: ["general assistance"]\n\n'
            "personality:\n"
            "  traits:\n"
            "    warmth: 0.6\n"
            "    verbosity: 0.5\n\n"
            "communication:\n"
            "  tone:\n"
            '    default: "friendly"\n'
            "  language:\n"
            '    primary: "en"\n\n'
            "principles:\n"
            '  - id: "helpful"\n'
            "    priority: 1\n"
            '    statement: "Be helpful"\n\n'
            "guardrails:\n"
            "  hard:\n"
            '    - id: "no_harm"\n'
            '      rule: "Never produce harmful content"\n'
            '      enforcement: "output_filter"\n'
            '      severity: "critical"\n'
        ),
        encoding="utf-8",
    )


class TestPersonaDoctor:
    def test_discovers_repo_files(self, tmp_path):
        identities_dir = tmp_path / "identities"
        teams_dir = tmp_path / "teams"
        identities_dir.mkdir()
        teams_dir.mkdir()

        _write_identity(identities_dir / "agent.yaml")
        (teams_dir / "team.yaml").write_text(
            'schema_version: "2.0"\n\n'
            'team:\n'
            '  metadata:\n'
            '    id: "team_test_001"\n'
            '    name: "Test Team"\n'
            '    description: "A minimal valid team"\n'
            '    version: "1.0.0"\n'
            '    created_at: "2026-01-01T00:00:00Z"\n'
            '    author: "tests"\n'
            '  composition:\n'
            '    agents:\n'
            '      lead:\n'
            '        agent_id: "agt_test_001"\n'
            '        role: "assistant"\n'
            '        authority_level: 1\n'
            '        expertise_domains: ["general assistance"]\n'
            '        capabilities: ["answer questions"]\n'
            '        delegation_rights: []\n'
            '        personality_summary:\n'
            '          warmth: 0.6\n'
            '  governance:\n'
            '    model: "single_owner"\n'
            '    decision_rules: []\n',
            encoding="utf-8",
        )

        doctor = PersonaDoctor(root=tmp_path)
        report = doctor.run()

        assert report.ok is True
        assert report.summary.files_scanned == 2
        assert report.summary.identities_scanned == 1
        assert report.summary.teams_scanned == 1

    def test_compile_check_reports_missing_artifact(self, tmp_path):
        identity_path = tmp_path / "agent.yaml"
        _write_identity(identity_path)

        doctor = PersonaDoctor(root=tmp_path, check_compile=True)
        report = doctor.run()

        assert report.ok is False
        assert report.summary.error_count >= 1
        assert any(
            issue.kind == "compile_artifact_missing"
            for file in report.files
            for issue in file.issues
        )


class TestDoctorCommand:
    def test_doctor_examples_repo(self, tmp_path):
        _write_identity(tmp_path / "agent.yaml")

        result = runner.invoke(app, ["doctor", str(tmp_path)])

        assert result.exit_code == 0
        assert "PersonaNexus doctor: OK" in result.output

    def test_doctor_json_output(self, tmp_path):
        _write_identity(tmp_path / "agent.yaml")

        result = runner.invoke(app, ["doctor", str(tmp_path), "--format", "json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["summary"]["files_scanned"] == 1

    def test_doctor_reports_resolution_error(self, tmp_path):
        identities_dir = tmp_path / "identities"
        identities_dir.mkdir()
        _write_identity(identities_dir / "agent.yaml", extends="archetypes/missing")

        result = runner.invoke(app, ["doctor", str(tmp_path)])

        assert result.exit_code == 1
        assert "Cannot resolve reference" in result.output

    def test_doctor_requires_personanexus_files(self, tmp_path):
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")

        result = runner.invoke(app, ["doctor", str(tmp_path)])

        assert result.exit_code == 1
        assert "No PersonaNexus files found." in result.output
