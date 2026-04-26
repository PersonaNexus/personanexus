"""Pure compile/load helpers for PersonaNexus Studio — no Streamlit dependency."""

from __future__ import annotations

import json
from pathlib import Path

from studio_model import StudioAgent, top_motifs, traits_from_profile


def _load_identity_safe(path: Path):
    """Return (AgentIdentity, None) or (None, error_str)."""
    try:
        from personanexus.parser import parse_identity_file

        return parse_identity_file(path), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _compile_safe(identity, fmt: str):
    """Return (result_str, None) or (None, error_str)."""
    try:
        from personanexus.compiler import compile_identity

        result = compile_identity(identity, target=fmt)
        if isinstance(result, dict):
            return json.dumps(result, indent=2, ensure_ascii=False), None
        return str(result), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _studio_agent_from_yaml(data: dict, slug: str = "custom") -> StudioAgent:
    metadata = data.get("metadata", {})
    role = data.get("role", {})
    communication = data.get("communication", {})
    tone = communication.get("tone", {})
    traits = traits_from_profile(data.get("personality", {}))
    principles = tuple(
        str(item.get("statement", item))
        for item in data.get("principles", [])[:3]
    )
    return StudioAgent(
        slug=slug,
        name=str(metadata.get("name") or slug.title()),
        title=str(role.get("title") or "AI Agent"),
        description=str(metadata.get("description") or role.get("purpose") or ""),
        tags=tuple(str(tag) for tag in metadata.get("tags", [])[:5]),
        status=str(metadata.get("status") or "draft"),
        traits=traits,
        tone=str(tone.get("default") if isinstance(tone, dict) else tone or "adaptive"),
        principles=principles,
        motifs=top_motifs(traits),
    )
