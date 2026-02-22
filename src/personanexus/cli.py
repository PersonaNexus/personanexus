"""Command-line interface for the AI PersonaNexus Framework."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

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
from personanexus.parser import ParseError
from personanexus.resolver import IdentityResolver, ResolutionError
from personanexus.team_types import TeamConfiguration
from personanexus.validator import IdentityValidator

app = typer.Typer(
    name="personanexus",
    help="AI PersonaNexus Framework CLI - validate, resolve, and scaffold agent identities",
    add_completion=False,
)
console = Console()


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
# resolve command
# ---------------------------------------------------------------------------


@app.command()
def resolve(
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file to resolve")],
    output: Annotated[
        str, typer.Option("--output", "-o", help="Output format: yaml or json")
    ] = "yaml",
    search_path: Annotated[
        list[Path],
        typer.Option(
            "--search-path", "-s",
            help="Additional search paths for archetypes/mixins (repeatable)",
        ),
    ] = None,
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
            f"[red]Error: Invalid output format '{output}'."
            f" Must be 'yaml' or 'json'[/red]"
        )
        raise typer.Exit(code=1)

    # Build search paths
    search_paths = search_path or []

    try:
        resolver = IdentityResolver(search_paths=search_paths)
        identity = resolver.resolve_file(file)
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

    # Generate filename from name
    filename = name.lower().replace(" ", "_").replace("-", "_")
    if not filename.endswith(".yaml"):
        filename += ".yaml"

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

    # Write the file
    output_path.write_text(content, encoding="utf-8")

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
        lines.extend([f"extends: {extends}", ""])

    lines.extend(
        [
            "metadata:",
            f"  id: {agent_id}",
            f"  name: {name}",
            "  version: 0.1.0",
            f"  description: Agent identity for {name}",
            f"  created_at: {timestamp}",
            f"  updated_at: {timestamp}",
            "  status: draft",
            "",
            "role:",
            f"  title: {name}",
            f"  purpose: Assist users with tasks related to {name.lower()}",
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
        lines.extend([f"extends: {extends}", ""])

    lines.extend(
        [
            "metadata:",
            f"  id: {agent_id}",
            f"  name: {name}",
            "  version: 0.1.0",
            f"  description: Full PersonaNexus for {name}",
            f"  created_at: {timestamp}",
            f"  updated_at: {timestamp}",
            "  author: PersonaNexus Framework",
            "  tags:",
            "    - assistant",
            "  status: draft",
            "",
            "role:",
            f"  title: {name}",
            f"  purpose: A comprehensive assistant for {name.lower()}-related tasks",
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
        f"  name: {name}",
        f"  description: Base archetype for {name.lower()} agents",
        "  abstract: true",
        "",
        "metadata:",
        f"  id: {agent_id}",
        f"  name: {name} Archetype",
        "  version: 1.0.0",
        f"  description: Archetype defining core traits for {name.lower()} agents",
        f"  created_at: {timestamp}",
        f"  updated_at: {timestamp}",
        "  status: active",
        "",
        "role:",
        f"  title: {name}",
        f"  purpose: Base purpose for {name.lower()} agents",
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
        f"  name: {name}",
        f"  description: Mixin providing {name.lower()} capabilities",
        "",
        "metadata:",
        f"  id: {agent_id}",
        f"  name: {name} Mixin",
        "  version: 1.0.0",
        f"  description: Adds {name.lower()} functionality to any agent",
        f"  created_at: {timestamp}",
        f"  updated_at: {timestamp}",
        "  status: active",
        "",
        "role:",
        f"  title: {name} Enhanced",
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
            "--target", "-t",
            help="Target format: text, anthropic, openai, openclaw, soul, or json",
        ),
    ] = "text",
    search_path: Annotated[
        list[Path],
        typer.Option(
            "--search-path", "-s",
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
) -> None:
    """Compile a resolved identity into a system prompt or platform format."""
    if not file.exists():
        console.print(f"[red]Error: File not found: {file}[/red]")
        raise typer.Exit(code=1)

    if not file.is_file():
        console.print(f"[red]Error: Not a file: {file}[/red]")
        raise typer.Exit(code=1)

    valid_targets = ("text", "anthropic", "openai", "openclaw", "soul", "json")
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
        soul_path.write_text(result["soul_md"], encoding="utf-8")
        style_path.write_text(result["style_md"], encoding="utf-8")
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
        }
        suffix = ext_map.get(target, ".compiled.txt")
        output = file.parent / f"{stem}{suffix}"

    # Write to file
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(output_text, encoding="utf-8")
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
        list[Path],
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
            f"[red]Error: Invalid format '{output_format}'."
            f" Must be 'table' or 'json'[/red]"
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
        "green" if result.confidence >= 0.8
        else "yellow" if result.confidence >= 0.5
        else "red"
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

    trait_order = [
        "warmth", "verbosity", "assertiveness", "humor", "empathy",
        "directness", "rigor", "creativity", "epistemic_humility", "patience",
    ]
    for trait_name in trait_order:
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
    help="OCEAN/DISC personality mapping utilities",
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
            help="DISC preset name (e.g. the_commander)"
            " - overrides individual values if provided",
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
                dominance is None or influence is None
                or steadiness is None or conscientiousness is None
            ):
                console.print(
                    "[red]Error: All DISC values required"
                    " when --preset not provided[/red]"
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


@personality_app.command("show-profile")
def personality_show_profile(
    file: Annotated[Path, typer.Argument(help="Path to PersonaNexus YAML file")],
    search_path: Annotated[
        list[Path],
        typer.Option("--search-path", "-s", help="Additional search paths for archetypes/mixins"),
    ] = None,
) -> None:
    """Show the personality profile and computed traits for an identity file."""
    from personanexus.personality import (
        compute_personality_traits,
        traits_to_disc,
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
    console.print()


def _print_traits_table(title: str, traits: dict[str, float]) -> None:
    """Print a Rich table of trait values."""
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Trait", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Level", style="dim")

    trait_order = [
        "warmth", "verbosity", "assertiveness", "humor", "empathy",
        "directness", "rigor", "creativity", "epistemic_humility", "patience",
    ]
    for trait_name in trait_order:
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
    filename = name.lower().replace(" ", "_").replace("-", "_") + ".yaml"
    output_path = output_dir / filename

    yaml_str = identity.to_yaml_string()
    output_path.write_text(yaml_str, encoding="utf-8")

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
        console.print(Panel(
            f"[bold]Compatibility Score[/bold]\n\n"
            f"  {file1.name}  \u2194  {file2.name}\n"
            f"\n"
            f"  [bold][green]{score}%[/green][/bold]\n"
            f"\n"
            f"[dim]Based on personality trait alignment (OCEAN/DISC)[/dim]",
            title="Score",
            border_style="green",
            padding=(1, 2),
        ))

        # Interpret the score
        if score >= 80:
            console.print(
                "\n[yellow]Interpretation: Very high alignment"
                " - agents will likely work well together![/yellow]"
            )
        elif score >= 60:
            console.print(
                "\n[yellow]Interpretation: Good alignment"
                " - minor adjustments may help.[/yellow]"
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
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
