"""Identity compiler — thin wrapper around the core personanexus compiler.

Re-exports all compiler classes and functions from ``personanexus.compiler``
so that existing imports (``from personanexus_skill.compiler import ...``)
continue to work without change.
"""

from __future__ import annotations

from personanexus.compiler import (  # noqa: F401 – re-exports
    AutoGenCompiler,
    CompilerError,
    CrewAICompiler,
    LangChainCompiler,
    MarkdownCompiler,
    OpenClawCompiler,
    SoulCompiler,
    SystemPromptCompiler,
    compile_identity,
)

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
