"""Interactive identity builder wizard and LLM enhancer."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

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

_TRAIT_ORDER = list(_TRAIT_DESCRIPTIONS.keys())


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


# ---------------------------------------------------------------------------
# IdentityBuilder wizard
# ---------------------------------------------------------------------------


class IdentityBuilder:
    """Interactive wizard for building agent identities step-by-step."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

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

        data: dict[str, Any] = {"schema_version": "1.0"}

        self._phase_basics(data)
        self._phase_personality_mode(data)
        self._phase_personality(data)
        self._phase_communication(data)
        self._phase_principles(data)
        self._phase_guardrails(data)
        self._phase_expertise(data)

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
        purpose = Prompt.ask(
            "Purpose (what does this agent do?)", default=default_purpose
        )
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
        """Select personality framework mode: custom, ocean, disc, or hybrid."""
        self.console.print("\n[bold blue]Phase 2a: Personality Mode[/bold blue]")
        self.console.rule()
        self.console.print(
            "[dim]Choose how to define your agent's personality:\n"
            "  custom  — Set each trait manually (0-1 scale)\n"
            "  ocean   — Use Big Five (OCEAN) dimensions, auto-map to traits\n"
            "  disc    — Use DISC profile or a named preset\n"
            "  hybrid  — Compute from a framework, then override specific traits[/dim]\n"
        )

        mode = self._prompt_choice(
            "Personality mode", ["custom", "ocean", "disc", "hybrid"], default="custom"
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
        for trait_name in _TRAIT_ORDER:
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
        self.console.print(
            "[dim]Rate each OCEAN dimension from 0.0 to 1.0.[/dim]\n"
        )

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
            preset_name = self._prompt_choice(
                "Preset", preset_names, default="the_analyst"
            )
            disc = get_disc_preset(preset_name)
            computed = disc_to_traits(disc)
            disc_data: dict[str, Any] = {
                "mode": "disc",
                "disc_preset": preset_name,
            }
        else:
            self.console.print(
                "[dim]Rate each DISC dimension from 0.0 to 1.0.[/dim]\n"
            )
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
            "Base framework", ["ocean", "disc"], default="ocean"
        )

        profile_data: dict[str, Any] = {"mode": "hybrid"}

        if framework == "ocean":
            ocean_dims = [
                "openness", "conscientiousness", "extraversion",
                "agreeableness", "neuroticism",
            ]
            scores: dict[str, float] = {}
            for dim in ocean_dims:
                value = self._prompt_float(dim, 0.0, 1.0, allow_skip=False)
                scores[dim] = value  # type: ignore[assignment]  # allow_skip=False guarantees non-None
            profile = OceanProfile(**scores)
            computed = ocean_to_traits(profile)
            profile_data["ocean"] = scores
        else:
            disc_dims = [
                "dominance", "influence", "steadiness", "conscientiousness",
            ]
            scores = {}
            for dim in disc_dims:
                value = self._prompt_float(dim, 0.0, 1.0, allow_skip=False)
                scores[dim] = value  # type: ignore[assignment]  # allow_skip=False guarantees non-None
            disc = DiscProfile(**scores)
            computed = disc_to_traits(disc)
            profile_data["disc"] = scores

        self.console.print("\n[bold]Computed base traits:[/bold]")
        self._show_computed_traits_preview(computed)

        # Now allow overrides
        self.console.print(
            "\n[dim]Override specific traits (Enter to keep computed value):[/dim]"
        )
        overrides: dict[str, float] = {}
        for trait_name in _TRAIT_ORDER:
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
        for trait_name in _TRAIT_ORDER:
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
            "[dim]Enter guiding principles for the agent."
            " Empty input to finish.[/dim]\n"
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
                "[yellow]No principles entered."
                " Adding default safety principle.[/yellow]"
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
            "[dim]Enter hard constraints the agent must never violate."
            " Empty to finish.[/dim]\n"
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
    # Phase 6: Expertise (optional)
    # ------------------------------------------------------------------

    def _phase_expertise(self, data: dict[str, Any]) -> None:
        self.console.print("\n[bold blue]Phase 6: Expertise (Optional)[/bold blue]")
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
            import anthropic

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
        name = data.get("metadata", {}).get("name", "Agent")
        role = data.get("role", {}).get("title", "Assistant")
        purpose = data.get("role", {}).get("purpose", "")
        traits = data.get("personality", {}).get("traits", {})

        trait_desc = ", ".join(f"{k}={v}" for k, v in traits.items())

        prompt = f"""I'm building an AI PersonaNexus. Generate enhancements for:

Name: {name}
Role: {role}
Purpose: {purpose}
Traits: {trait_desc}

Respond in this exact JSON format (no markdown, just raw JSON):
{{
  "personality_notes": "2-3 sentences synthesizing traits into a character description for {name}.",
  "greeting": "A warm greeting message from {name} introducing themselves and their role.",
  "vocabulary": {{
    "preferred": ["phrase1", "phrase2", "phrase3"],
    "avoided": ["phrase1", "phrase2", "phrase3"],
    "signature_phrases": ["phrase1", "phrase2"]
  }},
  "strategies": {{
    "uncertainty": {{
      "approach": "A brief description of how {name} handles uncertainty"
    }},
    "disagreement": {{
      "approach": "A brief description of how {name} handles disagreement"
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
            return json.loads(text)
        except Exception as exc:
            self.console.print(
                f"[yellow]LLM enhancement failed: {exc}."
                " Falling back to templates.[/yellow]"
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

        # Build greeting
        purpose_first_line = purpose.strip().split("\n")[0]
        greeting = f"Hello! I'm {name}, your {role}. {purpose_first_line} How can I help you today?"

        # Build vocabulary
        vocabulary = {
            "preferred": [
                "Let me help you with that",
                "Here's what I'd recommend",
                "Good question",
            ],
            "avoided": [
                "As an AI",
                "I cannot",
                "It depends",
            ],
            "signature_phrases": [
                "Let's work through this together",
                "Here's my take on it",
            ],
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
