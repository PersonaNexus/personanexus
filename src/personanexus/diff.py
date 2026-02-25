"""Identity comparison and compatibility scoring."""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from personanexus.personality import DISC_PRESETS, JUNGIAN_PRESETS

# Maximum file size to read (10 MB)
_MAX_FILE_SIZE = 10_000_000


def _load_yaml(path: str | os.PathLike) -> dict:
    """Load a YAML file and return its contents as a dictionary."""
    p = Path(path)
    file_size = p.stat().st_size
    if file_size > _MAX_FILE_SIZE:
        raise ValueError(
            f"File {path} is too large ({file_size:,} bytes, max {_MAX_FILE_SIZE:,})"
        )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten a nested dictionary using dot notation for keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


# ---------------------------------------------------------------------------
# Principles comparison
# ---------------------------------------------------------------------------


def _compare_principles(id1: dict, id2: dict) -> dict:
    """Compare principles between two identities by matching on ``id`` field.

    Args:
        id1: First identity dictionary (raw YAML).
        id2: Second identity dictionary (raw YAML).

    Returns:
        Dictionary with:
            - common: list of shared principle ids
            - unique_to_first: list of principle ids only in id1
            - unique_to_second: list of principle ids only in id2
            - conflicting: list of dicts with id, statement1, statement2
              for principles sharing an id but with different statements
            - alignment_score: 0-100 score of principle alignment
    """
    principles1 = id1.get("principles", [])
    principles2 = id2.get("principles", [])

    if not isinstance(principles1, list):
        principles1 = []
    if not isinstance(principles2, list):
        principles2 = []

    # Build lookup by id
    map1 = {p["id"]: p for p in principles1 if isinstance(p, dict) and "id" in p}
    map2 = {p["id"]: p for p in principles2 if isinstance(p, dict) and "id" in p}

    ids1 = set(map1.keys())
    ids2 = set(map2.keys())

    common_ids = sorted(ids1 & ids2)
    unique_to_first = sorted(ids1 - ids2)
    unique_to_second = sorted(ids2 - ids1)

    # Check for conflicting statements among shared ids
    conflicting = []
    matching_statements = 0
    for pid in common_ids:
        stmt1 = map1[pid].get("statement", "")
        stmt2 = map2[pid].get("statement", "")
        if stmt1 == stmt2:
            matching_statements += 1
        else:
            # Check for partial overlap (word-level)
            words1 = set(stmt1.lower().split())
            words2 = set(stmt2.lower().split())
            if words1 and words2:
                overlap = len(words1 & words2) / max(len(words1 | words2), 1)
            else:
                overlap = 0.0
            if overlap >= 0.5:
                # Partial overlap -- similar enough to not be conflicting
                matching_statements += 1
            else:
                conflicting.append(
                    {
                        "id": pid,
                        "statement1": stmt1,
                        "statement2": stmt2,
                    }
                )

    # Compute alignment score
    all_ids = ids1 | ids2
    if not all_ids:
        alignment_score = 100.0
    else:
        # Score is based on: shared principles with matching statements
        # weighted higher than just shared ids
        total = len(all_ids)
        matched = matching_statements
        # Shared but conflicting get partial credit
        matched += len(conflicting) * 0.25
        alignment_score = round(100.0 * matched / total, 2)

    return {
        "common": common_ids,
        "unique_to_first": unique_to_first,
        "unique_to_second": unique_to_second,
        "conflicting": conflicting,
        "alignment_score": alignment_score,
    }


# ---------------------------------------------------------------------------
# Expertise comparison
# ---------------------------------------------------------------------------


def _compare_expertise(id1: dict, id2: dict) -> dict:
    """Compare expertise domains between two identities by name (case-insensitive).

    Args:
        id1: First identity dictionary (raw YAML).
        id2: Second identity dictionary (raw YAML).

    Returns:
        Dictionary with:
            - shared_domains: list of domain names present in both
            - unique_to_first: list of domain names only in id1
            - unique_to_second: list of domain names only in id2
            - level_differences: dict mapping domain name to
              {level1, level2, delta} for shared domains
            - overlap_score: 0-100 score of expertise overlap
    """
    expertise1 = id1.get("expertise", {})
    expertise2 = id2.get("expertise", {})

    if not isinstance(expertise1, dict):
        expertise1 = {}
    if not isinstance(expertise2, dict):
        expertise2 = {}

    domains1 = expertise1.get("domains", [])
    domains2 = expertise2.get("domains", [])

    if not isinstance(domains1, list):
        domains1 = []
    if not isinstance(domains2, list):
        domains2 = []

    # Build lookup by lowercased name
    map1 = {}
    for d in domains1:
        if isinstance(d, dict) and "name" in d:
            map1[d["name"].lower()] = d
    map2 = {}
    for d in domains2:
        if isinstance(d, dict) and "name" in d:
            map2[d["name"].lower()] = d

    names1 = set(map1.keys())
    names2 = set(map2.keys())

    shared = sorted(names1 & names2)
    unique_first = sorted(names1 - names2)
    unique_second = sorted(names2 - names1)

    # Level differences for shared domains
    level_differences = {}
    for name in shared:
        level1 = map1[name].get("level", 0.0)
        level2 = map2[name].get("level", 0.0)
        if isinstance(level1, (int, float)) and isinstance(level2, (int, float)):
            level_differences[name] = {
                "level1": level1,
                "level2": level2,
                "delta": round(level2 - level1, 4),
            }

    # Overlap score
    all_names = names1 | names2
    overlap_score = 100.0 if not all_names else round(100.0 * len(shared) / len(all_names), 2)

    return {
        "shared_domains": shared,
        "unique_to_first": unique_first,
        "unique_to_second": unique_second,
        "level_differences": level_differences,
        "overlap_score": overlap_score,
    }


# ---------------------------------------------------------------------------
# Communication style comparison
# ---------------------------------------------------------------------------


def _compare_communication(id1: dict, id2: dict) -> dict:
    """Compare communication style between two identities.

    Compares tone.register, tone.default, and style.use_emoji.

    Args:
        id1: First identity dictionary (raw YAML).
        id2: Second identity dictionary (raw YAML).

    Returns:
        Dictionary with:
            - register_match: bool whether registers are the same
            - tone_similarity: float 0-1 (1.0 if default tones match exactly)
            - style_differences: list of (field, val1, val2) for differing style fields
            - compatibility_score: 0-100
    """
    comm1 = id1.get("communication", {})
    comm2 = id2.get("communication", {})

    if not isinstance(comm1, dict):
        comm1 = {}
    if not isinstance(comm2, dict):
        comm2 = {}

    tone1 = comm1.get("tone", {})
    tone2 = comm2.get("tone", {})

    if not isinstance(tone1, dict):
        tone1 = {}
    if not isinstance(tone2, dict):
        tone2 = {}

    style1 = comm1.get("style", {})
    style2 = comm2.get("style", {})

    if not isinstance(style1, dict):
        style1 = {}
    if not isinstance(style2, dict):
        style2 = {}

    # Register comparison
    register1 = tone1.get("register")
    register2 = tone2.get("register")
    register_match = register1 == register2

    # Tone default similarity
    default1 = str(tone1.get("default", "")).lower()
    default2 = str(tone2.get("default", "")).lower()

    if default1 == default2:
        tone_similarity = 1.0
    elif default1 and default2:
        # Word-level overlap for partial matching
        words1 = set(default1.replace("-", " ").replace("_", " ").split())
        words2 = set(default2.replace("-", " ").replace("_", " ").split())
        if words1 | words2:
            tone_similarity = round(len(words1 & words2) / len(words1 | words2), 4)
        else:
            tone_similarity = 0.0
    else:
        tone_similarity = 0.0 if (default1 or default2) else 1.0

    # Style differences
    style_fields = [
        "sentence_length",
        "paragraph_length",
        "use_headers",
        "use_lists",
        "use_code_blocks",
        "use_emoji",
        "preferred_formats",
    ]
    style_differences = []
    style_matches = 0
    style_compared = 0

    for field in style_fields:
        val1 = style1.get(field)
        val2 = style2.get(field)
        # Only compare if both are present
        if val1 is not None and val2 is not None:
            style_compared += 1
            if val1 == val2:
                style_matches += 1
            else:
                style_differences.append((field, val1, val2))

    # Compatibility score: weighted combination
    # register match: 30%, tone similarity: 40%, style similarity: 30%
    register_score = 100.0 if register_match else 0.0

    tone_score = tone_similarity * 100.0

    style_score = 100.0 * style_matches / style_compared if style_compared > 0 else 100.0

    compatibility_score_val = round(
        register_score * 0.30 + tone_score * 0.40 + style_score * 0.30,
        2,
    )

    return {
        "register_match": register_match,
        "tone_similarity": tone_similarity,
        "style_differences": style_differences,
        "compatibility_score": compatibility_score_val,
    }


# ---------------------------------------------------------------------------
# Guardrail conflict detection
# ---------------------------------------------------------------------------


def _compare_guardrails(id1: dict, id2: dict) -> dict:
    """Compare hard guardrails between two identities using word overlap.

    Args:
        id1: First identity dictionary (raw YAML).
        id2: Second identity dictionary (raw YAML).

    Returns:
        Dictionary with:
            - shared_rules: list of rule id pairs that have high overlap
            - unique_to_first: list of rule ids only in id1
            - unique_to_second: list of rule ids only in id2
            - potential_conflicts: list of dicts describing potential conflicts
    """
    guardrails1 = id1.get("guardrails", {})
    guardrails2 = id2.get("guardrails", {})

    if not isinstance(guardrails1, dict):
        guardrails1 = {}
    if not isinstance(guardrails2, dict):
        guardrails2 = {}

    hard1 = guardrails1.get("hard", [])
    hard2 = guardrails2.get("hard", [])

    if not isinstance(hard1, list):
        hard1 = []
    if not isinstance(hard2, list):
        hard2 = []

    # Build lookup by id
    map1 = {r["id"]: r for r in hard1 if isinstance(r, dict) and "id" in r}
    map2 = {r["id"]: r for r in hard2 if isinstance(r, dict) and "id" in r}

    ids1 = set(map1.keys())
    ids2 = set(map2.keys())

    shared_ids = sorted(ids1 & ids2)
    unique_first = sorted(ids1 - ids2)
    unique_second = sorted(ids2 - ids1)

    # For shared rules, check for text similarity
    shared_rules = []
    potential_conflicts = []

    for rid in shared_ids:
        rule1 = str(map1[rid].get("rule", ""))
        rule2 = str(map2[rid].get("rule", ""))

        words1 = set(rule1.lower().split())
        words2 = set(rule2.lower().split())

        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1 | words2), 1)
        else:
            overlap = 1.0 if (not words1 and not words2) else 0.0

        if overlap >= 0.5:
            shared_rules.append(rid)
        else:
            potential_conflicts.append(
                {
                    "id": rid,
                    "rule1": rule1,
                    "rule2": rule2,
                    "word_overlap": round(overlap, 4),
                }
            )

    # Also detect cross-id conflicts: rules in one that might contradict
    # rules in the other (using word overlap of rule text between
    # unique rules on each side)
    for rid1 in unique_first:
        rule1_text = str(map1[rid1].get("rule", "")).lower()
        words1 = set(rule1_text.split())
        if not words1:
            continue
        for rid2 in unique_second:
            rule2_text = str(map2[rid2].get("rule", "")).lower()
            words2 = set(rule2_text.split())
            if not words2:
                continue
            overlap = len(words1 & words2) / max(len(words1 | words2), 1)
            # If there is moderate overlap but they're different rules,
            # that could indicate a conflict or redundancy
            if 0.3 <= overlap < 0.8:
                potential_conflicts.append(
                    {
                        "id1": rid1,
                        "id2": rid2,
                        "rule1": str(map1[rid1].get("rule", "")),
                        "rule2": str(map2[rid2].get("rule", "")),
                        "word_overlap": round(overlap, 4),
                    }
                )

    return {
        "shared_rules": shared_rules,
        "unique_to_first": unique_first,
        "unique_to_second": unique_second,
        "potential_conflicts": potential_conflicts,
    }


# ---------------------------------------------------------------------------
# Change impact analysis
# ---------------------------------------------------------------------------

# Field prefix -> impact category mapping
_IMPACT_CATEGORIES: dict[str, str] = {
    "personality": "behavioral",
    "behavior": "behavioral",
    "guardrails": "safety",
    "principles": "safety",
    "metadata": "structural",
    "schema_version": "structural",
    "extends": "structural",
    "mixins": "structural",
    "role": "structural",
    "evolution": "structural",
    "evaluation": "structural",
    "composition": "structural",
    "communication": "cosmetic",
    "presentation": "cosmetic",
    "expertise": "behavioral",
    "memory": "structural",
    "narrative": "cosmetic",
    "behavioral_modes": "behavioral",
    "interaction": "behavioral",
}

_SEVERITY_MAP: dict[str, str] = {
    "behavioral": "high",
    "safety": "critical",
    "structural": "medium",
    "cosmetic": "low",
}


def _field_to_impact_category(field: str) -> str:
    """Map a dotted field name to an impact category."""
    # Check full prefixes from most specific to least
    parts = field.split(".")
    for i in range(len(parts), 0, -1):
        prefix = ".".join(parts[:i])
        if prefix in _IMPACT_CATEGORIES:
            return _IMPACT_CATEGORIES[prefix]
    # Fallback: check just the top-level key
    top_key = parts[0] if parts else ""
    return _IMPACT_CATEGORIES.get(top_key, "structural")


def _analyze_impact(diff: dict) -> dict:
    """Analyze the impact of changes in a diff result.

    Takes a diff result dictionary (from ``diff_identities``) and categorizes
    each change as behavioral, structural, safety, or cosmetic.

    Args:
        diff: A diff dictionary from ``diff_identities()``.

    Returns:
        Dictionary with:
            - categories: dict mapping category name to list of affected fields
            - field_impacts: dict mapping field name to {category, severity}
            - summary: dict with counts per category
    """
    categories: dict[str, list[str]] = {
        "behavioral": [],
        "structural": [],
        "safety": [],
        "cosmetic": [],
    }
    field_impacts: dict[str, dict[str, str]] = {}

    # Gather all changed / added / removed fields
    all_fields: list[str] = []

    for field, _val1, _val2 in diff.get("changed_fields", []):
        all_fields.append(field)

    for field in diff.get("added_fields", []):
        all_fields.append(field)

    for field in diff.get("removed_fields", []):
        all_fields.append(field)

    for field in all_fields:
        cat = _field_to_impact_category(field)
        severity = _SEVERITY_MAP.get(cat, "medium")
        categories[cat].append(field)
        field_impacts[field] = {"category": cat, "severity": severity}

    summary = {cat: len(fields) for cat, fields in categories.items()}

    return {
        "categories": categories,
        "field_impacts": field_impacts,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Core diff function
# ---------------------------------------------------------------------------


def diff_identities(path1: str, path2: str) -> dict:
    """Load two YAML identity files and return structured diff.

    Args:
        path1: Path to the first identity YAML file.
        path2: Path to the second identity YAML file.

    Returns:
        A dictionary containing:
            - changed_fields: list of (field, val1, val2) tuples
            - added_fields: fields present in id2 but not in id1
            - removed_fields: fields present in id1 but not in id2
            - personality_diff: dict of personality trait deltas if OCEAN/DISC present
            - principles_comparison: result of _compare_principles
            - expertise_comparison: result of _compare_expertise
            - communication_comparison: result of _compare_communication
            - guardrails_comparison: result of _compare_guardrails
            - impact_analysis: result of _analyze_impact
    """
    id1 = _load_yaml(path1)
    id2 = _load_yaml(path2)

    flat1 = _flatten_dict(id1)
    flat2 = _flatten_dict(id2)

    keys1 = set(flat1.keys())
    keys2 = set(flat2.keys())

    removed_fields = sorted(keys1 - keys2)
    added_fields = sorted(keys2 - keys1)
    common_keys = keys1 & keys2

    changed_fields = []
    for key in sorted(common_keys):
        if flat1[key] != flat2[key]:
            changed_fields.append((key, flat1[key], flat2[key]))

    # Extract personality differences if OCEAN or DISC is present
    personality_diff = _extract_personality_diff(id1, id2)

    # Semantic comparisons
    principles_comparison = _compare_principles(id1, id2)
    expertise_comparison = _compare_expertise(id1, id2)
    communication_comparison = _compare_communication(id1, id2)
    guardrails_comparison = _compare_guardrails(id1, id2)

    # Build base result (without impact_analysis) first
    result = {
        "changed_fields": changed_fields,
        "added_fields": added_fields,
        "removed_fields": removed_fields,
        "personality_diff": personality_diff,
        "principles_comparison": principles_comparison,
        "expertise_comparison": expertise_comparison,
        "communication_comparison": communication_comparison,
        "guardrails_comparison": guardrails_comparison,
    }

    # Impact analysis uses the base diff fields
    result["impact_analysis"] = _analyze_impact(result)

    return result


# ---------------------------------------------------------------------------
# Personality extraction helpers
# ---------------------------------------------------------------------------


def _extract_personality_diff(id1: dict, id2: dict) -> dict:
    """Extract personality trait differences between two identities.

    Args:
        id1: First identity dictionary.
        id2: Second identity dictionary.

    Returns:
        Dictionary with OCEAN and/or DISC trait differences.
    """
    personality_diff = {}

    # Check OCEAN traits
    ocean1 = _get_ocean_traits(id1)
    ocean2 = _get_ocean_traits(id2)

    if ocean1 and ocean2:
        ocean_diff = {}
        for trait in ocean1:
            if trait in ocean2 and ocean1[trait] is not None and ocean2[trait] is not None:
                delta = ocean2[trait] - ocean1[trait]
                ocean_diff[trait] = {
                    "val1": ocean1[trait],
                    "val2": ocean2[trait],
                    "delta": delta,
                }
        personality_diff["ocean"] = ocean_diff

    # Check DISC traits
    disc1 = _get_disc_traits(id1)
    disc2 = _get_disc_traits(id2)

    if disc1 and disc2:
        disc_diff = {}
        for trait in disc1:
            if trait in disc2 and disc1[trait] is not None and disc2[trait] is not None:
                delta = disc2[trait] - disc1[trait]
                disc_diff[trait] = {
                    "val1": disc1[trait],
                    "val2": disc2[trait],
                    "delta": delta,
                }
        personality_diff["disc"] = disc_diff

    # Check Jungian traits
    jungian1 = _get_jungian_traits(id1)
    jungian2 = _get_jungian_traits(id2)

    if jungian1 and jungian2:
        jungian_diff = {}
        for trait in jungian1:
            if trait in jungian2 and jungian1[trait] is not None and jungian2[trait] is not None:
                delta = jungian2[trait] - jungian1[trait]
                jungian_diff[trait] = {
                    "val1": jungian1[trait],
                    "val2": jungian2[trait],
                    "delta": delta,
                }
        personality_diff["jungian"] = jungian_diff

    return personality_diff


def _get_ocean_traits(identity: dict) -> dict | None:
    """Extract OCEAN traits from an identity dictionary.

    Returns None if OCEAN personality is not present.
    """
    personality = identity.get("personality", {})
    profile = personality.get("profile", {})
    if profile.get("mode") == "ocean":
        ocean = profile.get("ocean", {})
        if ocean:
            return {
                "openness": ocean.get("openness"),
                "conscientiousness": ocean.get("conscientiousness"),
                "extraversion": ocean.get("extraversion"),
                "agreeableness": ocean.get("agreeableness"),
                "neuroticism": ocean.get("neuroticism"),
            }
    return None


def _get_disc_traits(identity: dict) -> dict | None:
    """Extract DISC traits from an identity dictionary.

    Returns None if DISC personality is not present.
    """
    personality = identity.get("personality", {})
    profile = personality.get("profile", {})
    if profile.get("mode") == "disc":
        disc = profile.get("disc", {})
        if disc:
            return {
                "dominance": disc.get("dominance"),
                "influence": disc.get("influence"),
                "steadiness": disc.get("steadiness"),
                "conscientiousness": disc.get("conscientiousness"),
            }
        # Check for preset values using canonical DISC_PRESETS
        disc_preset = profile.get("disc_preset")
        if disc_preset and disc_preset in DISC_PRESETS:
            p = DISC_PRESETS[disc_preset]
            return {
                "dominance": p.dominance,
                "influence": p.influence,
                "steadiness": p.steadiness,
                "conscientiousness": p.conscientiousness,
            }
    return None


def _get_jungian_traits(identity: dict) -> dict | None:
    """Extract Jungian traits from an identity dictionary.

    Returns None if Jungian personality is not present.
    """
    personality = identity.get("personality", {})
    profile = personality.get("profile", {})
    if profile.get("mode") == "jungian":
        jungian = profile.get("jungian", {})
        if jungian:
            return {
                "ei": jungian.get("ei"),
                "sn": jungian.get("sn"),
                "tf": jungian.get("tf"),
                "jp": jungian.get("jp"),
            }
        # Check for preset values using canonical JUNGIAN_PRESETS
        jungian_preset = profile.get("jungian_preset")
        if jungian_preset and jungian_preset.lower() in JUNGIAN_PRESETS:
            p = JUNGIAN_PRESETS[jungian_preset.lower()]
            return {
                "ei": p.ei,
                "sn": p.sn,
                "tf": p.tf,
                "jp": p.jp,
            }
    return None


# ---------------------------------------------------------------------------
# Compatibility scoring
# ---------------------------------------------------------------------------


def compatibility_score(path1: str, path2: str) -> float:
    """Return 0-100 compatibility score based on personality, principles, expertise,
    and communication alignment.

    Base weighting: personality 50%, principles 25%, expertise 15%, communication 10%.

    When a section is absent from both identities (e.g. neither has principles),
    that section's weight is redistributed proportionally to the remaining sections
    so the score remains backward-compatible with personality-only comparisons.

    Args:
        path1: Path to the first identity YAML file.
        path2: Path to the second identity YAML file.

    Returns:
        A score from 0 to 100, where 100 indicates perfect alignment.
    """
    id1 = _load_yaml(path1)
    id2 = _load_yaml(path2)

    # Collect (score, weight) pairs, only including sections that have data
    # in at least one identity.
    components: list[tuple[float, float]] = []

    # --- Personality (always included with base weight 50%) ---
    personality_score = _personality_compatibility(id1, id2)
    components.append((personality_score, 0.50))

    # --- Principles (25%) — only if at least one identity has principles ---
    has_principles = bool(id1.get("principles")) or bool(id2.get("principles"))
    if has_principles:
        principles = _compare_principles(id1, id2)
        components.append((principles["alignment_score"], 0.25))

    # --- Expertise (15%) — only if at least one identity has expertise domains ---
    exp1 = id1.get("expertise", {})
    exp2 = id2.get("expertise", {})
    has_expertise = bool(
        (isinstance(exp1, dict) and exp1.get("domains"))
        or (isinstance(exp2, dict) and exp2.get("domains"))
    )
    if has_expertise:
        expertise = _compare_expertise(id1, id2)
        components.append((expertise["overlap_score"], 0.15))

    # --- Communication (10%) — only if at least one identity has communication ---
    has_communication = bool(id1.get("communication")) or bool(id2.get("communication"))
    if has_communication:
        communication = _compare_communication(id1, id2)
        components.append((communication["compatibility_score"], 0.10))

    # Normalize weights so they sum to 1.0
    total_weight = sum(w for _, w in components)
    if total_weight <= 0:
        return 50.0

    weighted = sum(score * (w / total_weight) for score, w in components)
    return round(weighted, 2)


def _personality_compatibility(id1: dict, id2: dict) -> float:
    """Compute personality-only compatibility score (0-100) from raw identity dicts."""
    # Extract personality traits
    ocean1 = _get_ocean_traits(id1)
    ocean2 = _get_ocean_traits(id2)

    if ocean1 and ocean2:
        return _calculate_ocean_compatibility(ocean1, ocean2)

    disc1 = _get_disc_traits(id1)
    disc2 = _get_disc_traits(id2)

    if disc1 and disc2:
        return _calculate_disc_compatibility(disc1, disc2)

    # Check for direct traits
    traits1 = _get_personality_traits(id1)
    traits2 = _get_personality_traits(id2)

    if traits1 and traits2:
        return _calculate_traits_compatibility(traits1, traits2)

    # No personality data: neutral
    return 50.0


def _get_personality_traits(identity: dict) -> dict | None:
    """Extract personality traits from an identity dictionary.

    Returns None if personality traits are not present.
    """
    personality = identity.get("personality", {})
    traits = personality.get("traits", {})
    if traits:
        return traits
    return None


def _calculate_traits_compatibility(traits1: dict, traits2: dict) -> float:
    """Calculate compatibility score based on direct personality trait similarity.

    Uses Euclidean distance in trait space, normalized to 0-100.
    """
    # Get all trait keys from both
    all_traits = set(traits1.keys()) & set(traits2.keys())

    if not all_traits:
        return 50.0

    # Calculate Euclidean distance
    distance_sq = sum((traits1[t] - traits2[t]) ** 2 for t in all_traits)

    # Max theoretical distance depends on number of traits and range
    # Each trait is 0-1, so max delta per trait is 1
    # Max distance = sqrt(n) for n traits
    max_distance = len(all_traits) ** 0.5
    distance = distance_sq**0.5

    # Normalize to 0-100 (closer = higher score)
    score = 100 * (1 - (distance / max_distance))
    return round(score, 2)


def _calculate_ocean_compatibility(ocean1: dict, ocean2: dict) -> float:
    """Calculate compatibility score based on OCEAN trait similarity.

    Uses Euclidean distance in 5D space, normalized to 0-100.
    """
    traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

    # Calculate Euclidean distance
    distance_sq = sum(
        (ocean1[t] - ocean2[t]) ** 2
        for t in traits
        if ocean1.get(t) is not None and ocean2.get(t) is not None
    )

    # Max theoretical distance is sqrt(5 * 1^2) = sqrt(5) ~ 2.236
    max_distance = 5**0.5
    distance = distance_sq**0.5

    # Normalize to 0-100 (closer = higher score)
    score = 100 * (1 - (distance / max_distance))
    return round(score, 2)


def _calculate_disc_compatibility(disc1: dict, disc2: dict) -> float:
    """Calculate compatibility score based on DISC trait similarity."""
    traits = ["dominance", "influence", "steadiness", "conscientiousness"]

    # Calculate Euclidean distance
    distance_sq = sum(
        (disc1[t] - disc2[t]) ** 2
        for t in traits
        if disc1.get(t) is not None and disc2.get(t) is not None
    )

    # Max theoretical distance is sqrt(4 * 1^2) = 2
    max_distance = 2.0
    distance = distance_sq**0.5

    # Normalize to 0-100
    score = 100 * (1 - (distance / max_distance))
    return round(score, 2)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _fmt_trait_delta(trait: str, data: dict, md: bool) -> str:
    """Format a single trait delta line for text or markdown."""
    delta = data["delta"]
    sign = "+" if delta >= 0 else ""
    if md:
        return f"- **{trait}:** {data['val1']} -> {data['val2']} ({sign}{delta})"
    return f"  {trait}: {data['val1']} -> {data['val2']} ({sign}{delta})"


def format_diff(diff: dict, fmt: str = "text") -> str:
    """Format diff as text, json, or markdown.

    Args:
        diff: A diff dictionary from diff_identities().
        fmt: Output format - "text", "json", or "markdown".

    Returns:
        Formatted string representation of the diff.
    """
    if fmt == "json":
        return json.dumps(diff, indent=2, default=str)

    md = fmt == "markdown"
    lines: list[str] = []

    # Header
    if md:
        lines += ["# Identity Diff Report", ""]
    else:
        lines += ["=" * 60, "IDENTITY DIFF REPORT", "=" * 60, ""]

    # --- Changed fields ---
    changed = diff.get("changed_fields", [])
    lines.append("## Changed Fields" if md else "CHANGED FIELDS:")
    if changed:
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")
        for field, val1, val2 in changed:
            if md:
                lines += [f"### `{field}`", f"- **Old:** `{val1}`", f"- **New:** `{val2}`", ""]
            else:
                lines += [f"  {field}:", f"    old: {val1}", f"    new: {val2}"]
        if not md:
            lines.append("")
    else:
        if md:
            lines += ["", "*None*", ""]
        else:
            lines[-1] += " (none)"
            lines.append("")

    # --- Added fields ---
    added = diff.get("added_fields", [])
    lines.append("## Added Fields" if md else "ADDED FIELDS:")
    if added:
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")
        for field in added:
            lines.append(f"- `+ {field}`" if md else f"  + {field}")
        lines.append("")
    else:
        if md:
            lines += ["", "*None*", ""]
        else:
            lines[-1] += " (none)"
            lines.append("")

    # --- Removed fields ---
    removed = diff.get("removed_fields", [])
    lines.append("## Removed Fields" if md else "REMOVED FIELDS:")
    if removed:
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")
        for field in removed:
            lines.append(f"- `- {field}`" if md else f"  - {field}")
        lines.append("")
    else:
        if md:
            lines += ["", "*None*", ""]
        else:
            lines[-1] += " (none)"
            lines.append("")

    # --- Personality diff ---
    personality = diff.get("personality_diff", {})
    if personality:
        lines.append("## Personality Differences" if md else "PERSONALITY DIFFERENCES:")
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")

        for framework, label in [("ocean", "OCEAN Traits"), ("disc", "DISC Traits"),
                                  ("jungian", "Jungian Profile")]:
            if framework in personality:
                lines.append(f"### {label}" if md else f"{label}:")
                if md:
                    lines.append("")
                for trait, data in personality[framework].items():
                    lines.append(_fmt_trait_delta(trait, data, md))
                if md:
                    lines.append("")
        if not md:
            lines.append("")
    elif not md:
        lines += ["PERSONALITY DIFFERENCES: (none)", ""]

    # --- Principles comparison ---
    principles = diff.get("principles_comparison")
    if principles:
        lines.append("## Principles Alignment" if md else "PRINCIPLES ALIGNMENT:")
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")
        score_line = f"Alignment Score: {principles['alignment_score']}%"
        lines.append(f"**{score_line}**" if md else f"  {score_line}")
        if md:
            lines.append("")
        if principles["common"]:
            val = ", ".join(principles["common"])
            lines.append(f"**Common:** {val}" if md else f"  Common: {val}")
            if md:
                lines.append("")
        if principles["unique_to_first"]:
            if md:
                lines.append("**Only in first:**")
                for p in principles["unique_to_first"]:
                    lines.append(f"- `{p}`")
            else:
                lines.append(f"  Only in first: {', '.join(principles['unique_to_first'])}")
            if md:
                lines.append("")
        if principles["unique_to_second"]:
            if md:
                lines.append("**Only in second:**")
                for p in principles["unique_to_second"]:
                    lines.append(f"- `{p}`")
            else:
                lines.append(f"  Only in second: {', '.join(principles['unique_to_second'])}")
            if md:
                lines.append("")
        if principles["conflicting"]:
            if md:
                lines += ["**Conflicting Principles:**", ""]
                for c in principles["conflicting"]:
                    lines += [f"- **{c['id']}**", f"  - First: {c['statement1']}",
                              f"  - Second: {c['statement2']}"]
            else:
                lines.append("  Conflicting:")
                for c in principles["conflicting"]:
                    lines += [f"    {c['id']}:", f"      first:  {c['statement1']}",
                              f"      second: {c['statement2']}"]
            if md:
                lines.append("")
        lines.append("")

    # --- Expertise comparison ---
    expertise = diff.get("expertise_comparison")
    if expertise:
        lines.append("## Expertise Overlap" if md else "EXPERTISE OVERLAP:")
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")
        score_line = f"Overlap Score: {expertise['overlap_score']}%"
        lines.append(f"**{score_line}**" if md else f"  {score_line}")
        if md:
            lines.append("")
        if expertise["shared_domains"]:
            if md:
                lines.append("**Shared Domains:**")
                for d in expertise["shared_domains"]:
                    level_info = expertise["level_differences"].get(d)
                    if level_info:
                        lines.append(
                            f"- `{d}`: {level_info['level1']} vs {level_info['level2']} "
                            f"(delta: {level_info['delta']:+})"
                        )
                    else:
                        lines.append(f"- `{d}`")
            else:
                lines.append(f"  Shared: {', '.join(expertise['shared_domains'])}")
            if md:
                lines.append("")
        if expertise["unique_to_first"]:
            if md:
                lines.append("**Only in first:**")
                for d in expertise["unique_to_first"]:
                    lines.append(f"- `{d}`")
            else:
                lines.append(f"  Only in first: {', '.join(expertise['unique_to_first'])}")
            if md:
                lines.append("")
        if expertise["unique_to_second"]:
            if md:
                lines.append("**Only in second:**")
                for d in expertise["unique_to_second"]:
                    lines.append(f"- `{d}`")
            else:
                lines.append(f"  Only in second: {', '.join(expertise['unique_to_second'])}")
            if md:
                lines.append("")
        if not md and expertise.get("level_differences"):
            lines.append("  Level Differences:")
            for name, data in expertise["level_differences"].items():
                lines.append(
                    f"    {name}: {data['level1']} -> {data['level2']} (delta: {data['delta']:+})"
                )
        lines.append("")

    # --- Communication comparison ---
    communication = diff.get("communication_comparison")
    if communication:
        lines.append(
            "## Communication Compatibility" if md else "COMMUNICATION COMPATIBILITY:"
        )
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")
        score_line = f"Compatibility Score: {communication['compatibility_score']}%"
        lines.append(f"**{score_line}**" if md else f"  {score_line}")
        if md:
            lines.append("")
        reg = f"Register Match: {communication['register_match']}"
        tone = f"Tone Similarity: {communication['tone_similarity']}"
        if md:
            lines += [f"- **{reg}**", f"- **{tone}**"]
        else:
            lines += [f"  {reg}", f"  {tone}"]
        if communication["style_differences"]:
            if md:
                lines += ["", "**Style Differences:**", ""]
                for field, val1, val2 in communication["style_differences"]:
                    lines.append(f"- `{field}`: `{val1}` -> `{val2}`")
            else:
                lines.append("  Style Differences:")
                for field, val1, val2 in communication["style_differences"]:
                    lines.append(f"    {field}: {val1} -> {val2}")
        lines.append("")

    # --- Guardrails comparison ---
    guardrails = diff.get("guardrails_comparison")
    if guardrails:
        lines.append("## Guardrail Comparison" if md else "GUARDRAIL COMPARISON:")
        if not md:
            lines.append("-" * 40)
        else:
            lines.append("")
        for key, label in [("shared_rules", "Shared"), ("unique_to_first", "Only in first"),
                           ("unique_to_second", "Only in second")]:
            items = guardrails.get(key, [])
            if items:
                if md:
                    lines.append(f"**{label}:**" if key != "shared_rules" else "**Shared Rules:**")
                    for r in items:
                        lines.append(f"- `{r}`")
                    lines.append("")
                else:
                    lines.append(f"  {label}: {', '.join(items)}")
        if guardrails["potential_conflicts"]:
            if md:
                lines += ["**Potential Conflicts:**", ""]
            else:
                lines.append("  Potential Conflicts:")
            for c in guardrails["potential_conflicts"]:
                if "id" in c:
                    if md:
                        lines.append(f"- **{c['id']}** (overlap: {c['word_overlap']})")
                    else:
                        lines.append(f"    {c['id']}: overlap={c['word_overlap']}")
                else:
                    if md:
                        lines.append(
                            f"- **{c['id1']}** vs **{c['id2']}** (overlap: {c['word_overlap']})"
                        )
                    else:
                        lines.append(
                            f"    {c['id1']} vs {c['id2']}: overlap={c['word_overlap']}"
                        )
            if md:
                lines.append("")
        lines.append("")

    # --- Impact analysis ---
    impact = diff.get("impact_analysis")
    if impact:
        summary = impact.get("summary", {})
        has_changes = any(v > 0 for v in summary.values())
        if has_changes:
            lines.append(
                "## Change Impact Analysis" if md else "CHANGE IMPACT ANALYSIS:"
            )
            if md:
                lines += [
                    "",
                    "| Category | Severity | Fields |",
                    "|----------|----------|--------|",
                ]
                for cat, count in summary.items():
                    if count > 0:
                        severity = _SEVERITY_MAP.get(cat, "medium")
                        lines.append(f"| {cat} | {severity} | {count} |")
            else:
                lines.append("-" * 40)
                for cat, count in summary.items():
                    if count > 0:
                        severity = _SEVERITY_MAP.get(cat, "medium")
                        lines.append(f"  {cat} ({severity}): {count} field(s)")
            lines.append("")

    return "\n".join(lines)


def format_diff_markdown(diff: dict) -> str:
    """Format diff as markdown. Convenience wrapper around format_diff."""
    return format_diff(diff, fmt="markdown")
