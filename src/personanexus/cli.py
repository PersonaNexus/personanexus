"""Command-line interface for the AI PersonaNexus Framework."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from personanexus.analyzer import AnalysisResult, AnalyzerError, SoulAnalyzer
from personanexus.compiler import CompilerError, compile_identity
from personanexus.diff import compatibility_score, diff_identities, format_diff
from personanexus.drift import detect_drift_from_files, format_drift_report
from personanexus.linter import IdentityLinter
from personanexus.parser import ParseError
from personanexus.resolver import IdentityResolver, ResolutionError
from personanexus.team_types import TeamConfiguration
from personanexus.types import TRAIT_ORDER
from personanexus.validator import IdentityValidator

app = typer.Typer(
    name="personanexus",
    help="AI PersonaNexus Framework CLI - validate, resolve, and scaffold agent identities",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------


def _sanitize_filename(name: str) -> str:
    """Sanitize a user-provided name into a safe filename component.

    Strips all characters except alphanumeric and underscores to prevent
    path traversal attacks.
    """
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower()).strip("_")
    # Collapse consecutive underscores
    safe = re.sub(r"_+", "_", safe)
    return safe if safe else "agent"


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically via temp-and-rename.

    On POSIX systems ``os.replace`` is atomic within the same filesystem,
    preventing partial writes from corrupting the target file.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(str(tmp), str(path))
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------


@app.command()
def validate(
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file")],
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show extra validation details")
    ] = False,
    no_warnings: Annotated[
        bool, typer.Option("--no-warnings", help="Suppress warning messages")
    ] = False,
) -> None:
    """Parse and validate an PersonaNexus YAML file."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    validator = IdentityValidator()

    try:
        result = validator.validate_file(file)
    except Exception as exc:
        console.print("[red]Validation failed with unexpected error:[/red]")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    # Display errors
    if result.errors:
        console.print(f"\n[red]✗ Validation failed for {file}[/red]\n")
        for error in result.errors:
            console.print(f"  [red]• {error}[/red]")
        console.print()
        raise typer.Exit(code=1)

    # Display warnings
    if result.warnings and not no_warnings:
        console.print(f"\n[yellow]Warnings ({len(result.warnings)}):[/yellow]\n")
        for warning in result.warnings:
            severity_color = {
                "low": "dim yellow",
                "medium": "yellow",
                "high": "bold yellow",
            }.get(warning.severity, "yellow")
            prefix = f"[{warning.type}]" if verbose else ""
            location = f" ({warning.path})" if warning.path and verbose else ""
            console.print(
                f"  [{severity_color}]\u26a0 {prefix}{location}"
                f" {warning.message}[/{severity_color}]"
            )
        console.print()

    # Success
    console.print(f"[green]✓ Validation successful: {file}[/green]")

    if verbose and result.identity:
        identity = result.identity
        console.print(f"\n[dim]Identity: {identity.metadata.id}[/dim]")
        console.print(f"[dim]Name: {identity.metadata.name}[/dim]")
        console.print(f"[dim]Version: {identity.metadata.version}[/dim]")
        console.print(f"[dim]Status: {identity.metadata.status.value}[/dim]")
        if identity.extends:
            console.print(f"[dim]Extends: {identity.extends}[/dim]")
        if identity.mixins:
            console.print(f"[dim]Mixins: {', '.join(identity.mixins)}[/dim]")


# ---------------------------------------------------------------------------
# lint command
# ---------------------------------------------------------------------------


@app.command()
def lint(
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file to lint")],
    severity: Annotated[
        str,
        typer.Option(
            "--severity",
            "-s",
            help="Minimum severity to show: info, warning, or error",
        ),
    ] = "info",
) -> None:
    """Run semantic lint checks on a PersonaNexus YAML file.

    Goes beyond schema validation to find logical inconsistencies,
    unused fields, conflicting settings, and missing recommended config.
    """
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    severity_levels = {"info": 0, "warning": 1, "error": 2}
    if severity not in severity_levels:
        console.print(
            f"[red]Error: Invalid severity '{severity}'. "
            "Must be 'info', 'warning', or 'error'[/red]"
        )
        raise typer.Exit(code=1)
    min_level = severity_levels[severity]

    linter = IdentityLinter()

    try:
        warnings = linter.lint_file(str(file))
    except Exception as exc:
        console.print("[red]Linting failed:[/red]")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    # Filter by severity
    filtered = [w for w in warnings if severity_levels.get(w.severity, 0) >= min_level]

    if not filtered:
        console.print(f"[green]No lint warnings for {file}[/green]")
        return

    severity_color = {
        "info": "blue",
        "warning": "yellow",
        "error": "red",
    }

    console.print(f"\n[bold]Lint results for {file} ({len(filtered)} findings):[/bold]\n")
    for w in filtered:
        color = severity_color.get(w.severity, "white")
        location = f" ({w.path})" if w.path else ""
        console.print(
            f"  [{color}][{w.severity.upper()}] {w.rule}{location}: {w.message}[/{color}]"
        )
    console.print()

    # Exit 1 if any errors found
    if any(w.severity == "error" for w in filtered):
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# resolve command
# ---------------------------------------------------------------------------


@app.command()
def resolve(
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file to resolve")],
    output: Annotated[
        str, typer.Option("--output", "-o", help="Output format: yaml or json")
    ] = "yaml",
    search_path: Annotated[
        list[Path] | None,
        typer.Option(
            "--search-path",
            "-s",
            help="Additional search paths for archetypes/mixins (repeatable)",
        ),
    ] = None,
    trace: Annotated[
        bool,
        typer.Option("--trace", help="Show merge trace after resolved output"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show only the merge trace, not the resolved identity"),
    ] = False,
) -> None:
    """Show fully resolved identity after inheritance and mixin composition."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    if output not in ("yaml", "json"):
        console.print(
            f"[red]Error: Invalid output format '{output}'. Must be 'yaml' or 'json'[/red]"
        )
        raise typer.Exit(code=1)

    # Build search paths
    search_paths = search_path or []
    use_trace = trace or dry_run

    try:
        resolver = IdentityResolver(search_paths=search_paths)
        if use_trace:
            identity, merge_trace = resolver.resolve_file_traced(file)
        else:
            identity = resolver.resolve_file(file)
            merge_trace = None
    except ParseError as exc:
        console.print(f"[red]Parse error: {exc}[/red]")
        raise typer.Exit(code=1)
    except ResolutionError as exc:
        console.print(f"[red]Resolution error: {exc}[/red]")
        raise typer.Exit(code=1)
    except ValidationError as exc:
        console.print("[red]Validation error after resolution:[/red]")
        for error in exc.errors():
            loc = " -> ".join(str(part) for part in error["loc"])
            console.print(f"  [red]• {loc}: {error['msg']}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print("[red]Resolution failed with unexpected error:[/red]")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    # Show resolved identity (unless --dry-run)
    if not dry_run:
        # Convert to dict — use mode="json" for serializable output
        resolved_dict = json.loads(identity.model_dump_json(exclude_none=True))

        if output == "json":
            json_str = json.dumps(resolved_dict, indent=2)
            console.print(json_str)
        else:
            yaml_str = yaml.dump(
                resolved_dict,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            console.print(yaml_str)

    # Show merge trace if requested
    if merge_trace is not None:
        if not dry_run:
            console.print()  # separator between output and trace
        console.print(merge_trace.format_text())


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


@app.command()
def init(
    name: Annotated[str, typer.Argument(help="Name for the new PersonaNexus")],
    type: Annotated[
        str,
        typer.Option(
            "--type",
            "-t",
            help="Type of identity to scaffold: minimal, full, archetype, or mixin",
        ),
    ] = "minimal",
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-d", help="Directory to create the identity file in"),
    ] = Path("./agents"),
    extends: Annotated[
        str | None,
        typer.Option("--extends", "-e", help="Archetype to extend (sets up inheritance)"),
    ] = None,
) -> None:
    """Scaffold a new PersonaNexus YAML file with sensible defaults."""
    if type not in ("minimal", "full", "archetype", "mixin"):
        console.print(
            f"[red]Error: Invalid type '{type}'. Must be"
            f" 'minimal', 'full', 'archetype', or 'mixin'[/red]"
        )
        raise typer.Exit(code=1)

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from name (sanitized to prevent path traversal)
    filename = _sanitize_filename(name) + ".yaml"

    output_path = output_dir / filename
    if output_path.exists():
        overwrite = typer.confirm(f"File {output_path} already exists. Overwrite?")
        if not overwrite:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    # Generate unique ID
    unique_suffix = uuid.uuid4().hex[:8]
    agent_id = f"agt_{filename.replace('.yaml', '')}_{unique_suffix}"

    # Current timestamp
    now = datetime.now()
    timestamp = now.isoformat()

    # Build the YAML content based on type
    if type == "archetype":
        content = _generate_archetype_template(name, agent_id, timestamp)
    elif type == "mixin":
        content = _generate_mixin_template(name, agent_id, timestamp)
    elif type == "full":
        content = _generate_full_template(name, agent_id, timestamp, extends)
    else:  # minimal
        content = _generate_minimal_template(name, agent_id, timestamp, extends)

    # Write the file (atomic to prevent corruption)
    _atomic_write(output_path, content)

    console.print(f"\n[green]✓ Created {type} identity: {output_path}[/green]")
    console.print(f"[dim]ID: {agent_id}[/dim]")
    if extends:
        console.print(f"[dim]Extends: {extends}[/dim]")
    console.print()


def _generate_minimal_template(
    name: str, agent_id: str, timestamp: str, extends: str | None
) -> str:
    """Generate a minimal identity template."""
    lines = ["schema_version: '1.0'", ""]

    if extends:
        lines.extend([f'extends: "{extends}"', ""])

    lines.extend(
        [
            "metadata:",
            f"  id: {agent_id}",
            f'  name: "{name}"',
            "  version: 0.1.0",
            f'  description: "Agent identity for {name}"',
            f'  created_at: "{timestamp}"',
            f'  updated_at: "{timestamp}"',
            "  status: draft",
            "",
            "role:",
            f'  title: "{name}"',
            f'  purpose: "Assist users with tasks related to {name.lower()}"',
            "  scope:",
            "    primary:",
            "      - General assistance",
            "",
            "personality:",
            "  traits:",
            "    warmth: 0.7",
            "    directness: 0.6",
            "    rigor: 0.5",
            "",
            "communication:",
            "  tone:",
            "    default: professional and helpful",
            "",
            "principles:",
            "  - id: principle_1",
            "    priority: 1",
            "    statement: Always prioritize user safety and privacy",
            "",
            "guardrails:",
            "  hard:",
            "    - id: no_harmful_content",
            "      rule: Never generate harmful, illegal, or unethical content",
            "      enforcement: output_filter",
            "      severity: critical",
        ]
    )

    return "\n".join(lines)


def _generate_full_template(name: str, agent_id: str, timestamp: str, extends: str | None) -> str:
    """Generate a full identity template with all major sections."""
    lines = ["schema_version: '1.0'", ""]

    if extends:
        lines.extend([f'extends: "{extends}"', ""])

    lines.extend(
        [
            "metadata:",
            f"  id: {agent_id}",
            f'  name: "{name}"',
            "  version: 0.1.0",
            f'  description: "Full PersonaNexus for {name}"',
            f'  created_at: "{timestamp}"',
            f'  updated_at: "{timestamp}"',
            "  author: PersonaNexus Framework",
            "  tags:",
            "    - assistant",
            "  status: draft",
            "",
            "role:",
            f'  title: "{name}"',
            f'  purpose: "A comprehensive assistant for {name.lower()}-related tasks"',
            "  scope:",
            "    primary:",
            "      - General assistance",
            "      - Information retrieval",
            "    secondary:",
            "      - Task planning",
            "  audience:",
            "    primary: General users",
            "    assumed_knowledge: intermediate",
            "",
            "personality:",
            "  traits:",
            "    warmth: 0.7",
            "    verbosity: 0.5",
            "    directness: 0.6",
            "    rigor: 0.5",
            "    empathy: 0.7",
            "  notes: A balanced personality focused on helpfulness",
            "",
            "communication:",
            "  tone:",
            "    default: professional and approachable",
            "    register: consultative",
            "  style:",
            "    sentence_length: mixed",
            "    use_headers: true",
            "    use_lists: true",
            "    use_emoji: sparingly",
            "  language:",
            "    primary: en",
            "    reading_level: intermediate",
            "    jargon_policy: define_on_first_use",
            "",
            "expertise:",
            "  domains:",
            "    - name: General Knowledge",
            "      level: 0.7",
            "      category: primary",
            "      can_teach: true",
            "  out_of_expertise_strategy: acknowledge_and_redirect",
            "",
            "principles:",
            "  - id: safety_first",
            "    priority: 1",
            "    statement: Prioritize user safety and wellbeing above all else",
            "  - id: be_helpful",
            "    priority: 2",
            "    statement: Provide accurate, helpful, and actionable information",
            "  - id: respect_privacy",
            "    priority: 3",
            "    statement: Respect user privacy and handle data responsibly",
            "",
            "behavior:",
            "  conversation:",
            "    length_calibration:",
            "      default: adaptive",
            "    clarification_policy:",
            "      default: ask_when_ambiguous",
            "      bias: toward_action",
            "",
            "guardrails:",
            "  hard:",
            "    - id: no_harmful_content",
            "      rule: Never generate harmful, illegal, or unethical content",
            "      enforcement: output_filter",
            "      severity: critical",
            "    - id: no_personal_data_leak",
            "      rule: Never expose or request sensitive personal information",
            "      enforcement: output_filter",
            "      severity: critical",
            "  permissions:",
            "    autonomous:",
            "      - Answer questions",
            "      - Provide explanations",
            "    forbidden:",
            "      - Access external systems without permission",
            "      - Modify user data",
            "",
            "memory:",
            "  session:",
            "    strategy: sliding_window_with_summary",
            "    sliding_window:",
            "      max_turns: 50",
            "      max_tokens: 8000",
            "",
            "presentation:",
            "  platforms:",
            "    defaults:",
            "      max_response_length: 2000",
            "      format: markdown",
            "",
            "# Dynamic personality — moods, modes, and memory influences",
            "dynamics:",
            "  default_mood: neutral",
            "  default_mode: stranger",
            "  moods:",
            "    - name: neutral",
            "      description: Default balanced state",
            "      trait_deltas: {}",
            "    - name: empathetic",
            "      description: Activated when user seems frustrated",
            "      triggers:",
            "        - type: sentiment_below",
            "          value: 0.3",
            "      trait_deltas:",
            "        warmth: 0.20",
            "        empathy: 0.15",
            "        patience: 0.10",
            "      tone_override: warm and supportive",
            "  modes:",
            "    - name: stranger",
            "      description: Default mode for unknown users",
            "      triggers:",
            "        - type: user_known",
            "          value: false",
            "      trait_overrides:",
            "        warmth: 0.50",
            "      tone_override: professional and helpful",
            "    - name: familiar",
            "      description: Mode for returning users",
            "      triggers:",
            "        - type: interaction_count_above",
            "          value: 5",
            "      trait_overrides:",
            "        warmth: 0.75",
            "      tone_override: friendly and personable",
            "  memory_influences:",
            "    - condition: 'positive_interactions > 10'",
            "      effect: 'warmth +0.10 permanent'",
            "    - condition: 'positive_interactions > 5'",
            "      effect: 'unlock_mode familiar'",
        ]
    )

    return "\n".join(lines)


def _generate_archetype_template(name: str, agent_id: str, timestamp: str) -> str:
    """Generate an archetype template."""
    lines = [
        "schema_version: '1.0'",
        "",
        "archetype:",
        f"  id: {agent_id}",
        f'  name: "{name}"',
        f'  description: "Base archetype for {name.lower()} agents"',
        "  abstract: true",
        "",
        "metadata:",
        f"  id: {agent_id}",
        f'  name: "{name} Archetype"',
        "  version: 1.0.0",
        f'  description: "Archetype defining core traits for {name.lower()} agents"',
        f'  created_at: "{timestamp}"',
        f'  updated_at: "{timestamp}"',
        "  status: active",
        "",
        "role:",
        f'  title: "{name}"',
        f'  purpose: "Base purpose for {name.lower()} agents"',
        "  scope:",
        "    primary:",
        "      - Core capability area",
        "",
        "personality:",
        "  traits:",
        "    warmth: 0.7",
        "    directness: 0.6",
        "    rigor: 0.5",
        "",
        "communication:",
        "  tone:",
        "    default: professional",
        "",
        "principles:",
        "  - id: core_principle",
        "    priority: 1",
        "    statement: Core principle for this archetype",
        "",
        "guardrails:",
        "  hard:",
        "    - id: base_safety",
        "      rule: Fundamental safety constraint",
        "      enforcement: output_filter",
        "      severity: critical",
    ]

    return "\n".join(lines)


def _generate_mixin_template(name: str, agent_id: str, timestamp: str) -> str:
    """Generate a mixin template."""
    lines = [
        "schema_version: '1.0'",
        "",
        "mixin:",
        f"  id: {agent_id}",
        f'  name: "{name}"',
        f'  description: "Mixin providing {name.lower()} capabilities"',
        "",
        "metadata:",
        f"  id: {agent_id}",
        f'  name: "{name} Mixin"',
        "  version: 1.0.0",
        f'  description: "Adds {name.lower()} functionality to any agent"',
        f'  created_at: "{timestamp}"',
        f'  updated_at: "{timestamp}"',
        "  status: active",
        "",
        "role:",
        f'  title: "{name} Enhanced"',
        "  purpose: Provides additional capabilities",
        "  scope:",
        "    primary:",
        "      - Enhanced capability",
        "",
        "personality:",
        "  traits:",
        "    warmth: 0.5",
        "    creativity: 0.6",
        "",
        "communication:",
        "  tone:",
        "    default: adaptive",
        "",
        "expertise:",
        "  domains:",
        f"    - name: {name}",
        "      level: 0.8",
        "      category: secondary",
        "",
        "principles:",
        "  - id: mixin_principle",
        "    priority: 10",
        f"    statement: Apply {name.lower()} best practices",
        "",
        "guardrails:",
        "  hard:",
        "    - id: mixin_safety",
        f"      rule: Safety constraint for {name.lower()}",
        "      enforcement: prompt_instruction",
        "      severity: high",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# compile command
# ---------------------------------------------------------------------------


@app.command()
def compile(
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file to compile")],
    target: Annotated[
        str,
        typer.Option(
            "--target",
            "-t",
            help="Target: text, anthropic, openai, openclaw, soul, "
            "json, langchain, crewai, autogen, markdown",
        ),
    ] = "text",
    search_path: Annotated[
        list[Path] | None,
        typer.Option(
            "--search-path",
            "-s",
            help="Additional search paths for archetypes/mixins (repeatable)",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (defaults to stdout)"),
    ] = None,
    token_budget: Annotated[
        int,
        typer.Option("--token-budget", help="Estimated token budget for system prompt"),
    ] = 3000,
    apply_evolution: Annotated[
        bool,
        typer.Option("--apply-evolution", help="Apply .evolution deltas before compiling"),
    ] = False,
) -> None:
    """Compile a resolved identity into a system prompt or platform format."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    valid_targets = (
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
    if target not in valid_targets:
        console.print(
            f"[red]Error: Invalid target '{target}'."
            f" Must be one of: {', '.join(valid_targets)}[/red]"
        )
        raise typer.Exit(code=1)

    # Resolve inheritance first
    search_paths = search_path or []

    try:
        resolver = IdentityResolver(search_paths=search_paths)
        identity = resolver.resolve_file(file)
        if apply_evolution:
            from personanexus.evolution import apply_deltas, load_evolution_state

            identity = apply_deltas(identity, load_evolution_state(file, create=False))
    except ParseError as exc:
        console.print(f"[red]Parse error: {exc}[/red]")
        raise typer.Exit(code=1)
    except ResolutionError as exc:
        console.print(f"[red]Resolution error: {exc}[/red]")
        raise typer.Exit(code=1)
    except ValidationError as exc:
        console.print("[red]Validation error after resolution:[/red]")
        for error in exc.errors():
            loc = " -> ".join(str(part) for part in error["loc"])
            console.print(f"  [red]• {loc}: {error['msg']}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Resolution failed: {exc}[/red]")
        raise typer.Exit(code=1)

    # Compile to target format
    try:
        result = compile_identity(identity, target=target, token_budget=token_budget)
    except CompilerError as exc:
        console.print(f"[red]Compilation error: {exc}[/red]")
        raise typer.Exit(code=1)

    # Soul target produces two files (SOUL.md + STYLE.md)
    if target == "soul":
        if not isinstance(result, dict):
            console.print("[red]Soul compiler returned unexpected format[/red]")
            raise typer.Exit(code=1)
        stem = file.stem
        if output:
            # If explicit output given, use it as directory
            out_dir = output if output.is_dir() or not output.suffix else output.parent
        else:
            out_dir = file.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        soul_path = out_dir / f"{stem}.SOUL.md"
        style_path = out_dir / f"{stem}.STYLE.md"
        _atomic_write(soul_path, result["soul_md"])
        _atomic_write(style_path, result["style_md"])
        console.print(f"[green]✓ Compiled {identity.metadata.name} → {soul_path}[/green]")
        console.print(f"[green]✓ Compiled {identity.metadata.name} → {style_path}[/green]")
        console.print("[dim]Target: soul (SOUL.md + STYLE.md)[/dim]")
        return

    # Format output
    if isinstance(result, dict):
        output_text = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        output_text = result

    # Auto-generate output path if not specified
    if not output:
        # Derive filename from source: ada.yaml → ada.compiled.txt / ada.personality.json
        stem = file.stem  # e.g. "ada"
        ext_map = {
            "text": ".compiled.md",
            "anthropic": ".compiled.anthropic.md",
            "openai": ".compiled.openai.md",
            "openclaw": ".personality.json",
            "json": ".compiled.json",
            "langchain": ".langchain.json",
            "crewai": ".crewai.yaml",
            "autogen": ".autogen.json",
            "markdown": ".compiled.doc.md",
        }
        suffix = ext_map.get(target, ".compiled.txt")
        output = file.parent / f"{stem}{suffix}"

    # Write to file
    output.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(output, output_text)
    console.print(f"[green]✓ Compiled {identity.metadata.name} → {output}[/green]")
    console.print(f"[dim]Target: {target}[/dim]")

    # Show token estimate for text formats
    if target in ("text", "anthropic", "openai"):
        token_estimate = len(str(output_text)) // 4
        console.print(f"[dim]Estimated tokens: ~{token_estimate}[/dim]")


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    file: Annotated[
        Path,
        typer.Argument(help="Path to SOUL.md, personality.json, or identity YAML file"),
    ],
    compare: Annotated[
        Path | None,
        typer.Option("--compare", "-c", help="Second file for side-by-side comparison"),
    ] = None,
    search_path: Annotated[
        list[Path] | None,
        typer.Option("--search-path", "-s", help="Search paths for YAML resolution"),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table or json"),
    ] = "table",
) -> None:
    """Analyze an agent personality file and show trait/OCEAN/DISC profiles."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if output_format not in ("table", "json"):
        console.print(
            f"[red]Error: Invalid format '{output_format}'. Must be 'table' or 'json'[/red]"
        )
        raise typer.Exit(code=1)

    analyzer = SoulAnalyzer()
    search_paths = search_path or []

    try:
        result = analyzer.analyze(file, search_paths=search_paths)
    except AnalyzerError as exc:
        console.print(f"[red]Analysis error: {exc}[/red]")
        raise typer.Exit(code=1)

    if output_format == "json":
        import json as json_mod

        output = json.loads(result.model_dump_json())
        if compare:
            try:
                result_b = analyzer.analyze(compare, search_paths=search_paths)
                comparison = analyzer.compare(result, result_b)
                output = json.loads(comparison.model_dump_json())
            except AnalyzerError as exc:
                console.print(f"[red]Comparison error: {exc}[/red]")
                raise typer.Exit(code=1)
        print(json_mod.dumps(output, indent=2))
        return

    # Table output
    _print_analysis(result)

    if compare:
        if not compare.exists():
            console.print(f"[red]Error: Comparison file not found: {compare}[/red]")
            raise typer.Exit(code=1)
        try:
            result_b = analyzer.analyze(compare, search_paths=search_paths)
        except AnalyzerError as exc:
            console.print(f"[red]Comparison error: {exc}[/red]")
            raise typer.Exit(code=1)

        console.print()
        _print_analysis(result_b)
        console.print()
        _print_comparison(result, result_b, analyzer)


def _print_analysis(result: AnalysisResult) -> None:
    """Render a full analysis result to the console."""

    name = result.agent_name or "Unknown Agent"
    fmt = result.source_format.value.replace("_", " ").title()
    conf_color = (
        "green" if result.confidence >= 0.8 else "yellow" if result.confidence >= 0.5 else "red"
    )

    console.print(
        f"\n[bold]{name}[/bold]  [dim]({fmt} — confidence:"
        f" [{conf_color}]{result.confidence:.0%}[/{conf_color}])[/dim]"
    )

    # Traits table
    traits = result.traits.defined_traits()
    conf_map = {e.name: e.confidence for e in result.trait_extractions}

    table = Table(title="Personality Traits", show_header=True, header_style="bold")
    table.add_column("Trait", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Level", style="dim")
    table.add_column("Confidence", justify="right")

    for trait_name in TRAIT_ORDER:
        if trait_name in traits:
            val = traits[trait_name]
            level = _level_label(val)
            conf = conf_map.get(trait_name, 1.0)
            conf_col = "green" if conf >= 0.8 else "yellow" if conf >= 0.5 else "red"
            table.add_row(trait_name, f"{val:.2f}", level, f"[{conf_col}]{conf:.0%}[/{conf_col}]")

    console.print(table)

    # OCEAN table
    ocean = result.ocean.model_dump()
    ocean_table = Table(title="OCEAN (Big Five)", show_header=True, header_style="bold")
    ocean_table.add_column("Dimension", style="cyan")
    ocean_table.add_column("Value", justify="right")
    ocean_table.add_column("Level", style="dim")
    for dim in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
        val = ocean[dim]
        ocean_table.add_row(dim.title(), f"{val:.3f}", _level_label(val))
    console.print(ocean_table)

    # DISC table
    disc = result.disc.model_dump()
    disc_table = Table(title="DISC Profile", show_header=True, header_style="bold")
    disc_table.add_column("Dimension", style="cyan")
    disc_table.add_column("Value", justify="right")
    disc_table.add_column("Level", style="dim")
    for dim in ["dominance", "influence", "steadiness", "conscientiousness"]:
        val = disc[dim]
        disc_table.add_row(dim.title(), f"{val:.3f}", _level_label(val))
    console.print(disc_table)

    if result.closest_preset:
        preset = result.closest_preset
        label = preset.preset_name.replace("_", " ").title()
        console.print(f"[dim]Closest DISC preset: {label} (distance: {preset.distance:.3f})[/dim]")

    console.print()


def _print_comparison(
    result_a: AnalysisResult,
    result_b: AnalysisResult,
    analyzer: SoulAnalyzer,
) -> None:
    """Render a comparison table."""
    comparison = analyzer.compare(result_a, result_b)
    name_a = result_a.agent_name or "A"
    name_b = result_b.agent_name or "B"

    console.print(f"[bold]Comparison: {name_a} vs {name_b}[/bold]")
    console.print(f"[dim]Similarity: {comparison.similarity_score:.1%}[/dim]\n")

    table = Table(title="Trait Comparison", show_header=True, header_style="bold")
    table.add_column("Trait", style="cyan")
    table.add_column(name_a, justify="right")
    table.add_column(name_b, justify="right")
    table.add_column("Delta", justify="right")

    for delta in comparison.trait_deltas:
        abs_d = abs(delta.delta)
        color = "green" if abs_d < 0.1 else "yellow" if abs_d < 0.25 else "red"
        sign = "+" if delta.delta > 0 else ""
        table.add_row(
            delta.trait,
            f"{delta.value_a:.2f}",
            f"{delta.value_b:.2f}",
            f"[{color}]{sign}{delta.delta:.2f}[/{color}]",
        )

    console.print(table)
    console.print()


def _level_label(val: float) -> str:
    """Map 0-1 value to a human-readable level label."""
    if val >= 0.8:
        return "Very High"
    elif val >= 0.6:
        return "High"
    elif val >= 0.4:
        return "Moderate"
    elif val >= 0.2:
        return "Low"
    return "Very Low"


# ---------------------------------------------------------------------------
# personality subcommand group
# ---------------------------------------------------------------------------

personality_app = typer.Typer(
    name="personality",
    help="OCEAN/DISC/Jungian personality mapping utilities",
    add_completion=False,
)
app.add_typer(personality_app, name="personality")


@personality_app.command("ocean-to-traits")
def personality_ocean_to_traits(
    openness: Annotated[float, typer.Option(help="Openness to experience (0-1)")],
    conscientiousness: Annotated[float, typer.Option(help="Conscientiousness (0-1)")],
    extraversion: Annotated[float, typer.Option(help="Extraversion (0-1)")],
    agreeableness: Annotated[float, typer.Option(help="Agreeableness (0-1)")],
    neuroticism: Annotated[float, typer.Option(help="Neuroticism (0-1)")],
) -> None:
    """Map OCEAN (Big Five) scores to personality traits."""
    from personanexus.personality import ocean_to_traits
    from personanexus.types import OceanProfile

    try:
        profile = OceanProfile(
            openness=openness,
            conscientiousness=conscientiousness,
            extraversion=extraversion,
            agreeableness=agreeableness,
            neuroticism=neuroticism,
        )
    except Exception as exc:
        console.print(f"[red]Invalid OCEAN values: {exc}[/red]")
        raise typer.Exit(code=1)

    traits = ocean_to_traits(profile)
    _print_traits_table("OCEAN → Traits", traits)


@personality_app.command("disc-to-traits")
def personality_disc_to_traits(
    preset: Annotated[
        str | None,
        typer.Option(
            help="DISC preset name (e.g. the_commander) - overrides individual values if provided",
        ),
    ] = None,
    dominance: Annotated[float | None, typer.Option(help="Dominance (0-1)")] = None,
    influence: Annotated[float | None, typer.Option(help="Influence (0-1)")] = None,
    steadiness: Annotated[float | None, typer.Option(help="Steadiness (0-1)")] = None,
    conscientiousness: Annotated[float | None, typer.Option(help="Conscientiousness (0-1)")] = None,
) -> None:
    """Map DISC scores to personality traits."""
    from personanexus.personality import disc_to_traits, get_disc_preset
    from personanexus.types import DiscProfile

    try:
        if preset:
            profile = get_disc_preset(preset)
        else:
            if (
                dominance is None
                or influence is None
                or steadiness is None
                or conscientiousness is None
            ):
                console.print(
                    "[red]Error: All DISC values required when --preset not provided[/red]"
                )
                raise typer.Exit(code=1)
            profile = DiscProfile(
                dominance=dominance,
                influence=influence,
                steadiness=steadiness,
                conscientiousness=conscientiousness,
            )
    except Exception as exc:
        console.print(f"[red]Invalid DISC values: {exc}[/red]")
        raise typer.Exit(code=1)

    traits = disc_to_traits(profile)
    _print_traits_table("DISC → Traits", traits)


@personality_app.command("preset")
def personality_preset(
    name: Annotated[str, typer.Argument(help="DISC preset name (e.g. the_commander)")],
) -> None:
    """Show computed traits for a named DISC preset."""
    from personanexus.personality import disc_to_traits, get_disc_preset

    try:
        profile = get_disc_preset(name)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]DISC Preset: {name}[/bold]")
    console.print(
        f"[dim]D={profile.dominance}, I={profile.influence}, "
        f"S={profile.steadiness}, C={profile.conscientiousness}[/dim]\n"
    )

    traits = disc_to_traits(profile)
    _print_traits_table(f"Preset '{name}' → Traits", traits)


@personality_app.command("list-disc-presets")
def personality_list_disc_presets() -> None:
    """List all available DISC presets."""
    from personanexus.personality import list_disc_presets

    presets = list_disc_presets()
    console.print("[bold]Available DISC Presets:[/bold]\n")
    for name in presets:
        profile = presets[name]
        console.print(f"  - {name}")
        console.print(
            f"    D={profile.dominance}, I={profile.influence}, "
            f"S={profile.steadiness}, C={profile.conscientiousness}"
        )


@personality_app.command("jungian-to-traits")
def personality_jungian_to_traits(
    preset: Annotated[
        str | None,
        typer.Option(
            help="Jungian type code (e.g. intj) - overrides individual values if provided",
        ),
    ] = None,
    ei: Annotated[float | None, typer.Option(help="Extraversion (0) vs Introversion (1)")] = None,
    sn: Annotated[float | None, typer.Option(help="Sensing (0) vs iNtuition (1)")] = None,
    tf: Annotated[float | None, typer.Option(help="Thinking (0) vs Feeling (1)")] = None,
    jp: Annotated[float | None, typer.Option(help="Judging (0) vs Perceiving (1)")] = None,
) -> None:
    """Map Jungian 16-type scores to personality traits."""
    from personanexus.personality import get_jungian_preset, jungian_to_traits
    from personanexus.types import JungianProfile

    try:
        if preset:
            profile = get_jungian_preset(preset)
        else:
            if ei is None or sn is None or tf is None or jp is None:
                console.print(
                    "[red]Error: All Jungian dimensions required when --preset not provided[/red]"
                )
                raise typer.Exit(code=1)
            profile = JungianProfile(ei=ei, sn=sn, tf=tf, jp=jp)
    except Exception as exc:
        console.print(f"[red]Invalid Jungian values: {exc}[/red]")
        raise typer.Exit(code=1)

    traits = jungian_to_traits(profile)
    _print_traits_table("Jungian → Traits", traits)


@personality_app.command("list-jungian-presets")
def personality_list_jungian_presets() -> None:
    """List all available Jungian 16-type presets."""
    from personanexus.personality import list_jungian_presets

    presets = list_jungian_presets()
    table = Table(title="Jungian 16-Type Presets", show_header=True, header_style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("E/I", justify="right")
    table.add_column("S/N", justify="right")
    table.add_column("T/F", justify="right")
    table.add_column("J/P", justify="right")

    for name, profile in sorted(presets.items()):
        table.add_row(
            name.upper(),
            f"{profile.ei:.2f}",
            f"{profile.sn:.2f}",
            f"{profile.tf:.2f}",
            f"{profile.jp:.2f}",
        )

    console.print(table)


@personality_app.command("jungian-recommend")
def personality_jungian_recommend(
    role_category: Annotated[
        str | None,
        typer.Argument(help="Role category (e.g. data_science, creative_writing)"),
    ] = None,
) -> None:
    """Show recommended Jungian types for an agent role category."""
    from personanexus.personality import (
        JUNGIAN_ROLE_RECOMMENDATIONS,
        get_jungian_role_recommendations,
    )

    if role_category is None:
        console.print("[bold]Available Role Categories:[/bold]\n")
        for category in sorted(JUNGIAN_ROLE_RECOMMENDATIONS.keys()):
            console.print(f"  - {category}")
        return

    try:
        recommendations = get_jungian_role_recommendations(role_category)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    table = Table(
        title=f"Jungian Recommendations for '{role_category}'",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Type", style="cyan")
    table.add_column("Description")

    for type_code, description in recommendations:
        table.add_row(type_code.upper(), description)

    console.print(table)


@personality_app.command("show-profile")
def personality_show_profile(
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file")],
    search_path: Annotated[
        list[Path] | None,
        typer.Option("--search-path", "-s", help="Additional search paths for archetypes/mixins"),
    ] = None,
) -> None:
    """Show the personality profile and computed traits for an identity file."""
    from personanexus.personality import (
        closest_jungian_type,
        compute_personality_traits,
        traits_to_disc,
        traits_to_jungian,
        traits_to_ocean,
    )

    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    search_paths = search_path or []

    try:
        resolver = IdentityResolver(search_paths=search_paths)
        identity = resolver.resolve_file(file)
    except Exception as exc:
        console.print(f"[red]Error resolving identity: {exc}[/red]")
        raise typer.Exit(code=1)

    profile = identity.personality.profile
    console.print(f"\n[bold]{identity.metadata.name} — Personality Profile[/bold]")
    console.print(f"[dim]Mode: {profile.mode.value}[/dim]")

    if profile.ocean:
        console.print(
            f"[dim]OCEAN: O={profile.ocean.openness}, C={profile.ocean.conscientiousness}, "
            f"E={profile.ocean.extraversion}, A={profile.ocean.agreeableness}, "
            f"N={profile.ocean.neuroticism}[/dim]"
        )
    if profile.disc:
        console.print(
            f"[dim]DISC: D={profile.disc.dominance}, I={profile.disc.influence}, "
            f"S={profile.disc.steadiness}, C={profile.disc.conscientiousness}[/dim]"
        )
    if profile.disc_preset:
        console.print(f"[dim]DISC Preset: {profile.disc_preset}[/dim]")
    if profile.jungian:
        console.print(
            f"[dim]Jungian: E/I={profile.jungian.ei}, S/N={profile.jungian.sn}, "
            f"T/F={profile.jungian.tf}, J/P={profile.jungian.jp}[/dim]"
        )
    if profile.jungian_preset:
        console.print(f"[dim]Jungian Preset: {profile.jungian_preset}[/dim]")

    # Compute final traits
    computed = compute_personality_traits(identity.personality)
    traits_dict = computed.defined_traits()
    _print_traits_table("Final Traits", traits_dict)

    # Show reverse mapping
    console.print("\n[bold]Approximate Reverse Mapping:[/bold]")
    ocean_approx = traits_to_ocean(computed)
    console.print(
        f"  OCEAN: O={ocean_approx.openness:.3f}, C={ocean_approx.conscientiousness:.3f}, "
        f"E={ocean_approx.extraversion:.3f}, A={ocean_approx.agreeableness:.3f}, "
        f"N={ocean_approx.neuroticism:.3f}"
    )
    disc_approx = traits_to_disc(computed)
    console.print(
        f"  DISC:  D={disc_approx.dominance:.3f}, I={disc_approx.influence:.3f}, "
        f"S={disc_approx.steadiness:.3f}, C={disc_approx.conscientiousness:.3f}"
    )
    jungian_approx = traits_to_jungian(computed)
    jungian_type = closest_jungian_type(jungian_approx)
    console.print(
        f"  Jungian: E/I={jungian_approx.ei:.3f}, S/N={jungian_approx.sn:.3f}, "
        f"T/F={jungian_approx.tf:.3f}, J/P={jungian_approx.jp:.3f}"
        f"  (closest: {jungian_type})"
    )
    console.print()


def _print_traits_table(title: str, traits: dict[str, float]) -> None:
    """Print a Rich table of trait values."""
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Trait", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Level", style="dim")

    for trait_name in TRAIT_ORDER:
        if trait_name in traits:
            val = traits[trait_name]
            if val >= 0.8:
                level = "Very High"
            elif val >= 0.6:
                level = "High"
            elif val >= 0.4:
                level = "Moderate"
            elif val >= 0.2:
                level = "Low"
            else:
                level = "Very Low"
            table.add_row(trait_name, f"{val:.4f}", level)

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# build command
# ---------------------------------------------------------------------------


@app.command()
def build(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-d", help="Directory to save the identity file"),
    ] = Path("./agents"),
    llm_enhance: Annotated[
        bool,
        typer.Option("--llm-enhance", help="Enhance with LLM suggestions after wizard"),
    ] = False,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Anthropic model for LLM enhancement"),
    ] = "claude-sonnet-4-20250514",
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY)"),
    ] = None,
) -> None:
    """Interactively build a new PersonaNexus with a step-by-step wizard."""
    from personanexus.builder import IdentityBuilder, LLMEnhancer

    builder = IdentityBuilder(console=console)
    identity = builder.run()

    # Optional LLM enhancement
    if llm_enhance:
        enhancer = LLMEnhancer(api_key=api_key, model=model, console=console)
        enhancements = enhancer.enhance(identity)
        identity = enhancer.apply_enhancements(identity, enhancements, interactive=True)

    # Write the file
    output_dir.mkdir(parents=True, exist_ok=True)
    name = identity.data.get("metadata", {}).get("name", "agent")
    filename = _sanitize_filename(name) + ".yaml"
    output_path = output_dir / filename

    yaml_str = identity.to_yaml_string()
    _atomic_write(output_path, yaml_str)

    console.print(f"\n[green]✓ Saved identity: {output_path}[/green]")

    # Validate the result
    validator = IdentityValidator()
    try:
        result = validator.validate_file(output_path)
        if result.valid:
            console.print("[green]✓ Validation passed[/green]")
        else:
            console.print("[yellow]⚠ Validation warnings:[/yellow]")
            for error in result.errors:
                console.print(f"  [yellow]• {error}[/yellow]")
    except Exception as exc:
        console.print(f"[yellow]⚠ Could not validate: {exc}[/yellow]")


# ---------------------------------------------------------------------------
# add-dynamics command
# ---------------------------------------------------------------------------


@app.command("add-dynamics")
def add_dynamics(
    file: Annotated[Path, typer.Argument(help="Path to existing PersonaNexus YAML file")],
) -> None:
    """Add dynamic personality features to an existing identity."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    # Validate first
    validator = IdentityValidator()
    try:
        result = validator.validate_file(file)
    except Exception as exc:
        console.print(f"[red]Error validating file: {exc}[/red]")
        raise typer.Exit(code=1)

    if not result.valid:
        console.print("[red]File has validation errors — fix them first:[/red]")
        for error in result.errors:
            console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)

    # Load existing data
    with open(file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data.get("dynamics"):
        console.print("[yellow]This file already has a dynamics section.[/yellow]")
        from rich.prompt import Confirm as RichConfirm

        if not RichConfirm.ask("Overwrite existing dynamics?", default=False):
            console.print("[dim]No changes made.[/dim]")
            raise typer.Exit(code=0)

    # Run the dynamics wizard
    from personanexus.builder import IdentityBuilder

    builder = IdentityBuilder(console=console)
    builder._phase_dynamics(data)

    if "dynamics" not in data:
        console.print("[dim]No dynamics added.[/dim]")
        raise typer.Exit(code=0)

    # Write back
    from datetime import UTC, datetime

    if "metadata" in data:
        data["metadata"]["updated_at"] = datetime.now(UTC).isoformat()

    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    _atomic_write(file, yaml_str)

    console.print(f"\n[green]✓ Dynamics added to {file}[/green]")

    # Re-validate
    try:
        result = validator.validate_file(file)
        if result.valid:
            console.print("[green]✓ Validation passed[/green]")
        else:
            console.print("[yellow]⚠ Validation issues:[/yellow]")
            for error in result.errors:
                console.print(f"  [yellow]• {error}[/yellow]")
    except Exception as exc:
        console.print(f"[yellow]⚠ Could not validate: {exc}[/yellow]")


# ---------------------------------------------------------------------------
# migrate command
# ---------------------------------------------------------------------------


@app.command()
def migrate(
    from_version: Annotated[str, typer.Argument(help="Source schema version (e.g., 1.0)")],
    to_version: Annotated[str, typer.Argument(help="Target schema version (e.g., 1.1)")],
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file to migrate")],
) -> None:
    """Migrate an identity file from one schema version to another (future use)."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    # Currently only v1.0 is supported
    if from_version == "1.0" and to_version == "1.0":
        console.print("[green]✓ File is already at schema version 1.0[/green]")
        console.print(f"[dim]No migration needed: {file}[/dim]")
        return

    # Placeholder for future migration logic
    console.print(
        Panel(
            f"[yellow]Migration from {from_version} to"
            f" {to_version} is not yet implemented.[/yellow]\n\n"
            f"Current schema version: 1.0\n"
            f"File: {file}\n\n"
            "This command is reserved for future schema evolution.",
            title="Migration Placeholder",
            border_style="yellow",
        )
    )


# ---------------------------------------------------------------------------
# diff command
# ---------------------------------------------------------------------------


@app.command()
def diff(
    file1: Annotated[Path, typer.Argument(help="Path to the first identity YAML file")],
    file2: Annotated[Path, typer.Argument(help="Path to the second identity YAML file")],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text, json, markdown"),
    ] = "text",
) -> None:
    """Compare two PersonaNexus files and show differences."""
    if not file1.exists():
        console.print(f"[red]Error: File not found: {file1}[/red]")
        raise typer.Exit(code=1)

    if not file2.exists():
        console.print(f"[red]Error: File not found: {file2}[/red]")
        raise typer.Exit(code=1)

    if not file1.is_file():
        console.print(f"[red]Error: Not a file: {file1}[/red]")
        raise typer.Exit(code=1)

    if not file2.is_file():
        console.print(f"[red]Error: Not a file: {file2}[/red]")
        raise typer.Exit(code=1)

    try:
        diff_result = diff_identities(str(file1), str(file2))

        if format == "json":
            console.print_json(data=diff_result)
        elif format == "markdown":
            console.print(Markdown(format_diff(diff_result, "markdown")))
        else:
            # text format
            console.print(format_diff(diff_result, "text"))

    except Exception as e:
        console.print(f"[red]Error computing diff: {e}[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# compat command
# ---------------------------------------------------------------------------


@app.command()
def compat(
    file1: Annotated[Path, typer.Argument(help="Path to the first identity YAML file")],
    file2: Annotated[Path, typer.Argument(help="Path to the second identity YAML file")],
) -> None:
    """Calculate compatibility score between two agent identities."""
    if not file1.exists():
        console.print(f"[red]Error: File not found: {file1}[/red]")
        raise typer.Exit(code=1)

    if not file2.exists():
        console.print(f"[red]Error: File not found: {file2}[/red]")
        raise typer.Exit(code=1)

    if not file1.is_file():
        console.print(f"[red]Error: Not a file: {file1}[/red]")
        raise typer.Exit(code=1)

    if not file2.is_file():
        console.print(f"[red]Error: Not a file: {file2}[/red]")
        raise typer.Exit(code=1)

    try:
        score = compatibility_score(str(file1), str(file2))

        # Create a colored progress bar style display
        console.print()
        console.print(
            Panel(
                f"[bold]Compatibility Score[/bold]\n\n"
                f"  {file1.name}  \u2194  {file2.name}\n"
                f"\n"
                f"  [bold][green]{score}%[/green][/bold]\n"
                f"\n"
                f"[dim]Based on personality trait alignment (OCEAN/DISC)[/dim]",
                title="Score",
                border_style="green",
                padding=(1, 2),
            )
        )

        # Interpret the score
        if score >= 80:
            console.print(
                "\n[yellow]Interpretation: Very high alignment"
                " - agents will likely work well together![/yellow]"
            )
        elif score >= 60:
            console.print(
                "\n[yellow]Interpretation: Good alignment - minor adjustments may help.[/yellow]"
            )
        elif score >= 40:
            console.print(
                "\n[yellow]Interpretation: Moderate alignment"
                " - some compatibility but differences present.[/yellow]"
            )
        else:
            console.print(
                "\n[yellow]Interpretation: Low alignment"
                " - significant personality differences detected.[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error calculating compatibility: {e}[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# drift command
# ---------------------------------------------------------------------------


@app.command()
def drift(
    baseline: Annotated[Path, typer.Argument(help="Path to the baseline identity YAML file")],
    current: Annotated[Path, typer.Argument(help="Path to the current identity YAML file")],
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="Trait drift threshold (default 0.1)"),
    ] = 0.1,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text, json"),
    ] = "text",
) -> None:
    """Detect configuration drift between two PersonaNexus identity files."""
    if not baseline.exists():
        console.print(f"[red]Error: File not found: {baseline}[/red]")
        raise typer.Exit(code=1)

    if not current.exists():
        console.print(f"[red]Error: File not found: {current}[/red]")
        raise typer.Exit(code=1)

    if not baseline.is_file():
        console.print(f"[red]Error: Not a file: {baseline}[/red]")
        raise typer.Exit(code=1)

    if not current.is_file():
        console.print(f"[red]Error: Not a file: {current}[/red]")
        raise typer.Exit(code=1)

    try:
        report = detect_drift_from_files(
            baseline_path=str(baseline),
            current_path=str(current),
            threshold=threshold,
        )

        if format == "json":
            console.print_json(data=report.to_dict())
        else:
            output = format_drift_report(report, fmt="text")
            if report.drift_detected:
                severity_colors = {
                    "minor": "yellow",
                    "major": "red",
                    "critical": "bold red",
                }
                color = severity_colors.get(report.severity, "green")
                console.print(
                    Panel(
                        output,
                        title=f"[{color}]Drift Report ({report.severity.upper()})[/{color}]",
                        border_style=color,
                    )
                )
            else:
                console.print(
                    Panel(
                        output,
                        title="[green]Drift Report (CLEAN)[/green]",
                        border_style="green",
                    )
                )

    except Exception as e:
        console.print(f"[red]Error detecting drift: {e}[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# validate-team command
# ---------------------------------------------------------------------------


@app.command("validate-team")
def validate_team(
    file: Annotated[Path, typer.Argument(help="Path to team configuration YAML file")],
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show extra validation details")
    ] = False,
) -> None:
    """Parse and validate a team configuration YAML file (schema v2.0)."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    try:
        # Parse YAML content
        with open(file, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if not content:
            console.print(f"[red]Error: Empty or invalid YAML file: {file}[/red]")
            raise typer.Exit(code=1)

        # Validate against team schema
        team_config = TeamConfiguration.model_validate(content)

        # Success
        console.print(f"[green]✓ Team validation successful: {file}[/green]")

        if verbose:
            # Show team composition summary
            agents = team_config.team.composition.agents
            console.print(f"[dim]Team: {team_config.team.metadata.name}[/dim]")
            console.print(f"[dim]Schema version: {team_config.schema_version}[/dim]")
            console.print(f"[dim]Agents: {len(agents)} ({', '.join(agents.keys())})[/dim]")

            if team_config.team.workflow_patterns:
                workflows = list(team_config.team.workflow_patterns.keys())
                console.print(f"[dim]Workflows: {len(workflows)} ({', '.join(workflows)})[/dim]")

    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)
    except yaml.YAMLError as e:
        console.print(f"[red]Error: Invalid YAML syntax: {e}[/red]")
        raise typer.Exit(code=1)
    except ValidationError as e:
        console.print(f"[red]✗ Team validation failed: {file}[/red]")
        console.print()

        # Show validation errors in a structured way
        errors_table = Table(title="Validation Errors", show_header=True, header_style="bold red")
        errors_table.add_column("Field", style="cyan")
        errors_table.add_column("Error", style="red")

        for error in e.errors():
            field_path = " → ".join(str(loc) for loc in error["loc"])
            error_msg = error["msg"]
            errors_table.add_row(field_path, error_msg)

        console.print(errors_table)
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error: Unexpected validation error: {e}[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Simulate — dynamics mock chat loop
# ---------------------------------------------------------------------------


_SIMULATE_MESSAGES = [
    ("Hello, I need help with my data.", 0.5),
    ("This is really frustrating, nothing works!", 0.15),
    ("Oh wait, I think I see the issue now.", 0.55),
    ("Wow, that's an interesting pattern in the data!", 0.85),
    ("We have an urgent deadline, can you be quick?", 0.35),
    ("Thanks so much, this is really helpful!", 0.9),
    ("Could you explain that in simpler terms? I'm confused.", 0.3),
    ("Great work! Let's keep going.", 0.8),
    ("I found a discovery in the dataset!", 0.9),
    ("Can we wrap up? I think we're done.", 0.6),
]


@app.command()
def simulate(
    persona: Annotated[Path, typer.Argument(help="Path to persona YAML with dynamics section")],
    user: Annotated[str, typer.Option(help="Simulated user ID")] = "stranger",
    steps: Annotated[int, typer.Option(help="Number of interaction steps to simulate")] = 10,
    show_prompt: Annotated[
        bool, typer.Option("--show-prompt", help="Show compiled prompt")
    ] = False,
    memory_dir: Annotated[str | None, typer.Option(help="Directory for memory persistence")] = None,
) -> None:
    """Simulate a multi-turn chat loop showing dynamic personality shifts."""
    from personanexus.dynamics import DynamicSession
    from personanexus.resolver import IdentityResolver

    try:
        resolver = IdentityResolver()
        identity = resolver.resolve_file(persona)
    except Exception as e:
        console.print(f"[red]Error loading persona: {e}[/red]")
        raise typer.Exit(code=1)

    if identity.dynamics is None:
        console.print("[yellow]Warning: This persona has no 'dynamics' section.[/yellow]")
        console.print("[dim]The simulation will run with static personality.[/dim]")

    session = DynamicSession(identity, user_id=user, memory_dir=memory_dir)

    console.print(
        Panel(
            f"[bold]Dynamics Simulation[/bold]\n"
            f"Persona: {identity.metadata.name} ({identity.metadata.id})\n"
            f"User: {user}\n"
            f"Steps: {steps}",
            title="PersonaNexus Simulate",
            border_style="blue",
        )
    )

    messages = _SIMULATE_MESSAGES
    actual_steps = min(steps, len(messages))

    for i in range(actual_steps):
        msg, sentiment = messages[i % len(messages)]
        positive = sentiment > 0.6

        console.print()
        console.print(f"[bold cyan]─── Step {i + 1}/{actual_steps} ───[/bold cyan]")
        console.print(f"[dim]User says:[/dim] {msg}")
        console.print(f"[dim]Sentiment:[/dim] {sentiment:.2f}")

        result = session.process(
            message=msg,
            sentiment=sentiment,
            positive=positive if positive else None,
            trust_delta=0.05 if positive else -0.02,
            compile_prompt=show_prompt,
        )

        # Build a trait change table
        table = Table(show_header=True, header_style="bold green", expand=False)
        table.add_column("Trait", style="cyan", width=20)
        table.add_column("Base", justify="right", width=8)
        table.add_column("Adjusted", justify="right", width=10)
        table.add_column("Delta", justify="right", width=8)

        base_traits = identity.personality.traits.defined_traits()
        for trait in sorted(result.adjusted_traits.keys()):
            base_val = base_traits.get(trait, 0.5)
            adj_val = result.adjusted_traits[trait]
            delta = adj_val - base_val
            delta_str = f"{delta:+.2f}" if delta != 0 else "—"
            delta_style = "green" if delta > 0 else "red" if delta < 0 else "dim"
            table.add_row(
                trait,
                f"{base_val:.2f}",
                f"{adj_val:.2f}",
                f"[{delta_style}]{delta_str}[/]",
            )

        console.print(table)
        console.print(
            f"  [bold]Mood:[/bold] {result.active_mood}  [bold]Mode:[/bold] {result.active_mode}"
        )
        if result.tone_override:
            console.print(f"  [bold]Tone override:[/bold] {result.tone_override}")
        if result.influences_applied:
            for inf in result.influences_applied:
                console.print(f"  [yellow]★ Influence applied:[/yellow] {inf}")

        # Show state summary
        st = session.state
        console.print(
            f"  [dim]Interactions: {st.interaction_count} | "
            f"Sentiment: {st.avg_sentiment:.2f} | "
            f"Trust: {st.trust_score:.2f} | "
            f"Positive: {st.custom.get('positive_interactions', 0)}[/dim]"
        )

        if show_prompt and result.compiled_prompt:
            console.print()
            console.print(
                Panel(
                    Markdown(
                        result.compiled_prompt[:500] + "..."
                        if len(result.compiled_prompt) > 500
                        else result.compiled_prompt
                    ),
                    title="Compiled Prompt (truncated)",
                    border_style="dim",
                )
            )

    console.print()
    console.print("[bold green]✓ Simulation complete.[/bold green]")

    # Final summary
    st = session.state
    console.print(
        Panel(
            f"Final State:\n"
            f"  Interactions: {st.interaction_count}\n"
            f"  Avg Sentiment: {st.avg_sentiment:.3f}\n"
            f"  Trust Score: {st.trust_score:.3f}\n"
            f"  Current Mood: {st.current_mood}\n"
            f"  Current Mode: {st.current_mode}\n"
            f"  Applied Influences: {len(st.applied_influences)}",
            title="Session Summary",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# evolve subcommand group
# ---------------------------------------------------------------------------

evolve_app = typer.Typer(
    name="evolve",
    help="Persona evolution engine commands",
    add_completion=False,
)
app.add_typer(evolve_app, name="evolve")


@evolve_app.command("enable")
def evolve_enable(
    persona: Annotated[str, typer.Argument(help="Persona YAML path or persona name")],
    mode: Annotated[
        str, typer.Option("--mode", help="Evolution mode: soft, hard, or both")
    ] = "soft",
    learning_rate: Annotated[
        str, typer.Option("--learning-rate", help="low, medium, or high")
    ] = "medium",
    consensus_threshold: Annotated[
        int, typer.Option("--consensus-threshold", help="Signals required for hard evolution")
    ] = 3,
    review_mode: Annotated[str, typer.Option("--review-mode", help="prompt or auto")] = "prompt",
) -> None:
    """Enable evolution settings on a persona YAML file."""
    from personanexus.evolution import configure_evolution, resolve_persona_path
    from personanexus.types import EvolutionMode, LearningRate, ReviewMode

    try:
        persona_path = resolve_persona_path(persona)
        configure_evolution(
            persona_path,
            mode=EvolutionMode(mode),
            learning_rate=LearningRate(learning_rate),
            consensus_threshold=consensus_threshold,
            review_mode=ReviewMode(review_mode),
        )
    except Exception as exc:
        console.print(f"[red]Enable failed: {exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓ Evolution enabled for {persona_path}[/green]")


@evolve_app.command("feedback")
def evolve_feedback(
    persona: Annotated[str, typer.Argument(help="Persona YAML path or persona name")],
    feedback: Annotated[str, typer.Argument(help="Feedback to record")],
    type: Annotated[str | None, typer.Option("--type", help="soft or hard")] = None,
    trait: Annotated[
        str | None, typer.Option("--trait", help="Trait to evolve for hard changes")
    ] = None,
    change: Annotated[
        float | None, typer.Option("--change", help="Hard-delta value before caps are applied")
    ] = None,
    source: Annotated[
        str, typer.Option("--source", help="Source label for audit log")
    ] = "manual_feedback",
    thumbs_down: Annotated[
        bool, typer.Option("--thumbs-down", help="Treat this as negative feedback")
    ] = False,
    response_id: Annotated[
        str | None, typer.Option("--response-id", help="Optional response identifier")
    ] = None,
) -> None:
    """Queue a feedback signal as a pending evolution candidate."""
    from personanexus.evolution import evolve_persona

    kind: Literal["soft", "hard"] | None = None  # noqa: UP040
    if type in ("soft", "hard"):
        kind = type  # type: ignore[assignment]
    try:
        candidate = evolve_persona(
            persona,
            feedback=feedback,
            source=source,
            candidate_type=kind,
            trait=trait,
            change=change,
            thumbs_down=thumbs_down,
            response_id=response_id,
        )
    except Exception as exc:
        console.print(f"[red]Feedback failed: {exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓ Queued {candidate.type} candidate {candidate.id}[/green]")
    if candidate.trait:
        console.print(f"[dim]Trait: {candidate.trait}[/dim]")
    if candidate.change is not None:
        console.print(f"[dim]Change: {candidate.change:+.2f}[/dim]")
    if candidate.guidance:
        console.print(f"[dim]Guidance: {candidate.guidance}[/dim]")


@evolve_app.command("pending")
def evolve_pending(
    persona: Annotated[str, typer.Argument(help="Persona YAML path or persona name")],
) -> None:
    """List pending evolution candidates."""
    from personanexus.evolution import get_candidates

    candidates = get_candidates(persona)
    if not candidates:
        console.print("[yellow]No pending evolution candidates.[/yellow]")
        return

    table = Table(title="Pending Evolution Candidates", show_header=True, header_style="bold")
    table.add_column("ID", style="cyan")
    table.add_column("Type")
    table.add_column("Target")
    table.add_column("Change")
    table.add_column("Signals")
    table.add_column("Reason")

    for candidate in candidates:
        table.add_row(
            candidate.id,
            candidate.type,
            candidate.trait or "tone_guidance",
            f"{candidate.change:+.2f}" if candidate.change is not None else "—",
            str(candidate.signals_supporting),
            candidate.reason,
        )

    console.print(table)


@evolve_app.command("promote")
def evolve_promote(
    persona: Annotated[str, typer.Argument(help="Persona YAML path or persona name")],
    candidate_id: Annotated[
        str | None, typer.Argument(help="Candidate ID", show_default=False)
    ] = None,
    accept: Annotated[
        bool, typer.Option("--accept", help="Accept the specified candidate")
    ] = False,
    reject: Annotated[
        bool, typer.Option("--reject", help="Reject the specified candidate")
    ] = False,
    accept_all: Annotated[
        bool, typer.Option("--accept-all", help="Promote all pending candidates")
    ] = False,
) -> None:
    """Promote pending candidates into active deltas."""
    from personanexus.evolution import promote_all, promote_candidate

    try:
        if accept_all:
            accepted, errors = promote_all(persona)
            console.print(f"[green]✓ Accepted {len(accepted)} candidate(s)[/green]")
            for err in errors:
                console.print(f"[yellow]Skipped: {err}[/yellow]")
            return

        if not candidate_id:
            console.print("[red]Error: candidate_id is required unless --accept-all is used[/red]")
            raise typer.Exit(code=1)
        if accept == reject:
            console.print("[red]Error: choose exactly one of --accept or --reject[/red]")
            raise typer.Exit(code=1)

        promote_candidate(persona, candidate_id, accept=accept)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Promote failed: {exc}[/red]")
        raise typer.Exit(code=1)

    action = "accepted" if accept else "rejected"
    console.print(f"[green]✓ Candidate {candidate_id} {action}[/green]")


@evolve_app.command("reset")
def evolve_reset(
    persona: Annotated[str, typer.Argument(help="Persona YAML path or persona name")],
) -> None:
    """Clear active evolution deltas and pending candidates."""
    from personanexus.evolution import reset_evolution

    try:
        state = reset_evolution(persona)
    except Exception as exc:
        console.print(f"[red]Reset failed: {exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓ Evolution reset. Current version: {state.version}[/green]")


@evolve_app.command("rollback")
def evolve_rollback(
    persona: Annotated[str, typer.Argument(help="Persona YAML path or persona name")],
    version: Annotated[
        int, typer.Option("--version", help="Historical version snapshot to restore")
    ],
) -> None:
    """Restore a previous evolution snapshot."""
    from personanexus.evolution import rollback_evolution

    try:
        state = rollback_evolution(persona, version)
    except Exception as exc:
        console.print(f"[red]Rollback failed: {exc}[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"[green]✓ Rolled back using snapshot {version}. Current version: {state.version}[/green]"
    )


@evolve_app.command("export")
def evolve_export(
    persona: Annotated[str, typer.Argument(help="Persona YAML path or persona name")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Where to write the evolved YAML")],
    search_path: Annotated[
        list[Path] | None,
        typer.Option("--search-path", "-s", help="Additional search paths for archetypes/mixins"),
    ] = None,
) -> None:
    """Export a new YAML file with active evolution deltas applied."""
    from personanexus.evolution import export_evolved_persona

    try:
        out = export_evolved_persona(persona, output, search_paths=search_path or [])
    except Exception as exc:
        console.print(f"[red]Export failed: {exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓ Exported evolved persona to {out}[/green]")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
