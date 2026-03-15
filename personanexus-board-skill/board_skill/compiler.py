"""Identity compiler — board skill extension.

Extends the core personanexus compiler classes with board-of-directors
rendering.  Re-exports everything so existing imports continue to work.
"""

from __future__ import annotations

import logging
from typing import Any

from board_skill.board import BoardConfig
from personanexus.compiler import (
    AutoGenCompiler,  # noqa: F401 – re-export
    CompilerError,  # noqa: F401 – re-export
    CrewAICompiler,  # noqa: F401 – re-export
    LangChainCompiler,  # noqa: F401 – re-export
    MarkdownCompiler,  # noqa: F401 – re-export
    OpenClawCompiler,  # noqa: F401 – re-export
)
from personanexus.compiler import (
    SoulCompiler as _BaseSoulCompiler,
)
from personanexus.compiler import (
    SystemPromptCompiler as _BaseSystemPromptCompiler,
)
from personanexus.compiler import (
    compile_identity as _base_compile_identity,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Board-aware SystemPromptCompiler
# ---------------------------------------------------------------------------


class SystemPromptCompiler(_BaseSystemPromptCompiler):
    """Extends the base prompt compiler with a board-of-directors section."""

    def _get_extra_optional_renderers(self, identity: Any) -> list[tuple[str, Any]]:
        """Add the board section as an optional renderer."""
        renderers: list[tuple[str, Any]] = []
        if hasattr(identity, "board"):
            renderers.append(("board", lambda: self._render_board(identity.board)))
        return renderers

    def _render_board(self, board: BoardConfig) -> str:
        """Render the Board of Directors advisory section."""
        if not board.enabled:
            return ""

        lines: list[str] = []

        # Disclaimer (always first)
        if board.disclaimer:
            lines.append(f"> {board.disclaimer}")
            lines.append("")

        lines.append("## Historical Advisory Board")

        # Board members
        if board.board_members:
            for member in board.board_members:
                lines.append(f"\n**{member.name}** ({member.died}) — {member.board_role}")
                lines.append(f"  Mindset: {member.core_mindset}")
                lines.append(f"  Modern relevance: {member.modern_relevance}")
                p = member.personality
                ocean = p.ocean
                ocean_str = (
                    f"O={ocean.openness:.1f}"
                    f" C={ocean.conscientiousness:.1f}"
                    f" E={ocean.extraversion:.1f}"
                    f" A={ocean.agreeableness:.1f}"
                    f" N={ocean.neuroticism:.1f}"
                )
                lines.append(
                    f"  Personality: {p.jungian_type},"
                    f" DISC={p.disc_style.value},"
                    f" OCEAN({ocean_str})"
                )
                if member.key_quote:
                    lines.append(f'  Key quote: "{member.key_quote}"')

        # Engagement rules
        if board.engagement_rules:
            lines.append("\nBoard engagement rules:")
            for rule in board.engagement_rules:
                lines.append(f"  - {rule}")

        # Notes
        if board.notes:
            lines.append(f"\nNote: {board.notes}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Board-aware SoulCompiler
# ---------------------------------------------------------------------------


class SoulCompiler(_BaseSoulCompiler):
    """Extends the base Soul compiler with a board advisory section."""

    def _render_soul(self, identity: Any, traits: dict[str, float]) -> str:
        base = super()._render_soul(identity, traits)

        # Insert board section before boundaries
        if hasattr(identity, "board"):
            board_section = self._soul_board(identity)
            if board_section:
                base += "\n\n" + board_section

        return base

    def _soul_board(self, identity: Any) -> str:
        """Render board section for SOUL.md."""
        board = identity.board
        if not board.enabled:
            return ""

        lines = ["## Advisory Board"]
        lines.append("")
        lines.append("I consult a panel of historical advisors:")

        for member in board.board_members:
            lines.append(f"- **{member.name}** ({member.board_role}): {member.core_mindset}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# compile_identity — board-aware entry point
# ---------------------------------------------------------------------------


def compile_identity(
    identity: Any,
    target: str = "text",
    token_budget: int = 3000,
) -> str | dict[str, Any]:
    """Compile a resolved AgentIdentity, using board-aware compilers."""
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
