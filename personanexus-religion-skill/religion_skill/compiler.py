"""Identity compiler — religion skill extension.

Extends the core personanexus compiler classes with religion/spiritual
framework rendering.  Re-exports everything so existing imports continue
to work.
"""

from __future__ import annotations

import logging
from typing import Any

from religion_skill.religion import InfluenceLevel, ReligionConfig

from personanexus.compiler import (
    CompilerError,  # noqa: F401 – re-export
    MarkdownCompiler,  # noqa: F401 – re-export
    OpenClawCompiler,  # noqa: F401 – re-export
    SoulCompiler as _BaseSoulCompiler,
    SystemPromptCompiler as _BaseSystemPromptCompiler,
    compile_identity as _base_compile_identity,
)
from personanexus.compiler import (
    AutoGenCompiler,  # noqa: F401 – re-export
    CrewAICompiler,  # noqa: F401 – re-export
    LangChainCompiler,  # noqa: F401 – re-export
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Religion-aware SystemPromptCompiler
# ---------------------------------------------------------------------------


class SystemPromptCompiler(_BaseSystemPromptCompiler):
    """Extends the base prompt compiler with a religion/spiritual section."""

    def _get_extra_optional_renderers(self, identity: Any) -> list[tuple[str, Any]]:
        """Add the religion section as an optional renderer."""
        renderers: list[tuple[str, Any]] = []
        if hasattr(identity, "religion"):
            renderers.append(("religion", lambda: self._render_religion(identity.religion)))
        return renderers

    def _render_religion(self, religion: ReligionConfig) -> str:
        """Render the religion/spiritual framework section."""
        if not religion.enabled:
            return ""

        lines: list[str] = ["## Religious & Spiritual Framework"]

        # Tradition / denomination header
        if religion.tradition_name:
            label = religion.tradition_name
            if religion.denomination:
                label += f" ({religion.denomination})"
            lines.append(f"Tradition: {label}")

        # Influence description
        influence_desc = {
            InfluenceLevel.SUBTLE: "These beliefs subtly inform your worldview.",
            InfluenceLevel.MODERATE: "These beliefs moderately shape your worldview and decisions.",
            InfluenceLevel.STRONG: (
                "These beliefs strongly shape your worldview"
                " and decision-making."
            ),
            InfluenceLevel.CENTRAL: (
                "These beliefs are central to your identity and permeate all decisions."
            ),
        }
        lines.append(influence_desc.get(religion.influence, ""))

        # Principles
        if religion.principles:
            lines.append("")
            influence_val = religion.influence.value
            principles_str = "; ".join(religion.principles)
            lines.append(
                f"You are guided by these {influence_val}-level principles: "
                f"{principles_str}. Weigh decisions against them."
            )

        # Moral framework
        if religion.moral_framework:
            mf = religion.moral_framework
            lines.append("")
            lines.append(f"Moral framework: {mf.name}")
            if mf.description:
                lines.append(f"  {mf.description}")
            if mf.principles:
                lines.append(f"  Core values: {', '.join(mf.principles)}")
            lines.append(f"  Decision weight: {mf.decision_weight}")

        # Sacred texts
        if religion.sacred_texts:
            lines.append("")
            lines.append("Sacred texts:")
            for text in religion.sacred_texts:
                desc = f" — {text.description}" if text.description else ""
                lines.append(f"  - {text.name} ({text.authority_level.value}){desc}")

        # Traditions
        if religion.traditions:
            lines.append("")
            lines.append("Traditions:")
            for tradition in religion.traditions:
                impact = f" → {tradition.behavioral_impact}" if tradition.behavioral_impact else ""
                lines.append(f"  - {tradition.name}{impact}")

        # Dietary rules
        if religion.dietary_rules:
            lines.append("")
            lines.append("Dietary observances:")
            for rule in religion.dietary_rules:
                exc = f" (exceptions: {', '.join(rule.exceptions)})" if rule.exceptions else ""
                lines.append(f"  - {rule.rule} [{rule.strictness.value}]{exc}")

        # Holy days
        if religion.holy_days:
            lines.append("")
            lines.append("Holy days:")
            for day in religion.holy_days:
                obs = f" — {day.observance}" if day.observance else ""
                period = f" ({day.period})" if day.period else ""
                lines.append(f"  - {day.name}{period}{obs}")

        # Prayer schedule
        if religion.prayer_schedule and religion.prayer_schedule.enabled:
            ps = religion.prayer_schedule
            lines.append("")
            freq = f": {ps.frequency}" if ps.frequency else ""
            lines.append(f"Prayer/meditation{freq}")
            if ps.description:
                lines.append(f"  {ps.description}")

        # Notes
        if religion.notes:
            lines.append("")
            lines.append(f"Note: {religion.notes}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Religion-aware SoulCompiler
# ---------------------------------------------------------------------------


class SoulCompiler(_BaseSoulCompiler):
    """Extends the base Soul compiler with a religion/faith section."""

    def _render_soul(self, identity: Any, traits: dict[str, float]) -> str:
        base = super()._render_soul(identity, traits)

        # Insert religion section
        if hasattr(identity, "religion"):
            religion_section = self._soul_religion(identity)
            if religion_section:
                base += "\n\n" + religion_section

        return base

    def _soul_religion(self, identity: Any) -> str:
        """Render religion section for SOUL.md."""
        religion = identity.religion
        if not religion.enabled:
            return ""

        lines = ["## Faith & Guiding Principles"]

        if religion.tradition_name:
            label = religion.tradition_name
            if religion.denomination:
                label += f" ({religion.denomination})"
            lines.append(f"\nI draw from the {label} tradition.")

        if religion.principles:
            lines.append("")
            for principle in religion.principles:
                lines.append(f"- {principle}")

        if religion.moral_framework:
            lines.append(f"\nMoral compass: {religion.moral_framework.name}")
            if religion.moral_framework.principles:
                for p in religion.moral_framework.principles:
                    lines.append(f"- {p}")

        if religion.sacred_texts:
            texts = ", ".join(t.name for t in religion.sacred_texts)
            lines.append(f"\nI draw wisdom from: {texts}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# compile_identity — religion-aware entry point
# ---------------------------------------------------------------------------


def compile_identity(
    identity: Any,
    target: str = "text",
    token_budget: int = 3000,
) -> str | dict[str, Any]:
    """Compile a resolved AgentIdentity, using religion-aware compilers."""
    if target == "soul":
        soul_compiler = SoulCompiler()
        return soul_compiler.compile(identity)
    if target in ("text", "anthropic", "openai"):
        prompt_compiler = SystemPromptCompiler(token_budget=token_budget)
        return prompt_compiler.compile(identity, format=target)
    # Fall through to base for all other targets
    return _base_compile_identity(identity, target=target, token_budget=token_budget)


__all__ = [
    "AutoGenCompiler",
    "CompilerError",
    "CrewAICompiler",
    "LangChainCompiler",
    "MarkdownCompiler",
    "OpenClawCompiler",
    "SoulCompiler",
    "SystemPromptCompiler",
    "compile_identity",
]
