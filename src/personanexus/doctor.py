"""Repo-wide health checks for PersonaNexus projects."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from personanexus.compiler import compile_identity
from personanexus.linter import IdentityLinter
from personanexus.parser import IdentityParser, ParseError
from personanexus.resolver import IdentityResolver, ResolutionError
from personanexus.team_types import TeamConfiguration
from personanexus.validator import IdentityValidator, ValidationWarning

_FILE_KINDS = ("identity", "team")
_IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}


@dataclasses.dataclass
class DoctorIssue:
    kind: str
    severity: Literal["error", "warning", "info"]
    message: str
    check: str
    path: str | None = None


@dataclasses.dataclass
class DoctorFileReport:
    path: str
    kind: Literal["identity", "team"]
    blocking: bool = False
    issues: list[DoctorIssue] = dataclasses.field(default_factory=list)

    def add_issue(
        self,
        *,
        kind: str,
        severity: Literal["error", "warning", "info"],
        message: str,
        check: str,
        path: str | None = None,
    ) -> None:
        self.issues.append(
            DoctorIssue(
                kind=kind,
                severity=severity,
                message=message,
                check=check,
                path=path,
            )
        )
        if severity == "error":
            self.blocking = True

    def summary_counts(self) -> dict[str, int]:
        counts = {"error": 0, "warning": 0, "info": 0}
        for issue in self.issues:
            counts[issue.severity] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "blocking": self.blocking,
            "issues": [dataclasses.asdict(issue) for issue in self.issues],
            "summary": self.summary_counts(),
        }


@dataclasses.dataclass
class DoctorSummary:
    root: str
    files_scanned: int
    identities_scanned: int
    teams_scanned: int
    blocking_files: int
    error_count: int
    warning_count: int
    info_count: int

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class DoctorReport:
    ok: bool
    summary: DoctorSummary
    files: list[DoctorFileReport]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "summary": self.summary.to_dict(),
            "files": [file.to_dict() for file in self.files],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class PersonaDoctor:
    """Run pragmatic repo-wide health checks for PersonaNexus files."""

    def __init__(
        self,
        *,
        root: str | Path,
        search_paths: list[str | Path] | None = None,
        check_compile: bool = False,
        compile_targets: list[str] | None = None,
        token_budget: int = 3000,
    ) -> None:
        self.root = Path(root).resolve()
        self.search_paths = [self.root, *(Path(p) for p in (search_paths or []))]
        self.check_compile = check_compile
        self.compile_targets = compile_targets or ["text"]
        self.token_budget = token_budget
        self.parser = IdentityParser()
        self.validator = IdentityValidator()
        self.linter = IdentityLinter()
        self.resolver = IdentityResolver(search_paths=self.search_paths)

    def run(self) -> DoctorReport:
        files = self.discover_files()
        reports = [self._check_file(path) for path in files]

        error_count = sum(
            1 for report in reports for issue in report.issues if issue.severity == "error"
        )
        warning_count = sum(
            1 for report in reports for issue in report.issues if issue.severity == "warning"
        )
        info_count = sum(
            1 for report in reports for issue in report.issues if issue.severity == "info"
        )
        blocking_files = sum(1 for report in reports if report.blocking)
        identities_scanned = sum(1 for report in reports if report.kind == "identity")
        teams_scanned = sum(1 for report in reports if report.kind == "team")

        summary = DoctorSummary(
            root=str(self.root),
            files_scanned=len(reports),
            identities_scanned=identities_scanned,
            teams_scanned=teams_scanned,
            blocking_files=blocking_files,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
        )
        return DoctorReport(ok=blocking_files == 0, summary=summary, files=reports)

    def discover_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.root.rglob("*"):
            if path.is_dir() and path.name in _IGNORED_DIRS:
                continue
            if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml"}:
                continue
            if any(part in _IGNORED_DIRS for part in path.parts):
                continue
            kind = self._detect_kind(path)
            if kind in _FILE_KINDS:
                files.append(path)
        return sorted(files)

    def _detect_kind(self, path: Path) -> str | None:
        if not _looks_like_personanexus_file(path):
            return None

        try:
            data = self.parser.parse_file(path)
        except ParseError:
            return "identity"

        schema_version = str(data.get("schema_version", "")).strip()
        if "team" in data or schema_version.startswith("2"):
            return "team"
        if "metadata" in data and "role" in data and "personality" in data:
            return "identity"
        return None

    def _check_file(self, path: Path) -> DoctorFileReport:
        kind = self._detect_kind(path)
        if kind == "team":
            return self._check_team(path)
        return self._check_identity(path)

    def _check_identity(self, path: Path) -> DoctorFileReport:
        report = DoctorFileReport(path=self._relative_path(path), kind="identity")

        validation = self.validator.validate_file(path)
        if validation.errors:
            for error in validation.errors:
                report.add_issue(
                    kind="validation_error",
                    severity="error",
                    message=error,
                    check="validate",
                )
            return report

        for warning in validation.warnings:
            report.add_issue(
                kind=warning.type,
                severity=_validation_warning_severity(warning),
                message=warning.message,
                check="validate",
                path=warning.path,
            )

        lint_warnings = self.linter.lint_file(str(path))
        for warning in lint_warnings:
            report.add_issue(
                kind=warning.rule,
                severity=warning.severity,
                message=warning.message,
                check="lint",
                path=warning.path,
            )

        try:
            identity = self.resolver.resolve_file(path)
        except (ParseError, ResolutionError) as exc:
            report.add_issue(
                kind="resolution_error",
                severity="error",
                message=str(exc),
                check="resolve",
            )
            return report
        except ValidationError as exc:
            for error in exc.errors():
                loc = " -> ".join(str(part) for part in error["loc"])
                report.add_issue(
                    kind="resolution_validation_error",
                    severity="error",
                    message=f"{loc}: {error['msg']}",
                    check="resolve",
                )
            return report

        if self.check_compile:
            self._check_compile_artifacts(path, identity, report)

        return report

    def _check_team(self, path: Path) -> DoctorFileReport:
        report = DoctorFileReport(path=self._relative_path(path), kind="team")
        try:
            data = self.parser.parse_file(path)
            TeamConfiguration.model_validate(data)
        except (ParseError, ValidationError) as exc:
            if isinstance(exc, ValidationError):
                for error in exc.errors():
                    loc = " -> ".join(str(part) for part in error["loc"])
                    report.add_issue(
                        kind="team_validation_error",
                        severity="error",
                        message=f"{loc}: {error['msg']}",
                        check="validate-team",
                    )
                return report
            report.add_issue(
                kind="team_validation_error",
                severity="error",
                message=str(exc),
                check="validate-team",
            )
            return report

        return report

    def _check_compile_artifacts(self, path: Path, identity: Any, report: DoctorFileReport) -> None:
        for target in self.compile_targets:
            expected_outputs = _expected_compile_outputs(path, target)
            try:
                compiled = compile_identity(identity, target=target, token_budget=self.token_budget)
            except Exception as exc:
                report.add_issue(
                    kind="compile_error",
                    severity="error",
                    message=f"{target}: {exc}",
                    check="compile",
                )
                continue

            actual_outputs = _normalize_compile_outputs(compiled)
            for expected_path, expected_content in zip(
                expected_outputs, actual_outputs, strict=True
            ):
                if not expected_path.exists():
                    report.add_issue(
                        kind="compile_artifact_missing",
                        severity="error",
                        message=(
                            f"Missing compiled artifact for target '{target}': "
                            f"{self._relative_path(expected_path)}"
                        ),
                        check="compile",
                    )
                    continue
                current_content = expected_path.read_text(encoding="utf-8")
                if current_content != expected_content:
                    report.add_issue(
                        kind="compile_drift",
                        severity="error",
                        message=(
                            f"Compiled artifact drift for target '{target}': "
                            f"{self._relative_path(expected_path)} is stale"
                        ),
                        check="compile",
                    )

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.root))
        except ValueError:
            return str(path)


def _looks_like_personanexus_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False

    markers = ("schema_version:", "metadata:", "personality:", "team:")
    return any(marker in text for marker in markers)


def _normalize_compile_outputs(compiled: str | dict[str, Any]) -> list[str]:
    if isinstance(compiled, dict):
        if {"soul_md", "style_md"} <= set(compiled):
            return [str(compiled["soul_md"]), str(compiled["style_md"])]
        return [json.dumps(compiled, indent=2, ensure_ascii=False)]
    return [compiled]


def _expected_compile_outputs(path: Path, target: str) -> list[Path]:
    stem = path.stem
    parent = path.parent
    ext_map = {
        "text": f"{stem}.compiled.md",
        "anthropic": f"{stem}.compiled.anthropic.md",
        "openai": f"{stem}.compiled.openai.md",
        "openclaw": f"{stem}.personality.json",
        "json": f"{stem}.compiled.json",
        "langchain": f"{stem}.langchain.json",
        "crewai": f"{stem}.crewai.yaml",
        "autogen": f"{stem}.autogen.json",
        "markdown": f"{stem}.compiled.doc.md",
        "soul": None,
    }
    if target not in ext_map:
        raise ValueError(f"Unsupported compile target: {target}")
    if target == "soul":
        return [parent / f"{stem}.SOUL.md", parent / f"{stem}.STYLE.md"]
    filename = ext_map[target]
    if filename is None:
        raise ValueError(f"Unexpected compile target: {target}")
    return [parent / filename]


def _validation_warning_severity(warning: ValidationWarning) -> Literal["warning", "info"]:
    if warning.severity == "high":
        return "warning"
    return "info"


def render_doctor_report(report: DoctorReport) -> str:
    lines = [f"PersonaNexus doctor: {'OK' if report.ok else 'ISSUES FOUND'}", ""]
    summary = report.summary
    lines.extend(
        [
            f"Root: {summary.root}",
            (
                "Scanned "
                f"{summary.files_scanned} file(s) "
                f"({summary.identities_scanned} identities, {summary.teams_scanned} teams)"
            ),
            (
                "Findings: "
                f"{summary.error_count} error(s), "
                f"{summary.warning_count} warning(s), "
                f"{summary.info_count} info finding(s)"
            ),
            "",
        ]
    )

    if not report.files:
        lines.append("No PersonaNexus files found.")
        return "\n".join(lines)

    for file_report in report.files:
        counts = file_report.summary_counts()
        status = "FAIL" if file_report.blocking else "OK"
        lines.append(
            f"[{status}] {file_report.path} ({file_report.kind})"
            f" - {counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} info"
        )
        for issue in file_report.issues:
            location = f" ({issue.path})" if issue.path else ""
            lines.append(
                "  - "
                f"{issue.severity.upper()} [{issue.check}:{issue.kind}]"
                f"{location}: {issue.message}"
            )
        lines.append("")

    return "\n".join(lines).rstrip()
