"""Repo-wide health checks for PersonaNexus projects."""

from __future__ import annotations

import dataclasses
import json
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from personanexus.compiler import compile_identity
from personanexus.linter import IdentityLinter
from personanexus.parser import IdentityParser, ParseError
from personanexus.resolver import IdentityResolver, ResolutionError
from personanexus.team_types import TeamConfiguration
from personanexus.validator import IdentityValidator, ValidationWarning

# Exit codes used by the `doctor` CLI.
EXIT_OK = 0
EXIT_ISSUES = 1
EXIT_NO_FILES = 2

# Compile targets understood by `_expected_compile_outputs`. The CLI imports
# this so the allowed --target values stay in sync with what the doctor can
# actually verify on disk.
SUPPORTED_COMPILE_TARGETS: tuple[str, ...] = (
    "text",
    "anthropic",
    "openai",
    "openclaw",
    "soul",
    "json",
    "langchain",
    "crewai",
    "autogen",
    "markdown",
)

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

_MARKERS = ("schema_version:", "metadata:", "personality:", "team:")
_TEAM_MARKER_RE = re.compile(r"(?m)^team:\s*$")


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


@dataclasses.dataclass
class _Discovered:
    path: Path
    kind: Literal["identity", "team"]
    # Parsed YAML payload, or None if the file failed to parse (identity path
    # will surface the ParseError through the validator).
    data: dict[str, Any] | None


class PersonaDoctor:
    """Run pragmatic repo-wide health checks for PersonaNexus files."""

    def __init__(
        self,
        *,
        root: str | Path,
        search_paths: Sequence[str | Path] | None = None,
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
        discovered = self._discover()
        reports = [self._check_file(item) for item in discovered]

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
        """Public helper kept for backwards compatibility."""
        return [item.path for item in self._discover()]

    def _discover(self) -> list[_Discovered]:
        """Walk the tree once, skipping ignored dirs, and classify each file."""
        found: list[_Discovered] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            # Prune ignored directories in-place so os.walk doesn't recurse
            # into them (saves a lot of I/O on large repos).
            dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS]
            for filename in filenames:
                if not filename.lower().endswith((".yaml", ".yml")):
                    continue
                path = Path(dirpath) / filename
                classified = self._classify(path)
                if classified is not None:
                    found.append(classified)
        found.sort(key=lambda item: item.path)
        return found

    def _classify(self, path: Path) -> _Discovered | None:
        """Read a file once and decide whether it's an identity or team."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        if not any(marker in text for marker in _MARKERS):
            return None

        try:
            data = self.parser.parse_file(path)
        except ParseError:
            # Fall back to textual heuristics so a malformed team file isn't
            # silently reported as an identity with a misleading error.
            kind: Literal["identity", "team"] = (
                "team" if _TEAM_MARKER_RE.search(text) else "identity"
            )
            return _Discovered(path=path, kind=kind, data=None)

        if not isinstance(data, dict):
            return None

        schema_version = str(data.get("schema_version", "")).strip()
        if "team" in data or schema_version.startswith("2"):
            return _Discovered(path=path, kind="team", data=data)
        if "metadata" in data and "role" in data and "personality" in data:
            return _Discovered(path=path, kind="identity", data=data)
        return None

    def _check_file(self, item: _Discovered) -> DoctorFileReport:
        if item.kind == "team":
            return self._check_team(item)
        return self._check_identity(item)

    def _check_identity(self, item: _Discovered) -> DoctorFileReport:
        path = item.path
        report = DoctorFileReport(path=self._relative_path(path), kind="identity")

        validation = self.validator.validate_file(path)
        if validation.errors:
            for error_message in validation.errors:
                report.add_issue(
                    kind="validation_error",
                    severity="error",
                    message=error_message,
                    check="validate",
                )
            return report

        for validation_warning in validation.warnings:
            report.add_issue(
                kind=validation_warning.type,
                severity=_validation_warning_severity(validation_warning),
                message=validation_warning.message,
                check="validate",
                path=validation_warning.path,
            )

        for lint_warning in self.linter.lint_file(str(path)):
            report.add_issue(
                kind=lint_warning.rule,
                severity=lint_warning.severity,
                message=lint_warning.message,
                check="lint",
                path=lint_warning.path,
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
            for pydantic_error in exc.errors():
                loc = " -> ".join(str(part) for part in pydantic_error["loc"])
                report.add_issue(
                    kind="resolution_validation_error",
                    severity="error",
                    message=f"{loc}: {pydantic_error['msg']}",
                    check="resolve",
                )
            return report

        if self.check_compile:
            self._check_compile_artifacts(path, identity, report)

        return report

    def _check_team(self, item: _Discovered) -> DoctorFileReport:
        path = item.path
        report = DoctorFileReport(path=self._relative_path(path), kind="team")
        try:
            data = item.data if item.data is not None else self.parser.parse_file(path)
            TeamConfiguration.model_validate(data)
        except ParseError as exc:
            report.add_issue(
                kind="team_parse_error",
                severity="error",
                message=str(exc),
                check="validate-team",
            )
            return report
        except ValidationError as exc:
            for pydantic_error in exc.errors():
                loc = " -> ".join(str(part) for part in pydantic_error["loc"])
                report.add_issue(
                    kind="team_validation_error",
                    severity="error",
                    message=f"{loc}: {pydantic_error['msg']}",
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
            if len(expected_outputs) != len(actual_outputs):
                report.add_issue(
                    kind="compile_output_shape",
                    severity="error",
                    message=(
                        f"Compile target '{target}' produced {len(actual_outputs)} "
                        f"output(s); doctor expected {len(expected_outputs)}. "
                        "The doctor's artifact layout is out of date — please update."
                    ),
                    check="compile",
                )
                continue

            for expected_path, expected_content in zip(
                expected_outputs, actual_outputs, strict=False
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
                if _normalize_for_compare(current_content) != _normalize_for_compare(
                    expected_content
                ):
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


def _normalize_compile_outputs(compiled: str | dict[str, Any]) -> list[str]:
    if isinstance(compiled, dict):
        if {"soul_md", "style_md"} <= set(compiled):
            return [str(compiled["soul_md"]), str(compiled["style_md"])]
        return [json.dumps(compiled, indent=2, ensure_ascii=False)]
    return [compiled]


def _normalize_for_compare(text: str) -> str:
    """Normalize trailing whitespace so trivial formatting drift doesn't fail."""
    return text.rstrip() + "\n"


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
    # `ValidationWarning.severity` is low | medium | high. Treat medium as a
    # warning so it isn't lost in the noise of info findings.
    if warning.severity in ("high", "medium"):
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
