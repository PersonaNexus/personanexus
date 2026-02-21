"""Identity compiler — transform resolved identities into system prompts and platform formats."""

from __future__ import annotations

import json
from typing import Any

from personanexus.personality import compute_personality_traits
from personanexus.types import (
    AgentIdentity,
    BehavioralModeConfig,
    Behavior,
    Communication,
    Expertise,
    ExpertiseCategory,
    Guardrails,
    InteractionConfig,
    Memory,
    Narrative,
    Personality,
    PersonalityMode,
    PersonalityTraits,
    Principle,
    Role,
    Severity,
)


class CompilerError(Exception):
    """Raised when compilation fails."""


# ---------------------------------------------------------------------------
# Trait-to-language mapping (5 levels per trait)
# ---------------------------------------------------------------------------

_TRAIT_TEMPLATES: dict[str, list[str]] = {
    "warmth": [
        "reserved and professional",
        "moderately warm",
        "warm and approachable",
        "very warm and friendly",
        "exceptionally warm and welcoming",
    ],
    "verbosity": [
        "concise and brief",
        "moderately detailed",
        "detailed in your explanations",
        "thorough and comprehensive",
        "extremely thorough and exhaustive",
    ],
    "assertiveness": [
        "deferential and reactive",
        "balanced in assertiveness",
        "assertive when appropriate",
        "confidently assertive",
        "highly directive and proactive",
    ],
    "humor": [
        "serious and professional",
        "occasionally light-hearted",
        "appropriately humorous",
        "frequently witty and playful",
        "highly playful with frequent humor",
    ],
    "empathy": [
        "task-focused and efficient",
        "considerate of feelings",
        "empathetic and supportive",
        "highly empathetic and emotionally attuned",
        "deeply empathetic with strong emotional intelligence",
    ],
    "directness": [
        "diplomatic and indirect",
        "balanced between tact and directness",
        "direct and straightforward",
        "very direct and candid",
        "bluntly direct with no sugarcoating",
    ],
    "rigor": [
        "flexible and adaptive",
        "reasonably rigorous",
        "rigorous and methodical",
        "highly rigorous and precise",
        "exceptionally rigorous with meticulous attention to detail",
    ],
    "creativity": [
        "conventional and proven in your approaches",
        "balanced between convention and creativity",
        "creative and open to new ideas",
        "highly creative and innovative",
        "exceptionally innovative with unconventional thinking",
    ],
    "epistemic_humility": [
        "confident and decisive",
        "reasonably aware of limitations",
        "appropriately humble about uncertainty",
        "very transparent about what you don't know",
        "deeply committed to acknowledging uncertainty and limitations",
    ],
    "patience": [
        "efficient and fast-paced",
        "moderately patient",
        "patient and willing to explain",
        "very patient with repeated questions",
        "exceptionally patient and never rushed",
    ],
}


def _trait_to_language(trait_name: str, value: float) -> str:
    """Convert a numeric trait (0-1) to a natural language sentence."""
    templates = _TRAIT_TEMPLATES.get(trait_name)
    if not templates:
        # Generic fallback for custom traits
        if value < 0.3:
            return f"You have low {trait_name}."
        elif value < 0.7:
            return f"You have moderate {trait_name}."
        else:
            return f"You have high {trait_name}."

    if value < 0.2:
        level = 0
    elif value < 0.4:
        level = 1
    elif value < 0.6:
        level = 2
    elif value < 0.8:
        level = 3
    else:
        level = 4

    return f"You are {templates[level]}."


def _expertise_level_text(level: float) -> str:
    """Convert expertise level to a word."""
    if level >= 0.9:
        return "expert"
    elif level >= 0.7:
        return "advanced"
    elif level >= 0.5:
        return "proficient"
    elif level >= 0.3:
        return "intermediate"
    return "basic"


# ---------------------------------------------------------------------------
# System Prompt Compiler
# ---------------------------------------------------------------------------


class SystemPromptCompiler:
    """Compiles a resolved AgentIdentity into a natural-language system prompt."""

    def __init__(self, token_budget: int = 3000):
        self.token_budget = token_budget

    def compile(self, identity: AgentIdentity, format: str = "text") -> str:
        """
        Compile an identity into a system prompt string.

        Args:
            identity: A fully resolved AgentIdentity.
            format: "text" (generic markdown), "anthropic", or "openai".

        Returns:
            The system prompt as a string.
        """
        sections: list[str] = []

        sections.append(self._render_header(identity))
        sections.append(self._render_role(identity.role))
        sections.append(self._render_personality(identity.personality))
        sections.append(self._render_communication(identity.communication))

        expertise_section = self._render_expertise(identity.expertise)
        if expertise_section:
            sections.append(expertise_section)

        sections.append(self._render_principles(identity.principles))

        behavior_section = self._render_behavior(identity.behavior)
        if behavior_section:
            sections.append(behavior_section)

        sections.append(self._render_guardrails(identity.guardrails))

        modes_section = self._render_behavioral_modes(identity.behavioral_modes)
        if modes_section:
            sections.append(modes_section)

        relationships_section = self._render_relationships(identity.memory)
        if relationships_section:
            sections.append(relationships_section)

        interaction_section = self._render_interaction(identity.interaction)
        if interaction_section:
            sections.append(interaction_section)

        prompt = "\n\n".join(s for s in sections if s)

        if format == "anthropic":
            return self._wrap_anthropic(prompt, identity)
        elif format == "openai":
            return self._wrap_openai(prompt)
        return prompt

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        return len(text) // 4

    # ------------------------------------------------------------------
    # Section renderers
    # ------------------------------------------------------------------

    def _render_header(self, identity: AgentIdentity) -> str:
        desc = identity.metadata.description.strip()
        return f"# {identity.metadata.name}\n\n{desc}"

    def _render_role(self, role: Role) -> str:
        lines = [f"## Your Role: {role.title}", "", role.purpose.strip()]

        if role.scope.primary:
            lines.append("\nYou specialize in:")
            for item in role.scope.primary:
                lines.append(f"- {item}")

        if role.scope.secondary:
            lines.append("\nYou can also help with:")
            for item in role.scope.secondary:
                lines.append(f"- {item}")

        if role.scope.out_of_scope:
            lines.append("\nOut of scope (do not attempt):")
            for item in role.scope.out_of_scope:
                lines.append(f"- {item}")

        if role.audience:
            lines.append(f"\nPrimary audience: {role.audience.primary}")

        return "\n".join(lines)

    def _render_personality(self, personality: Personality) -> str:
        lines = ["## Your Personality"]

        # Compute traits from profile if mode is not custom
        if personality.profile.mode != PersonalityMode.CUSTOM:
            computed = compute_personality_traits(personality)
            traits = computed.defined_traits()
            mode_label = personality.profile.mode.value.upper()
            lines.append(f"\n*Personality derived from {mode_label} profile.*")
        else:
            traits = personality.traits.defined_traits()

        for trait_name, value in sorted(traits.items()):
            lines.append(_trait_to_language(trait_name, value))

        if personality.notes:
            lines.append(f"\n{personality.notes.strip()}")

        # Render mood/emotional states if configured
        if personality.mood:
            lines.append("\n## Emotional States")
            lines.append(f"Default mood: {personality.mood.default or 'neutral'}")
            if personality.mood.states:
                lines.append("Available states:")
                for state in personality.mood.states:
                    state_info = f"- {state.name}"
                    if state.description:
                        state_info += f": {state.description}"
                    if state.trait_modifiers:
                        modifier_parts = []
                        for modifier in state.trait_modifiers:
                            sign = "+" if modifier.delta >= 0 else ""
                            modifier_parts.append(f"{modifier.trait} {sign}{modifier.delta}")
                        if modifier_parts:
                            state_info += f" (modifies: {', '.join(modifier_parts)})"
                    if state.tone_override:
                        state_info += f" (tone: {state.tone_override})"
                    lines.append(state_info)
            if personality.mood.transitions:
                lines.append("Transitions:")
                for transition in personality.mood.transitions:
                    from_display = "*" if transition.from_state == "*" else f"'{transition.from_state}'"
                    lines.append(f"- [{transition.trigger}] → '{transition.to_state}' (from: {from_display})")

        return "\n".join(lines)

    def _render_communication(self, comm: Communication) -> str:
        lines = ["## Communication Style", f"\nDefault tone: {comm.tone.default}"]

        if comm.tone.register:
            lines.append(f"Register: {comm.tone.register.value}")

        if comm.style:
            style_parts: list[str] = []
            if comm.style.sentence_length:
                style_parts.append(f"sentence length: {comm.style.sentence_length.value}")
            if comm.style.use_headers is not None:
                style_parts.append(f"use headers: {'yes' if comm.style.use_headers else 'no'}")
            if comm.style.use_lists is not None:
                style_parts.append(f"use lists: {'yes' if comm.style.use_lists else 'no'}")
            if comm.style.use_emoji:
                style_parts.append(f"emoji: {comm.style.use_emoji.value}")
            if style_parts:
                lines.append(f"Style: {', '.join(style_parts)}")

        if comm.vocabulary:
            if comm.vocabulary.preferred:
                lines.append("\nPreferred phrases:")
                for phrase in comm.vocabulary.preferred:
                    lines.append(f'- "{phrase}"')
            if comm.vocabulary.avoided:
                lines.append("\nAvoid phrases like:")
                for phrase in comm.vocabulary.avoided:
                    lines.append(f'- "{phrase}"')
            if comm.vocabulary.signature_phrases:
                lines.append("\nSignature phrases:")
                for phrase in comm.vocabulary.signature_phrases:
                    lines.append(f'- "{phrase}"')

        if comm.tone.overrides:
            lines.append("\nTone adjustments by context:")
            for override in comm.tone.overrides:
                lines.append(f"- When {override.context}: use {override.tone} tone")

        return "\n".join(lines)

    def _render_expertise(self, expertise: Expertise) -> str:
        if not expertise.domains:
            return ""

        lines = ["## Your Expertise"]

        primary = [d for d in expertise.domains if d.category == ExpertiseCategory.PRIMARY]
        secondary = [d for d in expertise.domains if d.category == ExpertiseCategory.SECONDARY]
        tertiary = [d for d in expertise.domains if d.category == ExpertiseCategory.TERTIARY]

        if primary:
            lines.append("\nPrimary expertise:")
            for domain in primary:
                level_text = _expertise_level_text(domain.level)
                line = f"- {domain.name} ({level_text})"
                if domain.description:
                    line += f" — {domain.description}"
                lines.append(line)

        if secondary:
            lines.append("\nSecondary expertise:")
            for domain in secondary:
                lines.append(f"- {domain.name}")

        if tertiary:
            lines.append("\nFamiliar with:")
            for domain in tertiary:
                lines.append(f"- {domain.name}")

        return "\n".join(lines)

    def _render_principles(self, principles: list[Principle]) -> str:
        lines = ["## Core Principles", "\nFollow these principles in order of priority:"]

        sorted_principles = sorted(principles, key=lambda p: p.priority)
        for i, principle in enumerate(sorted_principles, 1):
            lines.append(f"{i}. {principle.statement}")
            if principle.implications:
                for impl in principle.implications:
                    lines.append(f"   - {impl}")

        return "\n".join(lines)

    def _render_behavior(self, behavior: Behavior) -> str:
        if not behavior.strategies:
            return ""

        lines = ["## Behavioral Strategies"]

        for strategy_name, strategy in behavior.strategies.items():
            readable_name = strategy_name.replace("_", " ")
            lines.append(f"\nWhen handling {readable_name}:")
            lines.append(f"Approach: {strategy.approach}")

            for rule in strategy.rules:
                if rule.condition:
                    lines.append(f"- If {rule.condition}: {rule.action}")
                else:
                    lines.append(f"- {rule.action}")

            if strategy.final_fallback:
                lines.append(f"- Fallback: {strategy.final_fallback}")

        return "\n".join(lines)

    def _render_guardrails(self, guardrails: Guardrails) -> str:
        lines = ["## Non-Negotiable Rules"]

        critical = [g for g in guardrails.hard if g.severity == Severity.CRITICAL]
        high = [g for g in guardrails.hard if g.severity == Severity.HIGH]
        other = [
            g
            for g in guardrails.hard
            if g.severity not in (Severity.CRITICAL, Severity.HIGH)
        ]

        if critical:
            lines.append("\nCRITICAL — you must NEVER violate these:")
            for gr in critical:
                lines.append(f"- {gr.rule}")

        if high:
            lines.append("\nHigh priority constraints:")
            for gr in high:
                lines.append(f"- {gr.rule}")

        if other:
            lines.append("\nAdditional constraints:")
            for gr in other:
                lines.append(f"- {gr.rule}")

        if guardrails.topics and guardrails.topics.forbidden:
            lines.append("\nForbidden topics:")
            for topic in guardrails.topics.forbidden:
                reason = f" ({topic.reason})" if topic.reason else ""
                lines.append(f"- {topic.category}{reason}")

        return "\n".join(lines)

    def _render_relationships(self, memory: Memory) -> str:
        rels = memory.relationships
        if not rels.enabled and not rels.agent_relationships:
            return ""
        lines = ["## Agent Relationships"]
        if rels.agent_relationships:
            for r in rels.agent_relationships:
                name = r.name or r.agent_id
                desc = f"{name}: {r.relationship}"
                if r.dynamic:
                    desc += f" ({r.dynamic.value})"
                if r.context:
                    desc += f" — {r.context}"
                if r.interaction_style:
                    desc += f" [style: {r.interaction_style}]"
                lines.append(f"- {desc}")
        if rels.escalation_path:
            lines.append(f"\nEscalation path: {' → '.join(rels.escalation_path)}")
        if rels.unknown_agent_default:
            lines.append(f"Default interaction with unknown agents: {rels.unknown_agent_default}")
        lines.append("")
        return "\n".join(lines)

    def _render_interaction(self, interaction: InteractionConfig | None) -> str:
        if interaction is None:
            return ""
        lines = ["## Interaction Protocols"]
        h = interaction.human
        if h.greeting_style or h.farewell_style or h.tone_matching or h.escalation_triggers:
            lines.append("## With Humans")
            if h.greeting_style:
                lines.append(f"- Greeting: {h.greeting_style}")
            if h.farewell_style:
                lines.append(f"- Farewell: {h.farewell_style}")
            if h.tone_matching:
                lines.append("- Tone matching: Mirror the user's formality level")
            if h.escalation_triggers:
                triggers = ", ".join(t.value for t in h.escalation_triggers)
                lines.append(f"- Escalate when: {triggers}")
            if h.escalation_message:
                lines.append(f'- Escalation message: "{h.escalation_message}"')
        a = interaction.agent
        lines.append("## With Other Agents")
        lines.append(f"- Handoff style: {a.handoff_style}")
        lines.append(f"- Status reporting: {a.status_reporting}")
        lines.append(f"- Conflict resolution: {a.conflict_resolution}")
        lines.append("")
        return "\n".join(lines)

    def _render_behavioral_modes(self, modes: BehavioralModeConfig | None) -> str:
        if modes is None or not modes.modes:
            return ""
        lines = ["## Behavioral Modes", f"Default mode: {modes.default}", ""]
        for mode in modes.modes:
            desc = f" — {mode.description}" if mode.description else ""
            lines.append(f"### {mode.name}{desc}")
            if mode.overrides.tone_register:
                lines.append(f"  Register: {mode.overrides.tone_register}")
            if mode.overrides.tone_default:
                lines.append(f"  Tone: {mode.overrides.tone_default}")
            if mode.overrides.emoji_usage:
                lines.append(f"  Emoji: {mode.overrides.emoji_usage}")
            if mode.overrides.sentence_length:
                lines.append(f"  Sentences: {mode.overrides.sentence_length}")
            if mode.overrides.trait_modifiers:
                mods = ", ".join(f"{m.trait} {'+' if m.delta > 0 else ''}{m.delta}" for m in mode.overrides.trait_modifiers)
                lines.append(f"  Trait adjustments: {mods}")
            if mode.additional_guardrails:
                lines.append(f"  Additional rules: {'; '.join(mode.additional_guardrails)}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Format wrappers
    # ------------------------------------------------------------------

    def _wrap_anthropic(self, prompt: str, identity: AgentIdentity) -> str:
        """Wrap for Anthropic Claude — use XML section tags for clarity."""
        sections = [
            f"<identity>\n{prompt}\n</identity>",
        ]
        return "\n".join(sections)

    def _wrap_openai(self, prompt: str) -> str:
        """OpenAI uses system prompt as-is."""
        return prompt


# ---------------------------------------------------------------------------
# OpenClaw Compiler
# ---------------------------------------------------------------------------


class OpenClawCompiler:
    """Compiles a resolved AgentIdentity into OpenClaw personality.json format."""

    def __init__(self, prompt_compiler: SystemPromptCompiler | None = None):
        self.prompt_compiler = prompt_compiler or SystemPromptCompiler()

    def compile(
        self,
        identity: AgentIdentity,
        model_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Compile identity into OpenClaw personality.json format.

        Args:
            identity: The resolved PersonaNexus.
            model_config: Optional model configuration dict to override defaults.
                          Expected keys: primary_model, temperature, max_tokens, top_p.

        Returns:
            Dictionary matching the OpenClaw personality.json schema.
        """
        system_prompt = self.prompt_compiler.compile(identity, format="text")

        # Compute traits from profile if mode is not custom
        if identity.personality.profile.mode != PersonalityMode.CUSTOM:
            computed = compute_personality_traits(identity.personality)
            traits_dict = computed.defined_traits()
        else:
            traits_dict = identity.personality.traits.defined_traits()

        result: dict[str, Any] = {
            "agent_name": identity.metadata.name,
            "agent_role": self._simplify_role(identity.role.title),
            "version": identity.metadata.version,
            "system_prompt": system_prompt,
            "greeting": self._generate_greeting(identity),
            "personality_traits": traits_dict,
            "model_config": self._default_model_config(model_config),
            "tool_preferences": {},
            "behavioral_settings": self._extract_behavioral_settings(identity),
            "response_format": self._extract_response_format(identity),
            "domain_expertise": [d.name for d in identity.expertise.domains],
            "example_phrases": (
                identity.communication.vocabulary.signature_phrases
                if identity.communication.vocabulary
                else []
            ),
            "guidelines": [
                p.statement
                for p in sorted(identity.principles, key=lambda p: p.priority)
            ],
        }

        # Include personality profile metadata for non-custom modes
        profile = identity.personality.profile
        if profile.mode != PersonalityMode.CUSTOM:
            profile_meta: dict[str, Any] = {"mode": profile.mode.value}
            if profile.ocean:
                profile_meta["ocean"] = profile.ocean.model_dump()
            if profile.disc:
                profile_meta["disc"] = profile.disc.model_dump()
            if profile.disc_preset:
                profile_meta["disc_preset"] = profile.disc_preset
            result["personality_profile"] = profile_meta

        return result

    def _simplify_role(self, title: str) -> str:
        return title.lower().replace(" ", "_").replace("-", "_")

    def _generate_greeting(self, identity: AgentIdentity) -> str:
        name = identity.metadata.name
        role = identity.role.title
        purpose = identity.role.purpose.strip().split("\n")[0]  # first line only
        return (
            f"Hello! I'm {name}, your {role}. "
            f"{purpose} How can I assist you today?"
        )

    def _default_model_config(
        self,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        config = {
            "primary_model": "claude-sonnet-4",
            "fallback_model": "claude-haiku-4",
            "temperature": 0.3,
            "max_tokens": 4096,
            "top_p": 0.9,
        }
        if overrides:
            config.update(overrides)
        return config

    def _extract_behavioral_settings(self, identity: AgentIdentity) -> dict[str, bool]:
        settings: dict[str, bool] = {}
        for guardrail in identity.guardrails.hard:
            settings[guardrail.id] = True
        for guardrail in identity.guardrails.soft:
            settings[guardrail.id] = True
        return settings

    def _extract_response_format(self, identity: AgentIdentity) -> dict[str, Any]:
        result: dict[str, Any] = {"tone": identity.communication.tone.default}

        if identity.communication.style:
            style = identity.communication.style
            if style.use_headers is not None:
                result["use_headings"] = style.use_headers
            if style.use_lists is not None:
                result["use_bullet_points"] = style.use_lists
            if style.use_emoji:
                result["use_emoji"] = style.use_emoji.value
            if style.sentence_length:
                result["sentence_length"] = style.sentence_length.value

        return result


# ---------------------------------------------------------------------------
# Soul Compiler — YAML → SOUL.md + STYLE.md
# ---------------------------------------------------------------------------


class SoulCompiler:
    """Compiles a resolved AgentIdentity into SOUL.md and STYLE.md Markdown files.

    Follows the soul.md format (https://github.com/aaronjmars/soul.md)
    for compatibility with OpenClaw's workspace bootstrap system.
    """

    def compile(self, identity: AgentIdentity) -> dict[str, str]:
        """Compile identity into SOUL.md and STYLE.md content.

        Returns:
            Dict with keys "soul_md" and "style_md", each containing Markdown text.
        """
        return {
            "soul_md": self._render_soul(identity),
            "style_md": self._render_style(identity),
        }

    # ------------------------------------------------------------------
    # SOUL.md rendering
    # ------------------------------------------------------------------

    def _render_soul(self, identity: AgentIdentity) -> str:
        sections: list[str] = []

        sections.append(self._soul_header(identity))
        sections.append(self._soul_who_i_am(identity))
        sections.append(self._soul_worldview(identity))

        opinions = self._soul_opinions(identity.narrative)
        if opinions:
            sections.append(opinions)

        sections.append(self._soul_interests(identity))

        current_focus = self._soul_current_focus(identity.narrative)
        if current_focus:
            sections.append(current_focus)

        influences = self._soul_influences(identity.narrative)
        if influences:
            sections.append(influences)

        vocabulary = self._soul_vocabulary(identity)
        if vocabulary:
            sections.append(vocabulary)

        tensions = self._soul_tensions(identity.narrative)
        if tensions:
            sections.append(tensions)

        sections.append(self._soul_boundaries(identity))

        pet_peeves = self._soul_pet_peeves(identity.narrative)
        if pet_peeves:
            sections.append(pet_peeves)

        return "\n\n".join(s for s in sections if s)

    def _soul_header(self, identity: AgentIdentity) -> str:
        desc = identity.metadata.description.strip()
        return f"# {identity.metadata.name}\n\n{desc}"

    def _soul_who_i_am(self, identity: AgentIdentity) -> str:
        lines = ["## Who I Am"]

        # Use narrative backstory if available, otherwise build from role
        if identity.narrative.backstory:
            lines.append(f"\n{identity.narrative.backstory.strip()}")
        else:
            lines.append(f"\n{identity.role.purpose.strip()}")

        # Add personality narrative from notes
        if identity.personality.notes:
            lines.append(f"\n{identity.personality.notes.strip()}")

        # Add personality trait descriptions
        if identity.personality.profile.mode != PersonalityMode.CUSTOM:
            computed = compute_personality_traits(identity.personality)
            traits = computed.defined_traits()
        else:
            traits = identity.personality.traits.defined_traits()

        if traits:
            trait_lines: list[str] = []
            for trait_name, value in sorted(traits.items()):
                trait_lines.append(_trait_to_language(trait_name, value))
            lines.append("\n" + " ".join(trait_lines))

        return "\n".join(lines)

    def _soul_worldview(self, identity: AgentIdentity) -> str:
        lines = ["## Worldview"]
        for principle in sorted(identity.principles, key=lambda p: p.priority):
            lines.append(f"\n- {principle.statement}")
            for impl in principle.implications:
                lines.append(f"  - {impl}")
        return "\n".join(lines)

    def _soul_opinions(self, narrative: Narrative) -> str:
        if not narrative.opinions:
            return ""
        lines = ["## Opinions"]
        for opinion in narrative.opinions:
            lines.append(f"\n### {opinion.domain}")
            for take in opinion.takes:
                lines.append(f"- {take}")
        return "\n".join(lines)

    def _soul_interests(self, identity: AgentIdentity) -> str:
        if not identity.expertise.domains:
            return ""
        lines = ["## Interests"]
        for domain in identity.expertise.domains:
            level = _expertise_level_text(domain.level)
            desc = f": {domain.description}" if domain.description else ""
            lines.append(f"- **{domain.name}** ({level}){desc}")
        return "\n".join(lines)

    def _soul_current_focus(self, narrative: Narrative) -> str:
        if not narrative.current_focus:
            return ""
        lines = ["## Current Focus"]
        for focus in narrative.current_focus:
            lines.append(f"- {focus}")
        return "\n".join(lines)

    def _soul_influences(self, narrative: Narrative) -> str:
        if not narrative.influences:
            return ""
        lines = ["## Influences"]

        by_category: dict[str, list[tuple[str, str]]] = {}
        for inf in narrative.influences:
            cat = inf.category.title()
            by_category.setdefault(cat, []).append((inf.name, inf.insight))

        for category, items in by_category.items():
            lines.append(f"\n### {category}")
            for name, insight in items:
                lines.append(f"- **{name}**: {insight}")

        return "\n".join(lines)

    def _soul_vocabulary(self, identity: AgentIdentity) -> str:
        vocab = identity.communication.vocabulary
        if not vocab:
            return ""
        if not vocab.signature_phrases:
            return ""
        lines = ["## Vocabulary"]
        for phrase in vocab.signature_phrases:
            lines.append(f'- **"{phrase}"**')
        return "\n".join(lines)

    def _soul_tensions(self, narrative: Narrative) -> str:
        if not narrative.tensions:
            return ""
        lines = ["## Tensions & Contradictions"]
        for tension in narrative.tensions:
            lines.append(f"- {tension}")
        return "\n".join(lines)

    def _soul_boundaries(self, identity: AgentIdentity) -> str:
        lines = ["## Boundaries"]
        seen: set[str] = set()

        for gr in identity.guardrails.hard:
            key = gr.rule.lower().strip()
            if key not in seen:
                seen.add(key)
                lines.append(f"- Won't: {gr.rule}")

        # Out-of-scope items as boundaries
        if identity.role.scope.out_of_scope:
            for item in identity.role.scope.out_of_scope:
                key = item.lower().strip()
                if key not in seen:
                    seen.add(key)
                    lines.append(f"- Won't: {item}")

        return "\n".join(lines)

    def _soul_pet_peeves(self, narrative: Narrative) -> str:
        if not narrative.pet_peeves:
            return ""
        lines = ["## Pet Peeves"]
        for peeve in narrative.pet_peeves:
            lines.append(f"- {peeve}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # STYLE.md rendering
    # ------------------------------------------------------------------

    def _render_style(self, identity: AgentIdentity) -> str:
        sections: list[str] = []

        sections.append("# Voice & Style Guide")
        sections.append(self._style_voice_principles(identity))
        sections.append(self._style_vocabulary(identity))
        sections.append(self._style_formatting(identity))

        context_styles = self._style_context_adjustments(identity)
        if context_styles:
            sections.append(context_styles)

        examples = self._style_examples(identity)
        if examples:
            sections.append(examples)

        anti = self._style_anti_patterns(identity)
        if anti:
            sections.append(anti)

        return "\n\n".join(s for s in sections if s)

    def _style_voice_principles(self, identity: AgentIdentity) -> str:
        lines = ["## Voice Principles"]
        comm = identity.communication

        lines.append(f"\n- Default tone: {comm.tone.default}")
        if comm.tone.register:
            lines.append(f"- Register: {comm.tone.register.value}")

        # Add trait-derived voice description
        if identity.personality.profile.mode != PersonalityMode.CUSTOM:
            computed = compute_personality_traits(identity.personality)
            traits = computed.defined_traits()
        else:
            traits = identity.personality.traits.defined_traits()

        if traits:
            voice_notes: list[str] = []
            for trait_name, value in sorted(traits.items()):
                voice_notes.append(_trait_to_language(trait_name, value))
            lines.append(f"\n{' '.join(voice_notes)}")

        return "\n".join(lines)

    def _style_vocabulary(self, identity: AgentIdentity) -> str:
        vocab = identity.communication.vocabulary
        if not vocab:
            return ""

        lines = ["## Vocabulary"]

        if vocab.preferred:
            lines.append("\n### Words & Phrases You Use")
            for phrase in vocab.preferred:
                lines.append(f'- "{phrase}"')

        if vocab.avoided:
            lines.append("\n### Words You Never Use")
            for phrase in vocab.avoided:
                lines.append(f'- "{phrase}"')

        return "\n".join(lines)

    def _style_formatting(self, identity: AgentIdentity) -> str:
        style = identity.communication.style
        if not style:
            return ""

        lines = ["## Punctuation & Formatting"]

        if style.sentence_length:
            lines.append(f"- Sentence length: {style.sentence_length.value}")
        if style.use_headers is not None:
            lines.append(f"- Use headers: {'yes' if style.use_headers else 'no'}")
        if style.use_lists is not None:
            lines.append(f"- Use lists: {'yes' if style.use_lists else 'no'}")
        if style.use_code_blocks is not None:
            lines.append(f"- Use code blocks: {'yes' if style.use_code_blocks else 'no'}")
        if style.use_emoji:
            lines.append(f"- Emoji: {style.use_emoji.value}")

        return "\n".join(lines)

    def _style_context_adjustments(self, identity: AgentIdentity) -> str:
        if not identity.communication.tone.overrides:
            return ""

        lines = ["## Context-Specific Style"]
        for override in identity.communication.tone.overrides:
            lines.append(f"\n### {override.context.title()}")
            lines.append(f"- Tone: {override.tone}")
            if override.note:
                lines.append(f"- Note: {override.note}")

        return "\n".join(lines)

    def _style_examples(self, identity: AgentIdentity) -> str:
        examples = identity.communication.voice_examples
        if not examples:
            return ""
        if not examples.good and not examples.bad:
            return ""

        lines = ["## Voice Examples"]

        if examples.good:
            lines.append("\n### Right Voice")
            for ex in examples.good:
                ctx = f" ({ex.context})" if ex.context else ""
                lines.append(f'\n> "{ex.text}"{ctx}')

        if examples.bad:
            lines.append("\n### Wrong Voice")
            for ex in examples.bad:
                ctx = f" ({ex.context})" if ex.context else ""
                lines.append(f'\n> "{ex.text}"{ctx}')

        return "\n".join(lines)

    def _style_anti_patterns(self, identity: AgentIdentity) -> str:
        vocab = identity.communication.vocabulary
        if not vocab or not vocab.avoided:
            return ""

        lines = ["## Anti-Patterns", "\nNever say:"]
        for phrase in vocab.avoided:
            lines.append(f'- "{phrase}"')

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def compile_identity(
    identity: AgentIdentity,
    target: str = "text",
    token_budget: int = 3000,
) -> str | dict[str, Any]:
    """
    Compile a resolved AgentIdentity into the specified target format.

    Args:
        identity: A fully resolved AgentIdentity.
        target: "text", "anthropic", "openai", "openclaw", "soul", or "json".
        token_budget: Estimated token budget for system prompt.

    Returns:
        String for text formats, dict for openclaw/soul/json.
    """
    prompt_compiler = SystemPromptCompiler(token_budget=token_budget)

    if target in ("text", "anthropic", "openai"):
        return prompt_compiler.compile(identity, format=target)
    elif target == "openclaw":
        openclaw_compiler = OpenClawCompiler(prompt_compiler)
        return openclaw_compiler.compile(identity)
    elif target == "soul":
        soul_compiler = SoulCompiler()
        return soul_compiler.compile(identity)
    elif target == "json":
        prompt = prompt_compiler.compile(identity, format="text")
        return {"system_prompt": prompt, "tokens_estimated": prompt_compiler.estimate_tokens(prompt)}
    else:
        raise CompilerError(f"Unknown target format: {target}")
