"""Identity comparison and compatibility scoring."""

from __future__ import annotations

import json
import os

import yaml

from personanexus.personality import DISC_PRESETS


def _load_yaml(path: str | os.PathLike) -> dict:
    """Load a YAML file and return its contents as a dictionary."""
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

    return {
        "changed_fields": changed_fields,
        "added_fields": added_fields,
        "removed_fields": removed_fields,
        "personality_diff": personality_diff,
    }


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


def compatibility_score(path1: str, path2: str) -> float:
    """Return 0-100 compatibility score based on personality alignment.

    Args:
        path1: Path to the first identity YAML file.
        path2: Path to the second identity YAML file.

    Returns:
        A score from 0 to 100, where 100 indicates perfect personality alignment.
    """
    id1 = _load_yaml(path1)
    id2 = _load_yaml(path2)

    # Extract personality traits
    ocean1 = _get_ocean_traits(id1)
    ocean2 = _get_ocean_traits(id2)

    if ocean1 and ocean2:
        # Use OCEAN traits for compatibility
        return _calculate_ocean_compatibility(ocean1, ocean2)

    disc1 = _get_disc_traits(id1)
    disc2 = _get_disc_traits(id2)

    if disc1 and disc2:
        # Use DISC traits for compatibility
        return _calculate_disc_compatibility(disc1, disc2)

    # If no OCEAN/DISC profile, check for direct traits
    traits1 = _get_personality_traits(id1)
    traits2 = _get_personality_traits(id2)

    if traits1 and traits2:
        # Use direct personality traits for compatibility
        return _calculate_traits_compatibility(traits1, traits2)

    # If no personality data, return 50 (neutral)
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
    distance = distance_sq ** 0.5

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

    # Max theoretical distance is sqrt(5 * 1^2) = sqrt(5) ≈ 2.236
    max_distance = (5 ** 0.5)
    distance = distance_sq ** 0.5

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
    distance = distance_sq ** 0.5

    # Normalize to 0-100
    score = 100 * (1 - (distance / max_distance))
    return round(score, 2)


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

    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("IDENTITY DIFF REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Changed fields
    changed = diff.get("changed_fields", [])
    if changed:
        lines.append("CHANGED FIELDS:")
        lines.append("-" * 40)
        for field, val1, val2 in changed:
            lines.append(f"  {field}:")
            lines.append(f"    old: {val1}")
            lines.append(f"    new: {val2}")
        lines.append("")
    else:
        lines.append("CHANGED FIELDS: (none)")
        lines.append("")

    # Added fields
    added = diff.get("added_fields", [])
    if added:
        lines.append("ADDED FIELDS:")
        lines.append("-" * 40)
        for field in added:
            lines.append(f"  + {field}")
        lines.append("")
    else:
        lines.append("ADDED FIELDS: (none)")
        lines.append("")

    # Removed fields
    removed = diff.get("removed_fields", [])
    if removed:
        lines.append("REMOVED FIELDS:")
        lines.append("-" * 40)
        for field in removed:
            lines.append(f"  - {field}")
        lines.append("")
    else:
        lines.append("REMOVED FIELDS: (none)")
        lines.append("")

    # Personality diff
    personality = diff.get("personality_diff", {})
    if personality:
        lines.append("PERSONALITY DIFFERENCES:")
        lines.append("-" * 40)

        if "ocean" in personality:
            lines.append("OCEAN Traits:")
            for trait, data in personality["ocean"].items():
                delta = data["delta"]
                sign = "+" if delta >= 0 else ""
                lines.append(f"  {trait}: {data['val1']} → {data['val2']} ({sign}{delta})")

        if "disc" in personality:
            lines.append("DISC Traits:")
            for trait, data in personality["disc"].items():
                delta = data["delta"]
                sign = "+" if delta >= 0 else ""
                lines.append(f"  {trait}: {data['val1']} → {data['val2']} ({sign}{delta})")
        lines.append("")
    else:
        lines.append("PERSONALITY DIFFERENCES: (none)")
        lines.append("")

    return "\n".join(lines)


def format_diff_markdown(diff: dict) -> str:
    """Format diff as markdown (alias for format_diff with fmt='markdown')."""
    lines = []

    lines.append("# Identity Diff Report")
    lines.append("")

    # Changed fields
    changed = diff.get("changed_fields", [])
    if changed:
        lines.append("## Changed Fields")
        lines.append("")
        for field, val1, val2 in changed:
            lines.append(f"### `{field}`")
            lines.append(f"- **Old:** `{val1}`")
            lines.append(f"- **New:** `{val2}`")
            lines.append("")
    else:
        lines.append("## Changed Fields")
        lines.append("")
        lines.append("*None*")
        lines.append("")

    # Added fields
    added = diff.get("added_fields", [])
    if added:
        lines.append("## Added Fields")
        lines.append("")
        for field in added:
            lines.append(f"- `+ {field}`")
        lines.append("")
    else:
        lines.append("## Added Fields")
        lines.append("")
        lines.append("*None*")
        lines.append("")

    # Removed fields
    removed = diff.get("removed_fields", [])
    if removed:
        lines.append("## Removed Fields")
        lines.append("")
        for field in removed:
            lines.append(f"- `- {field}`")
        lines.append("")
    else:
        lines.append("## Removed Fields")
        lines.append("")
        lines.append("*None*")
        lines.append("")

    # Personality diff
    personality = diff.get("personality_diff", {})
    if personality:
        lines.append("## Personality Differences")
        lines.append("")

        if "ocean" in personality:
            lines.append("### OCEAN Traits")
            lines.append("")
            for trait, data in personality["ocean"].items():
                delta = data["delta"]
                sign = "+" if delta >= 0 else ""
                lines.append(f"- **{trait}:** {data['val1']} → {data['val2']} ({sign}{delta})")
            lines.append("")

        if "disc" in personality:
            lines.append("### DISC Traits")
            lines.append("")
            for trait, data in personality["disc"].items():
                delta = data["delta"]
                sign = "+" if delta >= 0 else ""
                lines.append(f"- **{trait}:** {data['val1']} → {data['val2']} ({sign}{delta})")
            lines.append("")

    return "\n".join(lines)
