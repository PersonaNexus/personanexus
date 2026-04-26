"""Pure data helpers for PersonaNexus Studio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

TRAIT_ORDER = [
    "warmth",
    "verbosity",
    "assertiveness",
    "humor",
    "empathy",
    "directness",
    "rigor",
    "creativity",
    "epistemic_humility",
    "patience",
]

TRAIT_LABELS = {
    "warmth": ("Warmth", "Cold", "Friendly"),
    "verbosity": ("Verbosity", "Brief", "Detailed"),
    "assertiveness": ("Assertiveness", "Passive", "Directive"),
    "humor": ("Humor", "Serious", "Witty"),
    "empathy": ("Empathy", "Task-focused", "Empathetic"),
    "directness": ("Directness", "Diplomatic", "Direct"),
    "rigor": ("Rigor", "Flexible", "Precise"),
    "creativity": ("Creativity", "Conventional", "Innovative"),
    "epistemic_humility": ("Epistemic Humility", "Confident", "Humble"),
    "patience": ("Patience", "Fast-paced", "Patient"),
}

AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"
FALLBACK_TRAITS: dict[str, float] = dict.fromkeys(TRAIT_ORDER, 0.5)

MOTIF_BY_TRAIT = {
    "warmth": "solar halo",
    "rigor": "blueprint grid",
    "creativity": "violet nebula",
    "empathy": "rose signal",
    "assertiveness": "red vector",
    "patience": "green orbit",
    "directness": "amber ray",
    "epistemic_humility": "cyan lens",
    "verbosity": "indigo ribbon",
    "humor": "gold spark",
}


@dataclass(frozen=True)
class StudioAgent:
    """Small view model for rendering an agent in PersonaNexus Studio."""

    slug: str
    name: str
    title: str
    description: str
    tags: tuple[str, ...]
    status: str
    traits: dict[str, float]
    tone: str
    principles: tuple[str, ...]
    motifs: tuple[str, ...]


def _clamp_score(value: Any) -> float:
    """Return a trait score safely clamped to the 0..1 range."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, score))


def traits_from_profile(personality: dict[str, Any]) -> dict[str, float]:
    """Extract explicit or approximate trait scores from a persona payload."""
    explicit = personality.get("traits")
    if isinstance(explicit, dict):
        return {trait: _clamp_score(explicit.get(trait, 0.5)) for trait in TRAIT_ORDER}

    ocean = personality.get("profile", {}).get("ocean")
    if not isinstance(ocean, dict):
        return FALLBACK_TRAITS.copy()

    openness = _clamp_score(ocean.get("openness"))
    conscientiousness = _clamp_score(ocean.get("conscientiousness"))
    extraversion = _clamp_score(ocean.get("extraversion"))
    agreeableness = _clamp_score(ocean.get("agreeableness"))
    neuroticism = _clamp_score(ocean.get("neuroticism"))
    calm = 1.0 - neuroticism

    return {
        "warmth": round((agreeableness + extraversion) / 2, 2),
        "verbosity": round((openness + extraversion) / 2, 2),
        "assertiveness": round((extraversion + (1.0 - agreeableness)) / 2, 2),
        "humor": round((openness + extraversion) / 2, 2),
        "empathy": round(agreeableness, 2),
        "directness": round((conscientiousness + (1.0 - agreeableness)) / 2, 2),
        "rigor": round(conscientiousness, 2),
        "creativity": round(openness, 2),
        "epistemic_humility": round((agreeableness + conscientiousness + calm) / 3, 2),
        "patience": round((agreeableness + calm) / 2, 2),
    }


def top_motifs(traits: dict[str, float], count: int = 4) -> tuple[str, ...]:
    """Return visual motifs implied by the strongest traits."""
    ranked = sorted(traits.items(), key=lambda item: item[1], reverse=True)
    return tuple(MOTIF_BY_TRAIT.get(trait, trait.replace("_", " ")) for trait, _ in ranked[:count])


def load_studio_agents(agents_dir: Path = AGENTS_DIR) -> list[StudioAgent]:
    """Load repository persona YAML files as Studio gallery cards."""
    agents: list[StudioAgent] = []
    for path in sorted(agents_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        metadata = data.get("metadata", {})
        role = data.get("role", {})
        communication = data.get("communication", {})
        tone = communication.get("tone", {})
        traits = traits_from_profile(data.get("personality", {}))
        principles = tuple(
            str(item.get("statement", item))
            for item in data.get("principles", [])[:3]
        )
        agents.append(
            StudioAgent(
                slug=path.stem,
                name=str(metadata.get("name") or path.stem.title()),
                title=str(role.get("title") or "AI Agent"),
                description=str(metadata.get("description") or role.get("purpose") or ""),
                tags=tuple(str(tag) for tag in metadata.get("tags", [])[:5]),
                status=str(metadata.get("status") or "draft"),
                traits=traits,
                tone=str(tone.get("default") if isinstance(tone, dict) else tone or "adaptive"),
                principles=principles,
                motifs=top_motifs(traits),
            )
        )
    return agents


def agent_signature(agent: StudioAgent) -> str:
    """Return a compact text summary for tests and gallery captions."""
    strongest = max(agent.traits.items(), key=lambda item: item[1])[0]
    label = TRAIT_LABELS.get(strongest, (strongest, "", ""))[0]
    return f"{agent.name} · {label} · {agent.tone}"
