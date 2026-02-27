"""Interactive identity builder wizard and LLM enhancer."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from personanexus.types import TRAIT_ORDER

console = Console()

# ---------------------------------------------------------------------------
# Trait descriptions for the wizard
# ---------------------------------------------------------------------------

_TRAIT_DESCRIPTIONS: dict[str, str] = {
    "warmth": "How warm and welcoming vs reserved and professional",
    "verbosity": "How detailed vs concise in responses",
    "assertiveness": "How proactive and directive vs reactive and deferential",
    "humor": "How playful and witty vs serious and professional",
    "empathy": "How emotionally attuned vs task-focused",
    "directness": "How blunt and candid vs diplomatic and indirect",
    "rigor": "How meticulous and precise vs flexible and adaptive",
    "creativity": "How innovative and unconventional vs proven and conventional",
    "epistemic_humility": "How transparent about uncertainty vs confident and decisive",
    "patience": "How patient and unhurried vs efficient and fast-paced",
}


# ---------------------------------------------------------------------------
# BuiltIdentity container
# ---------------------------------------------------------------------------


class BuiltIdentity:
    """Container for a wizard-built identity with serialization helpers."""

    def __init__(self, data: dict[str, Any]):
        self.data = data

    def to_yaml_string(self) -> str:
        """Serialize the identity to a YAML string."""
        return yaml.dump(
            self.data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the raw identity dict."""
        return self.data

    @classmethod
    def from_yaml(cls, path: str | Path) -> BuiltIdentity:
        """Load a BuiltIdentity from a YAML file on disk.

        Parameters
        ----------
        path:
            Filesystem path to a YAML identity file.

        Returns
        -------
        BuiltIdentity
            A new instance populated with the data from the file.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        yaml.YAMLError
            If the file is not valid YAML.
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"Expected a YAML mapping at top level, got {type(data).__name__}")
        return cls(data)


# ---------------------------------------------------------------------------
# IdentityBuilder wizard
# ---------------------------------------------------------------------------


class IdentityBuilder:
    """Interactive wizard for building agent identities step-by-step."""

    def __init__(self, console: Console | None = None, edit_path: str | None = None):
        self.console = console or Console()
        self.edit_path = edit_path

    # ------------------------------------------------------------------
    # Input helpers with re-prompting
    # ------------------------------------------------------------------

    def _prompt_float(
        self, label: str, low: float, high: float, allow_skip: bool = True
    ) -> float | None:
        """Prompt for a float value, re-asking on invalid input. Returns None if skipped."""
        while True:
            raw = Prompt.ask(f"  {label}", default="")
            if not raw.strip():
                if allow_skip:
                    return None
                self.console.print("  [red]A value is required.[/red]")
                continue
            try:
                value = float(raw.strip())
            except ValueError:
                self.console.print(
                    f"  [red]'{raw.strip()}' is not a number. "
                    f"Enter a value between {low} and {high}.[/red]"
                )
                continue
            if not (low <= value <= high):
                self.console.print(
                    f"  [red]{value} is out of range. Enter a value between {low} and {high}.[/red]"
                )
                continue
            return value

    def _prompt_choice(self, label: str, choices: list[str], default: str) -> str:
        """Prompt for a choice from a list, re-asking on invalid input."""
        while True:
            value = Prompt.ask(f"{label} ({', '.join(choices)})", default=default)
            if value in choices:
                return value
            self.console.print(
                f"  [red]'{value}' is not valid. Choose from: {', '.join(choices)}[/red]"
            )

    # ------------------------------------------------------------------

    def run(self) -> BuiltIdentity:
        """Run the full interactive wizard and return a BuiltIdentity."""
        self.console.print(
            Panel(
                "[bold]PersonaNexus Builder[/bold]\n\n"
                "This wizard will walk you through creating an AI PersonaNexus.\n"
                "Press Enter to use defaults or skip optional fields.",
                border_style="blue",
            )
        )

        # ---- Edit-existing mode -------------------------------------------
        if self.edit_path is not None:
            existing = BuiltIdentity.from_yaml(self.edit_path)
            return self._phase_edit_existing(existing.data)

        # ---- Normal creation mode -----------------------------------------
        data: dict[str, Any] = {"schema_version": "1.0"}

        self._phase_basics(data)  # Phase 1
        self._phase_personality_mode(data)  # Phase 2a
        self._phase_personality(data)  # Phase 2b
        self._phase_communication(data)  # Phase 3
        self._phase_principles(data)  # Phase 4
        self._phase_guardrails(data)  # Phase 5
        self._phase_narrative(data)  # Phase 6
        self._phase_behavioral_modes(data)  # Phase 7
        self._phase_interaction(data)  # Phase 8
        self._phase_expertise(data)  # Phase 9

        self.console.print("\n[green]Identity created successfully![/green]")

        return BuiltIdentity(data)

    # ------------------------------------------------------------------
    # Phase 1: Basics
    # ------------------------------------------------------------------

    def _phase_basics(self, data: dict[str, Any]) -> None:
        self.console.print("\n[bold blue]Phase 1: Basics[/bold blue]")
        self.console.rule()

        name = Prompt.ask("Agent name", default="MyAgent")
        title = Prompt.ask("Role title", default=name)
        default_purpose = f"Assist users with {name.lower()}-related tasks"
        purpose = Prompt.ask("Purpose (what does this agent do?)", default=default_purpose)
        description = Prompt.ask("Description", default=f"An AI agent named {name}")

        # Primary scope
        scope_input = Prompt.ask(
            "Primary scope (comma-separated)",
            default="General assistance",
        )
        primary_scope = [s.strip() for s in scope_input.split(",") if s.strip()]

        # Auto-generate fields
        unique_suffix = uuid.uuid4().hex[:8]
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        agent_id = f"agt_{safe_name}_{unique_suffix}"
        now = datetime.now(UTC).isoformat()

        data["metadata"] = {
            "id": agent_id,
            "name": name,
            "version": "0.1.0",
            "description": description,
            "created_at": now,
            "updated_at": now,
            "status": "draft",
        }

        data["role"] = {
            "title": title,
            "purpose": purpose,
            "scope": {"primary": primary_scope},
        }

    # ------------------------------------------------------------------
    # Phase 2a: Personality Mode
    # ------------------------------------------------------------------

    def _phase_personality_mode(self, data: dict[str, Any]) -> None:
        """Select personality framework mode: custom, ocean, disc, jungian, or hybrid."""
        self.console.print("\n[bold blue]Phase 2a: Personality Mode[/bold blue]")
        self.console.rule()
        self.console.print(
            "[dim]Choose how to define your agent's personality:\n"
            "  custom  — Set each trait manually (0-1 scale)\n"
            "  ocean   — Use Big Five (OCEAN) dimensions, auto-map to traits\n"
            "  disc    — Use DISC profile or a named preset\n"
            "  jungian — Use Jungian 16-type (e.g. INTJ, ENFP)\n"
            "  hybrid  — Compute from a framework, then override specific traits[/dim]\n"
        )

        mode = self._prompt_choice(
            "Personality mode", ["custom", "ocean", "disc", "jungian", "hybrid"], default="custom"
        )

        # Store mode; remaining phases will populate the profile
        data["_personality_mode"] = mode

    # ------------------------------------------------------------------
    # Phase 2b: Personality Traits
    # ------------------------------------------------------------------

    def _phase_personality(self, data: dict[str, Any]) -> None:
        mode = data.pop("_personality_mode", "custom")

        if mode == "custom":
            self._phase_personality_custom(data)
        elif mode == "ocean":
            self._phase_personality_ocean(data)
        elif mode == "disc":
            self._phase_personality_disc(data)
        elif mode == "jungian":
            self._phase_personality_jungian(data)
        elif mode == "hybrid":
            self._phase_personality_hybrid(data)

    def _phase_personality_custom(self, data: dict[str, Any]) -> None:
        """Original custom trait entry."""
        self.console.print("\n[bold blue]Phase 2b: Personality Traits (Custom)[/bold blue]")
        self.console.rule()
        self.console.print("[dim]Rate each trait from 0.0 to 1.0. Press Enter to skip.[/dim]\n")

        # Show trait table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Trait", style="cyan")
        table.add_column("Description")
        table.add_column("Scale", style="dim")
        for trait_name, desc in _TRAIT_DESCRIPTIONS.items():
            table.add_row(trait_name, desc, "0.0 ← → 1.0")
        self.console.print(table)
        self.console.print()

        traits: dict[str, float] = {}
        for trait_name in TRAIT_ORDER:
            value = self._prompt_float(trait_name, 0.0, 1.0, allow_skip=True)
            if value is not None:
                traits[trait_name] = value

        # Ensure at least 2 traits
        if len(traits) < 2:
            self.console.print("[yellow]At least 2 traits required. Adding defaults.[/yellow]")
            if "warmth" not in traits:
                traits["warmth"] = 0.7
            if "directness" not in traits:
                traits["directness"] = 0.6
            if "rigor" not in traits:
                traits["rigor"] = 0.5

        data["personality"] = {"traits": traits}

    def _phase_personality_ocean(self, data: dict[str, Any]) -> None:
        """Collect OCEAN (Big Five) scores and compute traits."""
        from personanexus.personality import ocean_to_traits
        from personanexus.types import OceanProfile

        self.console.print("\n[bold blue]Phase 2b: OCEAN (Big Five) Profile[/bold blue]")
        self.console.rule()
        self.console.print("[dim]Rate each OCEAN dimension from 0.0 to 1.0.[/dim]\n")

        ocean_dims = {
            "openness": "Curiosity, creativity, openness to new experiences",
            "conscientiousness": "Organization, dependability, self-discipline",
            "extraversion": "Sociability, assertiveness, positive emotions",
            "agreeableness": "Cooperation, trust, altruism",
            "neuroticism": "Emotional instability, anxiety, moodiness",
        }

        scores: dict[str, float] = {}
        for dim, desc in ocean_dims.items():
            self.console.print(f"  [dim]{desc}[/dim]")
            value = self._prompt_float(dim, 0.0, 1.0, allow_skip=False)
            scores[dim] = value  # type: ignore[assignment]  # allow_skip=False guarantees non-None

        profile = OceanProfile(**scores)
        computed = ocean_to_traits(profile)

        # Show computed traits preview
        self._show_computed_traits_preview(computed)

        data["personality"] = {
            "traits": computed,
            "profile": {
                "mode": "ocean",
                "ocean": scores,
            },
        }

    def _phase_personality_disc(self, data: dict[str, Any]) -> None:
        """Collect DISC scores (manual or preset) and compute traits."""
        from personanexus.personality import (
            disc_to_traits,
            get_disc_preset,
            list_disc_presets,
        )
        from personanexus.types import DiscProfile

        self.console.print("\n[bold blue]Phase 2b: DISC Profile[/bold blue]")
        self.console.rule()

        # Offer preset or manual
        presets = list_disc_presets()
        preset_names = list(presets.keys())
        self.console.print("[dim]Available DISC presets:[/dim]")
        for name, p in presets.items():
            self.console.print(
                f"  [cyan]{name}[/cyan]: D={p.dominance}, I={p.influence}, "
                f"S={p.steadiness}, C={p.conscientiousness}"
            )
        self.console.print()

        use_preset = Confirm.ask("Use a preset?", default=True)

        if use_preset:
            preset_name = self._prompt_choice("Preset", preset_names, default="the_analyst")
            disc = get_disc_preset(preset_name)
            computed = disc_to_traits(disc)
            disc_data: dict[str, Any] = {
                "mode": "disc",
                "disc_preset": preset_name,
            }
        else:
            self.console.print("[dim]Rate each DISC dimension from 0.0 to 1.0.[/dim]\n")
            disc_dims = {
                "dominance": "Drive, assertiveness, control orientation",
                "influence": "Sociability, enthusiasm, collaboration",
                "steadiness": "Patience, reliability, team orientation",
                "conscientiousness": "Accuracy, quality, systematic thinking",
            }
            scores: dict[str, float] = {}
            for dim, desc in disc_dims.items():
                self.console.print(f"  [dim]{desc}[/dim]")
                value = self._prompt_float(dim, 0.0, 1.0, allow_skip=False)
                scores[dim] = value  # type: ignore[assignment]  # allow_skip=False guarantees non-None

            disc = DiscProfile(**scores)
            computed = disc_to_traits(disc)
            disc_data = {
                "mode": "disc",
                "disc": scores,
            }

        self._show_computed_traits_preview(computed)

        data["personality"] = {
            "traits": computed,
            "profile": disc_data,
        }

    def _collect_jungian_input(self) -> tuple[dict[str, float], dict[str, Any]]:
        """Interactive 3-path Jungian type collection.

        Returns:
            (computed_traits, profile_fragment) where profile_fragment contains
            either ``jungian_preset`` or ``jungian`` dimension scores.
        """
        from personanexus.personality import (
            JUNGIAN_ROLE_RECOMMENDATIONS,
            get_jungian_preset,
            jungian_to_traits,
            list_jungian_presets,
        )
        from personanexus.types import JungianProfile

        self.console.print(
            "[dim]Choose how to specify your Jungian type:\n"
            "  1  — I know my type (enter a 4-letter code)\n"
            "  2  — Recommend based on role\n"
            "  3  — Enter dimensions manually[/dim]\n"
        )

        path = self._prompt_choice("Input path", ["1", "2", "3"], default="1")

        if path == "1":
            valid_types = set(list_jungian_presets().keys())
            while True:
                code = Prompt.ask("  Jungian type code (e.g. INTJ, ENFP)")
                code_lower = code.strip().lower()
                if code_lower in valid_types:
                    break
                self.console.print(
                    f"  [red]'{code.strip()}' is not a valid Jungian type. "
                    f"Valid types: {', '.join(sorted(t.upper() for t in valid_types))}[/red]"
                )

            jungian = get_jungian_preset(code_lower)
            computed = jungian_to_traits(jungian)
            profile_fragment: dict[str, Any] = {"jungian_preset": code_lower}

        elif path == "2":
            self.console.print("\n[bold]Role Categories:[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("#", style="dim", width=3)
            table.add_column("Category", style="cyan")
            categories = sorted(JUNGIAN_ROLE_RECOMMENDATIONS.keys())
            for idx, cat in enumerate(categories, 1):
                table.add_row(str(idx), cat.replace("_", " ").title())
            self.console.print(table)
            self.console.print()

            while True:
                cat_input = Prompt.ask("  Category number")
                if cat_input.strip().isdigit():
                    cat_idx = int(cat_input.strip()) - 1
                    if 0 <= cat_idx < len(categories):
                        break
                self.console.print(f"  [red]Enter a number between 1 and {len(categories)}.[/red]")

            selected_category = categories[cat_idx]
            recommendations = JUNGIAN_ROLE_RECOMMENDATIONS[selected_category]

            self.console.print(
                f"\n[bold]Recommended types for "
                f"{selected_category.replace('_', ' ').title()}:[/bold]"
            )
            rec_table = Table(show_header=True, header_style="bold")
            rec_table.add_column("#", style="dim", width=3)
            rec_table.add_column("Type", style="cyan")
            rec_table.add_column("Description")
            for idx, (type_code, desc) in enumerate(recommendations, 1):
                rec_table.add_row(str(idx), type_code.upper(), desc)
            self.console.print(rec_table)
            self.console.print()

            while True:
                rec_input = Prompt.ask("  Pick a type number")
                if rec_input.strip().isdigit():
                    rec_idx = int(rec_input.strip()) - 1
                    if 0 <= rec_idx < len(recommendations):
                        break
                self.console.print(
                    f"  [red]Enter a number between 1 and {len(recommendations)}.[/red]"
                )

            chosen_code = recommendations[rec_idx][0]
            jungian = get_jungian_preset(chosen_code)
            computed = jungian_to_traits(jungian)
            profile_fragment = {"jungian_preset": chosen_code}

        else:
            self.console.print("\n[dim]Enter each Jungian dimension from 0.0 to 1.0.[/dim]\n")
            jungian_dims = {
                "ei": "Extraversion (0) ←→ Introversion (1)",
                "sn": "Sensing (0) ←→ iNtuition (1)",
                "tf": "Thinking (0) ←→ Feeling (1)",
                "jp": "Judging (0) ←→ Perceiving (1)",
            }
            scores: dict[str, float] = {}
            for dim, desc in jungian_dims.items():
                self.console.print(f"  [dim]{desc}[/dim]")
                value = self._prompt_float(dim, 0.0, 1.0, allow_skip=False)
                scores[dim] = value  # type: ignore[assignment]  # allow_skip=False guarantees non-None

            jungian = JungianProfile(**scores)
            computed = jungian_to_traits(jungian)
            profile_fragment = {"jungian": scores}

        return computed, profile_fragment

    def _phase_personality_jungian(self, data: dict[str, Any]) -> None:
        """Collect Jungian 16-type data (preset, role-based, or manual) and compute traits."""
        self.console.print("\n[bold blue]Phase 2b: Jungian 16-Type Profile[/bold blue]")
        self.console.rule()

        computed, profile_fragment = self._collect_jungian_input()
        jungian_data = {"mode": "jungian", **profile_fragment}

        self._show_computed_traits_preview(computed)

        data["personality"] = {
            "traits": computed,
            "profile": jungian_data,
        }

    def _phase_personality_hybrid(self, data: dict[str, Any]) -> None:
        """Compute traits from a framework, then allow manual overrides."""
        from personanexus.personality import disc_to_traits, ocean_to_traits
        from personanexus.types import DiscProfile, OceanProfile

        self.console.print("\n[bold blue]Phase 2b: Hybrid Personality[/bold blue]")
        self.console.rule()
        self.console.print(
            "[dim]First, select a framework to compute base traits. "
            "Then override specific traits manually.[/dim]\n"
        )

        framework = self._prompt_choice(
            "Base framework", ["ocean", "disc", "jungian"], default="ocean"
        )

        profile_data: dict[str, Any] = {"mode": "hybrid"}

        if framework == "ocean":
            ocean_dims = [
                "openness",
                "conscientiousness",
                "extraversion",
                "agreeableness",
                "neuroticism",
            ]
            scores: dict[str, float] = {}
            for dim in ocean_dims:
                value = self._prompt_float(dim, 0.0, 1.0, allow_skip=False)
                scores[dim] = value  # type: ignore[assignment]  # allow_skip=False guarantees non-None
            profile = OceanProfile(**scores)
            computed = ocean_to_traits(profile)
            profile_data["ocean"] = scores
        elif framework == "disc":
            disc_dims = [
                "dominance",
                "influence",
                "steadiness",
                "conscientiousness",
            ]
            scores = {}
            for dim in disc_dims:
                value = self._prompt_float(dim, 0.0, 1.0, allow_skip=False)
                scores[dim] = value  # type: ignore[assignment]  # allow_skip=False guarantees non-None
            disc = DiscProfile(**scores)
            computed = disc_to_traits(disc)
            profile_data["disc"] = scores
        else:
            computed, jungian_fragment = self._collect_jungian_input()
            profile_data.update(jungian_fragment)

        self.console.print("\n[bold]Computed base traits:[/bold]")
        self._show_computed_traits_preview(computed)

        # Now allow overrides
        self.console.print("\n[dim]Override specific traits (Enter to keep computed value):[/dim]")
        overrides: dict[str, float] = {}
        for trait_name in TRAIT_ORDER:
            current = computed.get(trait_name, 0.5)
            self.console.print(f"  [dim]Current {trait_name}: {current}[/dim]")
            value = self._prompt_float(f"{trait_name} override", 0.0, 1.0, allow_skip=True)
            if value is not None:
                overrides[trait_name] = value
                computed[trait_name] = value  # Apply override

        profile_data["override_priority"] = "explicit_wins"

        data["personality"] = {
            "traits": overrides if overrides else computed,
            "profile": profile_data,
        }

    def _show_computed_traits_preview(self, traits: dict[str, float]) -> None:
        """Display a Rich table of computed trait values."""
        self.console.print("\n[bold]Computed Personality Traits:[/bold]")
        table = Table(show_header=True, header_style="bold")
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
                table.add_row(trait_name, f"{val:.3f}", level)
        self.console.print(table)

    # ------------------------------------------------------------------
    # Phase 3: Communication
    # ------------------------------------------------------------------

    def _phase_communication(self, data: dict[str, Any]) -> None:
        self.console.print("\n[bold blue]Phase 3: Communication Style[/bold blue]")
        self.console.rule()

        tone = Prompt.ask("Default tone", default="professional and helpful")

        register_choices = ["formal", "consultative", "casual", "technical", "friendly"]
        register = self._prompt_choice("Register", register_choices, default="consultative")

        emoji_choices = ["never", "sparingly", "moderate", "frequent"]
        emoji = self._prompt_choice("Emoji usage", emoji_choices, default="sparingly")

        data["communication"] = {
            "tone": {
                "default": tone,
                "register": register,
            },
            "style": {
                "use_emoji": emoji,
            },
        }

    # ------------------------------------------------------------------
    # Phase 4: Principles
    # ------------------------------------------------------------------

    def _phase_principles(self, data: dict[str, Any]) -> None:
        self.console.print("\n[bold blue]Phase 4: Core Principles[/bold blue]")
        self.console.rule()
        self.console.print(
            "[dim]Enter guiding principles for the agent. Empty input to finish.[/dim]\n"
        )

        principles: list[dict[str, Any]] = []
        priority = 1

        while True:
            statement = Prompt.ask(f"  Principle {priority}", default="")
            if not statement.strip():
                break
            safe_id = statement.strip().lower()[:30].replace(" ", "_")
            safe_id = "".join(c for c in safe_id if c.isalnum() or c == "_")
            principles.append(
                {
                    "id": f"principle_{safe_id}",
                    "priority": priority,
                    "statement": statement.strip(),
                }
            )
            priority += 1

        # Add default if empty
        if not principles:
            self.console.print(
                "[yellow]No principles entered. Adding default safety principle.[/yellow]"
            )
            principles.append(
                {
                    "id": "safety_first",
                    "priority": 1,
                    "statement": "Always prioritize user safety and privacy",
                }
            )

        data["principles"] = principles

    # ------------------------------------------------------------------
    # Phase 5: Guardrails
    # ------------------------------------------------------------------

    def _phase_guardrails(self, data: dict[str, Any]) -> None:
        self.console.print("\n[bold blue]Phase 5: Guardrails[/bold blue]")
        self.console.rule()
        self.console.print(
            "[dim]Enter hard constraints the agent must never violate. Empty to finish.[/dim]\n"
        )

        guardrails: list[dict[str, Any]] = []
        counter = 1

        while True:
            rule = Prompt.ask(f"  Guardrail {counter}", default="")
            if not rule.strip():
                break
            safe_id = rule.strip().lower()[:30].replace(" ", "_")
            safe_id = "".join(c for c in safe_id if c.isalnum() or c == "_")
            guardrails.append(
                {
                    "id": f"guardrail_{safe_id}",
                    "rule": rule.strip(),
                    "enforcement": "output_filter",
                    "severity": "critical",
                }
            )
            counter += 1

        # Add default if empty
        if not guardrails:
            self.console.print("[yellow]No guardrails entered. Adding default.[/yellow]")
            guardrails.append(
                {
                    "id": "no_harmful_content",
                    "rule": "Never generate harmful, illegal, or unethical content",
                    "enforcement": "output_filter",
                    "severity": "critical",
                }
            )

        data["guardrails"] = {"hard": guardrails}

    # ------------------------------------------------------------------
    # Phase 6: Narrative / Backstory
    # ------------------------------------------------------------------

    def _phase_narrative(self, data: dict[str, Any]) -> None:
        """Collect optional backstory, current focus items, and pet peeves."""
        self.console.print("\n[bold blue]Phase 6: Narrative / Backstory[/bold blue]")
        self.console.rule()

        add_narrative = Confirm.ask("Add narrative/backstory details?", default=False)
        if not add_narrative:
            return

        narrative: dict[str, Any] = {}

        # Backstory (optional, single prompt)
        self.console.print(
            "[dim]Enter a backstory for the agent (optional, press Enter to skip).[/dim]"
        )
        backstory = Prompt.ask("  Backstory", default="")
        if backstory.strip():
            narrative["backstory"] = backstory.strip()

        # Current focus items (loop until empty)
        self.console.print("\n[dim]Enter current focus items. Empty to finish.[/dim]")
        focus_items: list[str] = []
        counter = 1
        while True:
            item = Prompt.ask(f"  Focus {counter}", default="")
            if not item.strip():
                break
            focus_items.append(item.strip())
            counter += 1
        if focus_items:
            narrative["current_focus"] = focus_items

        # Pet peeves (loop until empty)
        self.console.print("\n[dim]Enter pet peeves. Empty to finish.[/dim]")
        pet_peeves: list[str] = []
        counter = 1
        while True:
            peeve = Prompt.ask(f"  Pet peeve {counter}", default="")
            if not peeve.strip():
                break
            pet_peeves.append(peeve.strip())
            counter += 1
        if pet_peeves:
            narrative["pet_peeves"] = pet_peeves

        if narrative:
            data["narrative"] = narrative

    # ------------------------------------------------------------------
    # Phase 7: Behavioral Modes
    # ------------------------------------------------------------------

    def _phase_behavioral_modes(self, data: dict[str, Any]) -> None:
        """Define named behavioral modes with optional tone overrides."""
        self.console.print("\n[bold blue]Phase 7: Behavioral Modes[/bold blue]")
        self.console.rule()

        add_modes = Confirm.ask("Define behavioral modes?", default=False)
        if not add_modes:
            return

        modes: list[dict[str, Any]] = []

        self.console.print(
            "[dim]Add behavioral modes. Each mode has a name, description, "
            "and optional tone overrides. Empty name to finish.[/dim]\n"
        )

        while True:
            mode_name = Prompt.ask("  Mode name (empty to finish)", default="")
            if not mode_name.strip():
                break

            description = Prompt.ask("  Description", default="")

            mode_entry: dict[str, Any] = {
                "name": mode_name.strip(),
                "description": description.strip() if description.strip() else mode_name.strip(),
            }

            # Optional tone_register override
            register_override = Prompt.ask("  Tone register override (empty to skip)", default="")
            if register_override.strip():
                mode_entry["tone_register"] = register_override.strip()

            # Optional tone_default override
            tone_override = Prompt.ask("  Tone default override (empty to skip)", default="")
            if tone_override.strip():
                mode_entry["tone_default"] = tone_override.strip()

            modes.append(mode_entry)
            self.console.print(f"  [green]Added mode: {mode_name.strip()}[/green]\n")

        if not modes:
            return

        # Ask for a default mode
        mode_names = [m["name"] for m in modes]
        default_mode = self._prompt_choice("  Default mode", mode_names, default=mode_names[0])

        data["behavioral_modes"] = {
            "modes": modes,
            "default": default_mode,
        }

    # ------------------------------------------------------------------
    # Phase 8: Interaction Protocols
    # ------------------------------------------------------------------

    def _phase_interaction(self, data: dict[str, Any]) -> None:
        """Configure interaction protocols for human and agent interactions."""
        self.console.print("\n[bold blue]Phase 8: Interaction Protocols[/bold blue]")
        self.console.rule()

        add_interaction = Confirm.ask("Configure interaction protocols?", default=False)
        if not add_interaction:
            return

        interaction: dict[str, Any] = {}

        # --- Human interaction settings ---
        self.console.print("\n[bold]Human Interaction[/bold]")

        greeting_style = Prompt.ask("  Greeting style (empty to skip)", default="")
        farewell_style = Prompt.ask("  Farewell style (empty to skip)", default="")
        tone_matching = Confirm.ask("  Enable tone matching?", default=True)

        human_config: dict[str, Any] = {"tone_matching": tone_matching}
        if greeting_style.strip():
            human_config["greeting_style"] = greeting_style.strip()
        if farewell_style.strip():
            human_config["farewell_style"] = farewell_style.strip()

        interaction["human"] = human_config

        # --- Agent interaction settings ---
        self.console.print("\n[bold]Agent Interaction[/bold]")

        handoff_style = self._prompt_choice(
            "  Handoff style", ["structured", "freeform"], default="structured"
        )
        status_reporting = self._prompt_choice(
            "  Status reporting", ["verbose", "concise", "minimal"], default="concise"
        )
        conflict_resolution = self._prompt_choice(
            "  Conflict resolution",
            ["escalate", "negotiate", "defer"],
            default="escalate",
        )

        interaction["agent"] = {
            "handoff_style": handoff_style,
            "status_reporting": status_reporting,
            "conflict_resolution": conflict_resolution,
        }

        data["interaction"] = interaction

    # ------------------------------------------------------------------
    # Phase 9: Expertise (optional)
    # ------------------------------------------------------------------

    def _phase_expertise(self, data: dict[str, Any]) -> None:
        self.console.print("\n[bold blue]Phase 9: Expertise (Optional)[/bold blue]")
        self.console.rule()

        add_expertise = Confirm.ask("Add expertise domains?", default=False)
        if not add_expertise:
            return

        domains: list[dict[str, Any]] = []

        while True:
            name = Prompt.ask("  Domain name (empty to finish)", default="")
            if not name.strip():
                break

            level = self._prompt_float("Level", 0.0, 1.0, allow_skip=False)

            category_choices = ["primary", "secondary", "tertiary"]
            category = self._prompt_choice("  Category", category_choices, default="primary")

            domains.append(
                {
                    "name": name.strip(),
                    "level": level,
                    "category": category,
                }
            )

        if domains:
            data["expertise"] = {"domains": domains}

    # ------------------------------------------------------------------
    # Edit-existing mode
    # ------------------------------------------------------------------

    # Map of phase keys to (display name, phase method name) for the edit menu
    _EDITABLE_PHASES: list[tuple[str, str, str]] = [
        ("basics", "Basics", "_phase_basics"),
        ("personality", "Personality", "_phase_personality_edit_wrapper"),
        ("communication", "Communication Style", "_phase_communication"),
        ("principles", "Core Principles", "_phase_principles"),
        ("guardrails", "Guardrails", "_phase_guardrails"),
        ("narrative", "Narrative / Backstory", "_phase_narrative"),
        ("behavioral_modes", "Behavioral Modes", "_phase_behavioral_modes"),
        ("interaction", "Interaction Protocols", "_phase_interaction"),
        ("expertise", "Expertise", "_phase_expertise"),
    ]

    def _phase_personality_edit_wrapper(self, data: dict[str, Any]) -> None:
        """Run personality mode selection then personality traits when editing."""
        self._phase_personality_mode(data)
        self._phase_personality(data)

    def _phase_edit_existing(self, data: dict[str, Any]) -> BuiltIdentity:
        """Edit an existing identity by choosing which sections to re-run.

        Displays current values and lets the user pick which phases to
        re-execute. Phases that are not selected keep their current data.
        """
        self.console.print(
            Panel(
                "[bold]Editing Existing Identity[/bold]\n\n"
                f"Loaded: {data.get('metadata', {}).get('name', '(unknown)')}\n"
                f"Version: {data.get('metadata', {}).get('version', '?')}",
                border_style="yellow",
            )
        )

        # Show summary of current sections
        self.console.print("\n[bold]Current sections:[/bold]")
        section_table = Table(show_header=True, header_style="bold")
        section_table.add_column("#", style="dim", width=3)
        section_table.add_column("Section", style="cyan")
        section_table.add_column("Status", style="dim")

        for idx, (key, display_name, _method) in enumerate(self._EDITABLE_PHASES, 1):
            present = (
                key in data
                or (key == "basics" and "metadata" in data)
                or (key == "personality" and "personality" in data)
            )
            status = "[green]present[/green]" if present else "[dim]empty[/dim]"
            section_table.add_row(str(idx), display_name, status)

        self.console.print(section_table)

        # Ask which sections to re-run
        self.console.print(
            "\n[dim]Select sections to re-run (comma-separated numbers, "
            "or 'all'). Press Enter to keep everything unchanged.[/dim]"
        )
        selection = Prompt.ask("  Sections to edit", default="")

        if not selection.strip():
            self.console.print("\n[green]No changes made.[/green]")
            return BuiltIdentity(data)

        # Parse selection
        phases_to_run: list[int] = []
        if selection.strip().lower() == "all":
            phases_to_run = list(range(len(self._EDITABLE_PHASES)))
        else:
            for part in selection.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(self._EDITABLE_PHASES):
                        phases_to_run.append(idx)
                    else:
                        self.console.print(f"  [yellow]Skipping invalid number: {part}[/yellow]")
                else:
                    self.console.print(f"  [yellow]Skipping invalid input: {part}[/yellow]")

        # Run selected phases
        for idx in phases_to_run:
            _key, display_name, method_name = self._EDITABLE_PHASES[idx]
            self.console.print(f"\n[bold yellow]Re-running: {display_name}[/bold yellow]")
            method = getattr(self, method_name)
            method(data)

        # Update timestamp
        if "metadata" in data:
            data["metadata"]["updated_at"] = datetime.now(UTC).isoformat()

        self.console.print("\n[green]Identity updated successfully![/green]")
        return BuiltIdentity(data)


# ---------------------------------------------------------------------------
# LLM Enhancer
# ---------------------------------------------------------------------------


class LLMEnhancer:
    """Enhances a wizard-built identity using LLM suggestions or templates.

    Tries to use the Anthropic API if available, falls back to template-based
    generation otherwise.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        console: Console | None = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.console = console or Console()
        self._client = None

    def _get_client(self) -> Any | None:
        """Try to create an Anthropic client, return None if SDK not installed."""
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            import anthropic  # type: ignore[import-not-found]

            self._client = anthropic.Anthropic(api_key=self.api_key)
            return self._client
        except ImportError:
            return None

    def enhance(self, identity: BuiltIdentity) -> dict[str, Any]:
        """Generate enhancement suggestions for the identity.

        Returns a dict with keys:
            - personality_notes: str
            - greeting: str
            - vocabulary: dict with preferred, avoided, signature_phrases
            - strategies: dict of behavior strategies

        Uses LLM if available, otherwise falls back to templates.
        """
        client = self._get_client()
        if client:
            return self._enhance_with_llm(client, identity)
        else:
            if not self.api_key:
                self.console.print(
                    "[yellow]No API key found. Using template-based enhancement.[/yellow]"
                )
            else:
                self.console.print(
                    "[yellow]Anthropic SDK not installed."
                    " Using template-based enhancement.[/yellow]"
                )
            return self._enhance_with_templates(identity)

    def _enhance_with_llm(self, client: Any, identity: BuiltIdentity) -> dict[str, Any]:
        """Use Anthropic API to generate enhancements."""
        data = identity.data
        name = data.get("metadata", {}).get("name", "Agent")[:100]
        role = data.get("role", {}).get("title", "Assistant")[:200]
        purpose = data.get("role", {}).get("purpose", "")[:500]
        traits = data.get("personality", {}).get("traits", {})

        trait_desc = ", ".join(f"{k}={v}" for k, v in traits.items())[:500]

        # Note: user-provided values are embedded below (length-limited above).
        prompt = f"""I'm building an AI agent identity. Generate enhancements \
for the agent described below.

<agent_description>
Name: {name}
Role: {role}
Purpose: {purpose}
Traits: {trait_desc}
</agent_description>

Respond in this exact JSON format (no markdown, just raw JSON):
{{
  "personality_notes": "2-3 sentences synthesizing traits into a character description.",
  "greeting": "A warm greeting message introducing the agent and its role.",
  "vocabulary": {{
    "preferred": ["phrase1", "phrase2", "phrase3"],
    "avoided": ["phrase1", "phrase2", "phrase3"],
    "signature_phrases": ["phrase1", "phrase2"]
  }},
  "strategies": {{
    "uncertainty": {{
      "approach": "A brief description of how the agent handles uncertainty"
    }},
    "disagreement": {{
      "approach": "A brief description of how the agent handles disagreement"
    }}
  }}
}}"""

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            import json

            text = response.content[0].text
            parsed: dict[str, Any] = json.loads(text)
            return parsed
        except Exception as exc:
            self.console.print(
                f"[yellow]LLM enhancement failed: {exc}. Falling back to templates.[/yellow]"
            )
            return self._enhance_with_templates(identity)

    def _enhance_with_templates(self, identity: BuiltIdentity) -> dict[str, Any]:
        """Generate template-based enhancements without API."""
        data = identity.data
        name = data.get("metadata", {}).get("name", "Agent")
        role = data.get("role", {}).get("title", "Assistant")
        purpose = data.get("role", {}).get("purpose", "Help users")
        traits = data.get("personality", {}).get("traits", {})

        # Build personality notes from traits
        notes_parts = [f"{name} is a {role} focused on: {purpose}."]
        if traits.get("warmth", 0) >= 0.7:
            notes_parts.append(f"{name} brings warmth and approachability to every interaction.")
        elif traits.get("warmth", 0) <= 0.3:
            notes_parts.append(f"{name} maintains a reserved, professional demeanor.")
        if traits.get("rigor", 0) >= 0.7:
            notes_parts.append(f"Precision and thoroughness are hallmarks of {name}'s work.")
        if traits.get("humor", 0) >= 0.6:
            notes_parts.append(f"{name} isn't afraid to lighten the mood with appropriate humor.")

        # Additional notes for other prominent traits
        if traits.get("empathy", 0) >= 0.7:
            notes_parts.append(
                f"{name} is deeply attuned to the emotional state of those they interact with."
            )
        if traits.get("creativity", 0) >= 0.7:
            notes_parts.append(
                f"{name} favors innovative and unconventional approaches to problem-solving."
            )
        if traits.get("patience", 0) >= 0.7:
            notes_parts.append(
                f"{name} takes a calm, unhurried approach and gives every question"
                f" the time it deserves."
            )
        if traits.get("directness", 0) >= 0.8:
            notes_parts.append(f"{name} values candor and gets straight to the point.")
        elif traits.get("directness", 0) <= 0.2:
            notes_parts.append(f"{name} communicates with tact and diplomatic sensitivity.")

        # ---- Greeting style variation based on warmth & assertiveness ----
        warmth = traits.get("warmth", 0.5)
        assertiveness = traits.get("assertiveness", 0.5)
        purpose_first_line = purpose.strip().split("\n")[0]

        if warmth >= 0.7 and assertiveness >= 0.7:
            greeting = (
                f"Hey there! I'm {name}, your {role}. "
                f"{purpose_first_line} "
                f"Let's dive right in -- what are we tackling today?"
            )
        elif warmth >= 0.7 and assertiveness < 0.4:
            greeting = (
                f"Hi! I'm {name}, your {role}. "
                f"{purpose_first_line} "
                f"Whenever you're ready, I'm here to help."
            )
        elif warmth < 0.3 and assertiveness >= 0.7:
            greeting = (
                f"I'm {name}, {role}. {purpose_first_line} State your request and I'll get started."
            )
        elif warmth < 0.3:
            greeting = f"I'm {name}, {role}. {purpose_first_line} How may I assist you?"
        else:
            greeting = (
                f"Hello! I'm {name}, your {role}. {purpose_first_line} How can I help you today?"
            )

        # ---- Sophisticated vocabulary generation based on traits ----------
        preferred: list[str] = []
        avoided: list[str] = []
        signature_phrases: list[str] = []

        # High rigor -> formal, precise words
        rigor = traits.get("rigor", 0.5)
        if rigor >= 0.7:
            preferred.extend(
                [
                    "Precisely",
                    "To be specific",
                    "The data indicates",
                    "Let me verify that",
                ]
            )
            avoided.extend(
                [
                    "Roughly speaking",
                    "More or less",
                    "I think maybe",
                ]
            )
            signature_phrases.append("Let me be precise about this")
        elif rigor <= 0.3:
            preferred.extend(
                [
                    "Roughly",
                    "In broad strokes",
                    "The gist is",
                ]
            )
            avoided.extend(
                [
                    "To be pedantic",
                    "Technically speaking",
                ]
            )
            signature_phrases.append("Here's the big picture")

        # High warmth -> casual, friendly words
        if warmth >= 0.7:
            preferred.extend(
                [
                    "Great question!",
                    "I'd love to help with that",
                    "Absolutely",
                ]
            )
            avoided.extend(
                [
                    "Negative",
                    "That is incorrect",
                ]
            )
            signature_phrases.append("Let's work through this together")
        elif warmth <= 0.3:
            preferred.extend(
                [
                    "Understood",
                    "Acknowledged",
                    "Proceeding",
                ]
            )
            avoided.extend(
                [
                    "No worries!",
                    "Awesome!",
                ]
            )
            signature_phrases.append("Here is the assessment")

        # High humor -> playful language
        humor = traits.get("humor", 0.5)
        if humor >= 0.6:
            preferred.extend(
                [
                    "Fun fact",
                    "Here's the interesting part",
                ]
            )
            signature_phrases.append("Glad you asked!")
        elif humor <= 0.2:
            avoided.extend(
                [
                    "Just kidding",
                    "LOL",
                    "Haha",
                ]
            )

        # High assertiveness -> directive language
        if assertiveness >= 0.7:
            preferred.extend(
                [
                    "Here's what I'd recommend",
                    "The best approach is",
                    "You should",
                ]
            )
            signature_phrases.append("Here's my take on it")
        elif assertiveness <= 0.3:
            preferred.extend(
                [
                    "You might consider",
                    "One option could be",
                    "If you'd like",
                ]
            )
            signature_phrases.append("What do you think about this approach?")

        # High empathy -> emotionally aware language
        empathy = traits.get("empathy", 0.5)
        if empathy >= 0.7:
            preferred.extend(
                [
                    "I understand how that feels",
                    "That makes sense",
                ]
            )
            avoided.append("Just do it")

        # High creativity -> inventive phrasing
        creativity = traits.get("creativity", 0.5)
        if creativity >= 0.7:
            preferred.extend(
                [
                    "Here's an unconventional idea",
                    "What if we tried",
                ]
            )
            signature_phrases.append("Let's think outside the box")

        # High epistemic humility -> hedged language
        epistemic_humility = traits.get("epistemic_humility", 0.5)
        if epistemic_humility >= 0.7:
            preferred.extend(
                [
                    "Based on what I know",
                    "I could be wrong, but",
                ]
            )
            avoided.extend(
                [
                    "Obviously",
                    "Clearly",
                    "Without a doubt",
                ]
            )

        # Fallback defaults if nothing accumulated
        if not preferred:
            preferred = [
                "Let me help you with that",
                "Here's what I'd recommend",
                "Good question",
            ]
        if not avoided:
            avoided = [
                "As an AI",
                "I cannot",
                "It depends",
            ]
        if not signature_phrases:
            signature_phrases = [
                "Let's work through this together",
                "Here's my take on it",
            ]

        vocabulary = {
            "preferred": preferred,
            "avoided": avoided,
            "signature_phrases": signature_phrases,
        }

        # Build strategies
        strategies: dict[str, Any] = {
            "uncertainty": {
                "approach": "transparent_calibration",
            },
            "disagreement": {
                "approach": "respectful_challenge",
            },
        }

        return {
            "personality_notes": " ".join(notes_parts),
            "greeting": greeting,
            "vocabulary": vocabulary,
            "strategies": strategies,
        }

    def apply_enhancements(
        self, identity: BuiltIdentity, enhancements: dict[str, Any], interactive: bool = True
    ) -> BuiltIdentity:
        """Apply accepted enhancements to the identity.

        If interactive=True, prompts user for each enhancement.
        If interactive=False, applies all enhancements.
        """
        data = identity.data

        # Personality notes
        if "personality_notes" in enhancements:
            notes = enhancements["personality_notes"]
            if interactive:
                self.console.print("\n[bold]Suggested personality notes:[/bold]")
                self.console.print(f"  [dim]{notes}[/dim]")
                if Confirm.ask("  Accept?", default=True):
                    data["personality"]["notes"] = notes
            else:
                data["personality"]["notes"] = notes

        # Greeting (stored as metadata for OpenClaw use)
        if "greeting" in enhancements:
            greeting = enhancements["greeting"]
            if interactive:
                self.console.print("\n[bold]Suggested greeting:[/bold]")
                self.console.print(f"  [dim]{greeting}[/dim]")
                if Confirm.ask("  Accept?", default=True):
                    data.setdefault("metadata", {})["greeting"] = greeting
            else:
                data.setdefault("metadata", {})["greeting"] = greeting

        # Vocabulary
        if "vocabulary" in enhancements:
            vocab = enhancements["vocabulary"]
            if interactive:
                self.console.print("\n[bold]Suggested vocabulary:[/bold]")
                for key, phrases in vocab.items():
                    self.console.print(f"  {key}: {', '.join(phrases)}")
                if Confirm.ask("  Accept?", default=True):
                    data.setdefault("communication", {})["vocabulary"] = vocab
            else:
                data.setdefault("communication", {})["vocabulary"] = vocab

        # Behavior strategies
        if "strategies" in enhancements:
            strategies = enhancements["strategies"]
            if interactive:
                self.console.print("\n[bold]Suggested behavior strategies:[/bold]")
                for name, strategy in strategies.items():
                    self.console.print(f"  {name}: {strategy.get('approach', 'N/A')}")
                if Confirm.ask("  Accept?", default=True):
                    data.setdefault("behavior", {})["strategies"] = strategies
            else:
                data.setdefault("behavior", {})["strategies"] = strategies

        return BuiltIdentity(data)
