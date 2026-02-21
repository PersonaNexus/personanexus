"""Conflict resolution strategies for identity inheritance and mixin composition."""

from __future__ import annotations

from typing import Any

from personanexus.types import (
    ConflictResolution,
    ListConflictStrategy,
    NumericConflictStrategy,
    ObjectConflictStrategy,
)


class ConflictResolver:
    """Resolves conflicts when merging identity specs during inheritance/mixin composition."""

    def __init__(self, config: ConflictResolution | None = None):
        self.config = config or ConflictResolution()

    def merge(self, base: dict[str, Any], override: dict[str, Any], path: str = "") -> dict[str, Any]:
        """Deep-merge override into base using configured conflict resolution strategies."""
        result = dict(base)

        for key, override_val in override.items():
            current_path = f"{path}.{key}" if path else key
            base_val = base.get(key)

            # Check for explicit per-field strategy
            explicit = self._get_explicit_strategy(current_path)

            if base_val is None:
                result[key] = override_val
            elif explicit:
                result[key] = self._apply_explicit(base_val, override_val, explicit)
            elif isinstance(base_val, dict) and isinstance(override_val, dict):
                result[key] = self._merge_objects(base_val, override_val, current_path)
            elif isinstance(base_val, list) and isinstance(override_val, list):
                result[key] = self._merge_lists(base_val, override_val, current_path)
            elif isinstance(base_val, (int, float)) and isinstance(override_val, (int, float)):
                result[key] = self._merge_numeric(base_val, override_val, current_path)
            else:
                # String or other primitives: last wins
                result[key] = override_val

        return result

    def _merge_numeric(self, base: float, override: float, path: str) -> float:
        strategy = self.config.numeric_traits
        if strategy == NumericConflictStrategy.LAST_WINS:
            return override
        elif strategy == NumericConflictStrategy.HIGHEST:
            return max(base, override)
        elif strategy == NumericConflictStrategy.LOWEST:
            return min(base, override)
        elif strategy == NumericConflictStrategy.AVERAGE:
            return (base + override) / 2
        return override

    def _merge_lists(self, base: list[Any], override: list[Any], path: str) -> list[Any]:
        # Check for _merge_strategy in override (if it's a list of dicts with this key)
        strategy = self.config.list_fields

        # Special case: lists of dicts with 'id' keys get merged by id (override wins)
        # This applies to guardrails.hard, principles, expertise.domains, etc.
        if self._is_id_keyed_list(base, override):
            return self._union_by_id(base, override)

        if strategy == ListConflictStrategy.REPLACE:
            return override
        elif strategy == ListConflictStrategy.APPEND:
            return base + override
        elif strategy == ListConflictStrategy.UNIQUE_APPEND:
            seen = set()
            result = []
            for item in base + override:
                key = self._list_item_key(item)
                if key not in seen:
                    seen.add(key)
                    result.append(item)
            return result
        return override

    def _merge_objects(self, base: dict[str, Any], override: dict[str, Any], path: str) -> dict[str, Any]:
        strategy = self.config.object_fields
        if strategy == ObjectConflictStrategy.REPLACE:
            return override
        # deep_merge is the default
        return self.merge(base, override, path)

    def _get_explicit_strategy(self, path: str) -> str | None:
        for resolution in self.config.explicit_resolutions:
            if resolution.field == path:
                return resolution.strategy
        return None

    def _apply_explicit(self, base: Any, override: Any, strategy: str) -> Any:
        if strategy == "union" and isinstance(base, list) and isinstance(override, list):
            return self._union_by_id(base, override)
        if strategy == "highest" and isinstance(base, (int, float)) and isinstance(override, (int, float)):
            return max(base, override)
        if strategy == "lowest" and isinstance(base, (int, float)) and isinstance(override, (int, float)):
            return min(base, override)
        if strategy == "average" and isinstance(base, (int, float)) and isinstance(override, (int, float)):
            return (base + override) / 2
        # Default: last wins
        return override

    def _is_id_keyed_list(self, base: list[Any], override: list[Any]) -> bool:
        """Check if both lists contain dicts with 'id' fields."""
        all_items = base + override
        if not all_items:
            return False
        return all(isinstance(item, dict) and "id" in item for item in all_items)

    def _union_by_id(self, base: list[Any], override: list[Any]) -> list[Any]:
        """Merge lists of dicts by 'id' field. Override wins for matching ids."""
        result_map: dict[str, Any] = {}
        for item in base:
            item_id = item.get("id") if isinstance(item, dict) else str(item)
            result_map[str(item_id)] = item
        for item in override:
            item_id = item.get("id") if isinstance(item, dict) else str(item)
            result_map[str(item_id)] = item  # override wins
        return list(result_map.values())

    def _list_item_key(self, item: Any) -> str:
        """Create a hashable key for list deduplication."""
        if isinstance(item, dict):
            return str(item.get("id", item))
        return str(item)
