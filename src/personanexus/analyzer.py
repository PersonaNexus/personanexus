"""Soul analysis — reverse-map SOUL.md / personality.json / YAML into personality frameworks.

Parses agent personality files and extracts the 10 standardized traits,
then maps them to OCEAN and DISC frameworks for comparison and visualization.
"""

from __future__ import annotations

import enum
import json
import logging
import math
from pathlib import Path

from pydantic import BaseModel, Field

from personanexus.compiler import _TRAIT_TEMPLATES
from personanexus.personality import (
    DISC_PRESETS,
    compute_personality_traits,
    traits_to_disc,
    traits_to_ocean,
)
from personanexus.resolver import IdentityResolver
from personanexus.types import (
    DiscProfile,
    OceanProfile,
    PersonalityTraits,
)

logger = logging.getLogger(__name__)


class AnalyzerError(Exception):
    """Raised when analysis fails."""


# ---------------------------------------------------------------------------
# Enums & Data Models
# ---------------------------------------------------------------------------


class SourceFormat(enum.StrEnum):
    SOUL_MD = "soul_md"
    PERSONALITY_JSON = "personality_json"
    IDENTITY_YAML = "identity_yaml"


class TraitExtraction(BaseModel):
    """A single extracted trait with value and confidence."""

    name: str
    value: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_text: str | None = None


class DiscPresetMatch(BaseModel):
    """Closest DISC preset match with Euclidean distance."""

    preset_name: str
    distance: float
    profile: DiscProfile


class AnalysisResult(BaseModel):
    """Complete result of analyzing an agent personality source."""

    source_path: str
    source_format: SourceFormat

    traits: PersonalityTraits
    trait_extractions: list[TraitExtraction] = Field(default_factory=list)

    ocean: OceanProfile
    disc: DiscProfile
    closest_preset: DiscPresetMatch | None = None

    confidence: float = Field(..., ge=0.0, le=1.0)

    agent_name: str | None = None


class TraitDelta(BaseModel):
    """Difference in a single trait between two analyses."""

    trait: str
    value_a: float
    value_b: float
    delta: float


class ComparisonResult(BaseModel):
    """Side-by-side comparison of two analysis results."""

    result_a: AnalysisResult
    result_b: AnalysisResult
    trait_deltas: list[TraitDelta]
    ocean_deltas: dict[str, float]
    disc_deltas: dict[str, float]
    similarity_score: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STANDARD_TRAITS = [
    "warmth", "verbosity", "assertiveness", "humor", "empathy",
    "directness", "rigor", "creativity", "epistemic_humility", "patience",
]

# Level boundaries match _trait_to_language() in compiler.py:
# value < 0.2 → level 0, < 0.4 → level 1, < 0.6 → level 2, < 0.8 → level 3, >= 0.8 → level 4
_LEVEL_MIDPOINTS = [0.1, 0.3, 0.5, 0.7, 0.9]

# Keyword signals for fuzzy matching hand-written SOUL.md files
_KEYWORD_SIGNALS: dict[str, list[tuple[list[str], float]]] = {
    "warmth": [
        (["cold", "detached", "impersonal", "aloof"], 0.15),
        (["reserved", "professional distance"], 0.3),
        (["warm", "friendly", "approachable"], 0.7),
        (["welcoming", "caring", "nurturing", "compassionate"], 0.85),
    ],
    "verbosity": [
        (["concise", "brief", "terse", "succinct"], 0.15),
        (["moderate detail", "balanced"], 0.3),
        (["detailed", "thorough", "comprehensive"], 0.75),
        (["exhaustive", "extremely thorough", "verbose"], 0.9),
    ],
    "assertiveness": [
        (["deferential", "passive", "reactive", "submissive"], 0.15),
        (["balanced", "measured"], 0.4),
        (["assertive", "confident", "proactive"], 0.7),
        (["directive", "commanding", "authoritative"], 0.9),
    ],
    "humor": [
        (["serious", "no-nonsense", "formal"], 0.15),
        (["light-hearted", "occasional humor"], 0.35),
        (["witty", "playful", "humorous", "funny"], 0.75),
        (["highly playful", "comedic", "constantly joking"], 0.9),
    ],
    "empathy": [
        (["task-focused", "efficient", "impersonal"], 0.15),
        (["considerate", "aware"], 0.35),
        (["empathetic", "supportive", "understanding"], 0.7),
        (["deeply empathetic", "emotionally attuned", "emotionally intelligent"], 0.9),
    ],
    "directness": [
        (["diplomatic", "indirect", "tactful", "circumspect"], 0.15),
        (["balanced", "nuanced"], 0.35),
        (["direct", "straightforward", "frank"], 0.7),
        (["blunt", "candid", "no sugarcoating", "brutally honest"], 0.9),
    ],
    "rigor": [
        (["flexible", "adaptive", "loose", "casual"], 0.15),
        (["reasonable", "adequate"], 0.35),
        (["rigorous", "methodical", "systematic"], 0.7),
        (["meticulous", "precise", "exceptional attention to detail"], 0.9),
    ],
    "creativity": [
        (["conventional", "traditional", "proven", "standard"], 0.15),
        (["balanced", "pragmatic"], 0.35),
        (["creative", "innovative", "imaginative"], 0.7),
        (["unconventional", "highly innovative", "visionary"], 0.9),
    ],
    "epistemic_humility": [
        (["confident", "decisive", "certain"], 0.15),
        (["aware of limitations", "careful"], 0.4),
        (["humble", "transparent about uncertainty", "acknowledges limits"], 0.7),
        (["deeply humble", "committed to acknowledging uncertainty"], 0.9),
    ],
    "patience": [
        (["fast-paced", "efficient", "impatient", "brisk"], 0.15),
        (["moderate", "reasonable pace"], 0.35),
        (["patient", "willing to explain", "unhurried"], 0.7),
        (["exceptionally patient", "never rushed", "infinitely patient"], 0.9),
    ],
}


# ---------------------------------------------------------------------------
# Reverse Template Builder
# ---------------------------------------------------------------------------


def _build_reverse_templates() -> dict[str, list[tuple[str, float]]]:
    """Build reverse lookup from compiler's _TRAIT_TEMPLATES.

    Returns mapping of trait_name -> [(phrase, midpoint_value), ...] sorted
    from highest to lowest value so longer/more-specific phrases match first.
    """
    reverse: dict[str, list[tuple[str, float]]] = {}
    for trait_name, templates in _TRAIT_TEMPLATES.items():
        pairs = [
            (template, _LEVEL_MIDPOINTS[i])
            for i, template in enumerate(templates)
        ]
        # Reverse so we match high-value (more specific) phrases first
        reverse[trait_name] = list(reversed(pairs))
    return reverse


_REVERSE_TEMPLATES = _build_reverse_templates()


# ---------------------------------------------------------------------------
# Format Detection
# ---------------------------------------------------------------------------


def detect_format(path: Path) -> SourceFormat:
    """Auto-detect the format of an agent personality file."""
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return SourceFormat.IDENTITY_YAML
    elif suffix == ".json":
        return SourceFormat.PERSONALITY_JSON
    elif suffix == ".md":
        return SourceFormat.SOUL_MD

    # Content-based fallback
    try:
        content = path.read_text(encoding="utf-8")
    except (PermissionError, OSError) as exc:
        raise AnalyzerError(f"Cannot read file {path}: {exc}") from exc

    # Check for oversized files to avoid memory issues
    if len(content) > 1000000:  # 1MB limit
        raise AnalyzerError(f"File {path} is too large to process")

    if "schema_version" in content and "metadata:" in content:
        return SourceFormat.IDENTITY_YAML
    elif content.lstrip().startswith("{"):
        return SourceFormat.PERSONALITY_JSON
    elif content.lstrip().startswith("#"):
        return SourceFormat.SOUL_MD

    raise AnalyzerError(f"Cannot detect format of {path}")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


class PersonalityJsonParser:
    """Extract personality traits from a personality.json file."""

    def parse(self, content: str) -> tuple[dict[str, float], list[TraitExtraction]]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AnalyzerError(f"Invalid JSON: {exc}") from exc

        traits_raw = data.get("personality_traits", {})
        if not traits_raw:
            raise AnalyzerError("No 'personality_traits' key found in JSON")

        extractions: list[TraitExtraction] = []
        traits: dict[str, float] = {}
        for name in STANDARD_TRAITS:
            if name in traits_raw and isinstance(traits_raw[name], (int, float)):
                val = max(0.0, min(1.0, float(traits_raw[name])))
                traits[name] = val
                extractions.append(TraitExtraction(
                    name=name,
                    value=val,
                    confidence=1.0,
                    source_text=f"personality_traits.{name}: {traits_raw[name]}",
                ))

        return traits, extractions

    def extract_name(self, content: str) -> str | None:
        try:
            data = json.loads(content)
            return data.get("agent_name")
        except (json.JSONDecodeError, AttributeError):
            return None


class IdentityYamlParser:
    """Extract personality traits from an personanexus YAML file."""

    def parse(
        self, path: Path, search_paths: list[Path] | None = None,
    ) -> tuple[dict[str, float], list[TraitExtraction]]:
        resolver = IdentityResolver(search_paths=search_paths or [])
        identity = resolver.resolve_file(path)
        try:
            computed = compute_personality_traits(identity.personality)
            traits_dict = computed.defined_traits()
        except Exception as exc:
            raise AnalyzerError(
                f"Failed to compute personality traits from {path}: {exc}"
            ) from exc

        extractions = [
            TraitExtraction(name=k, value=v, confidence=1.0)
            for k, v in traits_dict.items()
        ]
        return traits_dict, extractions

    def extract_name(self, path: Path, search_paths: list[Path] | None = None) -> str | None:
        try:
            resolver = IdentityResolver(search_paths=search_paths or [])
            identity = resolver.resolve_file(path)
            return identity.metadata.name
        except Exception:
            return None


class SoulMdParser:
    """Extract personality traits from SOUL.md Markdown content.

    Uses a two-phase approach:
    1. Exact template matching (confidence 1.0) — matches phrases generated
       by the SoulCompiler.
    2. Keyword fuzzy matching (confidence 0.5-0.7) — handles hand-written files.
    """

    def parse(self, content: str) -> tuple[dict[str, float], list[TraitExtraction]]:
        traits: dict[str, float] = {}
        extractions: list[TraitExtraction] = []
        content_lower = content.lower()

        for trait_name in STANDARD_TRAITS:
            # Phase 1: exact template match
            matched = False
            for phrase, value in _REVERSE_TEMPLATES.get(trait_name, []):
                # The compiler generates "You are {phrase}."
                pattern = f"you are {phrase}".lower()
                if pattern in content_lower:
                    traits[trait_name] = value
                    extractions.append(TraitExtraction(
                        name=trait_name,
                        value=value,
                        confidence=1.0,
                        source_text=f"You are {phrase}.",
                    ))
                    matched = True
                    break

            if matched:
                continue

            # Phase 2: keyword fuzzy match
            best_score = -1.0
            best_value = 0.5
            best_keywords: list[str] = []
            for keywords, value in _KEYWORD_SIGNALS.get(trait_name, []):
                matches = [kw for kw in keywords if kw.lower() in content_lower]
                score = len(matches) / len(keywords) if keywords else 0
                if score > best_score:
                    best_score = score
                    best_value = value
                    best_keywords = matches

            if best_score > 0:
                confidence = min(0.7, 0.3 + best_score * 0.4)
                traits[trait_name] = best_value
                extractions.append(TraitExtraction(
                    name=trait_name,
                    value=best_value,
                    confidence=round(confidence, 2),
                    source_text=f"keywords: {', '.join(best_keywords)}",
                ))
            else:
                # Fallback: neutral with low confidence
                traits[trait_name] = 0.5
                extractions.append(TraitExtraction(
                    name=trait_name,
                    value=0.5,
                    confidence=0.1,
                    source_text=None,
                ))

        return traits, extractions

    def extract_name(self, content: str) -> str | None:
        """Extract agent name from the first markdown heading."""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                return stripped[2:].strip()
        return None


# ---------------------------------------------------------------------------
# DISC Preset Matching
# ---------------------------------------------------------------------------


def find_closest_preset(disc: DiscProfile) -> DiscPresetMatch:
    """Find the closest DISC preset by Euclidean distance."""
    best_name = ""
    best_dist = float("inf")

    for name, preset in DISC_PRESETS.items():
        dist = math.sqrt(
            (disc.dominance - preset.dominance) ** 2
            + (disc.influence - preset.influence) ** 2
            + (disc.steadiness - preset.steadiness) ** 2
            + (disc.conscientiousness - preset.conscientiousness) ** 2
        )
        if dist < best_dist:
            best_dist = dist
            best_name = name

    return DiscPresetMatch(
        preset_name=best_name,
        distance=round(best_dist, 4),
        profile=DISC_PRESETS[best_name],
    )


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------


class SoulAnalyzer:
    """Analyze agent personality files and map to frameworks."""

    def analyze(
        self,
        path: Path,
        search_paths: list[Path] | None = None,
    ) -> AnalysisResult:
        """Analyze any supported personality file.

        Args:
            path: Path to SOUL.md, personality.json, or identity YAML file.
            search_paths: Additional search paths for YAML archetype/mixin resolution.

        Returns:
            AnalysisResult with extracted traits, OCEAN, DISC, and preset match.
        """
        if not path.exists():
            raise AnalyzerError(f"File not found: {path}")

        fmt = detect_format(path)
        content = path.read_text(encoding="utf-8")
        agent_name: str | None = None

        if fmt == SourceFormat.PERSONALITY_JSON:
            parser = PersonalityJsonParser()
            traits_dict, extractions = parser.parse(content)
            agent_name = parser.extract_name(content)

        elif fmt == SourceFormat.IDENTITY_YAML:
            yaml_parser = IdentityYamlParser()
            traits_dict, extractions = yaml_parser.parse(path, search_paths)
            agent_name = yaml_parser.extract_name(path, search_paths)

        elif fmt == SourceFormat.SOUL_MD:
            soul_parser = SoulMdParser()
            traits_dict, extractions = soul_parser.parse(content)
            agent_name = soul_parser.extract_name(content)

        else:
            raise AnalyzerError(f"Unsupported format: {fmt}")

        # Build PersonalityTraits
        traits = PersonalityTraits(**traits_dict)

        # Compute framework mappings
        ocean = traits_to_ocean(traits)
        disc = traits_to_disc(traits)
        closest = find_closest_preset(disc)

        # Overall confidence
        avg_conf = (
            sum(e.confidence for e in extractions) / len(extractions)
            if extractions
            else 0.0
        )

        return AnalysisResult(
            source_path=str(path),
            source_format=fmt,
            traits=traits,
            trait_extractions=extractions,
            ocean=ocean,
            disc=disc,
            closest_preset=closest,
            confidence=round(avg_conf, 2),
            agent_name=agent_name,
        )

    def compare(
        self, result_a: AnalysisResult, result_b: AnalysisResult,
    ) -> ComparisonResult:
        """Compare two analysis results."""
        traits_a = result_a.traits.defined_traits()
        traits_b = result_b.traits.defined_traits()

        # Trait deltas
        all_traits = sorted(set(traits_a) | set(traits_b))
        deltas: list[TraitDelta] = []
        for trait in all_traits:
            va = traits_a.get(trait, 0.5)
            vb = traits_b.get(trait, 0.5)
            deltas.append(TraitDelta(
                trait=trait, value_a=va, value_b=vb,
                delta=round(vb - va, 4),
            ))

        # OCEAN deltas
        oa = result_a.ocean.model_dump()
        ob = result_b.ocean.model_dump()
        ocean_deltas = {k: round(ob[k] - oa[k], 4) for k in oa}

        # DISC deltas
        da = result_a.disc.model_dump()
        db = result_b.disc.model_dump()
        disc_deltas = {k: round(db[k] - da[k], 4) for k in da}

        # Similarity score (cosine similarity on trait vectors)
        similarity = _cosine_similarity(
            [traits_a.get(t, 0.5) for t in STANDARD_TRAITS],
            [traits_b.get(t, 0.5) for t in STANDARD_TRAITS],
        )

        return ComparisonResult(
            result_a=result_a,
            result_b=result_b,
            trait_deltas=deltas,
            ocean_deltas=ocean_deltas,
            disc_deltas=disc_deltas,
            similarity_score=round(similarity, 4),
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (mag_a * mag_b)))
