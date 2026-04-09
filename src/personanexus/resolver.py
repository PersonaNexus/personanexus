"""Inheritance and mixin resolution for PersonaNexus specs."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from personanexus.conflict import ConflictResolver, MergeTrace
from personanexus.parser import IdentityParser, ParseError
from personanexus.types import AgentIdentity, ConflictResolution

logger = logging.getLogger(__name__)


class ResolutionError(Exception):
    """Raised when identity resolution fails."""


class IdentityResolver:
    """Resolves identity inheritance (extends), mixins, and overrides into a single spec."""

    def __init__(self, search_paths: Sequence[str | Path] | None = None, max_depth: int = 10):
        self.search_paths = [Path(p) for p in (search_paths or [])]
        self.max_depth = max_depth
        self._parser = IdentityParser()

    def resolve_file(self, path: str | Path) -> AgentIdentity:
        """Load and fully resolve an identity file."""
        path = Path(path)
        data = self._parser.parse_file(path)
        resolved = self._resolve(data, path, depth=0, stack=[])
        return AgentIdentity.model_validate(resolved)

    def resolve_file_traced(self, path: str | Path) -> tuple[AgentIdentity, MergeTrace]:
        """Load and fully resolve an identity file, returning a merge trace.

        Returns a tuple of (resolved identity, trace of all merge operations).
        """
        path = Path(path)
        data = self._parser.parse_file(path)
        trace = MergeTrace()
        resolved = self._resolve(data, path, depth=0, stack=[], trace=trace)
        return AgentIdentity.model_validate(resolved), trace

    def resolve_dict(
        self, data: dict[str, Any], base_path: str | Path | None = None
    ) -> AgentIdentity:
        """Resolve an already-parsed identity dict."""
        bp = Path(base_path) if base_path else Path.cwd() / "identity.yaml"
        resolved = self._resolve(data, bp, depth=0, stack=[])
        return AgentIdentity.model_validate(resolved)

    # ------------------------------------------------------------------
    # Internal resolution pipeline
    # ------------------------------------------------------------------

    def _resolve(
        self,
        data: dict[str, Any],
        source_path: Path,
        depth: int,
        stack: list[str],
        trace: MergeTrace | None = None,
    ) -> dict[str, Any]:
        if depth > self.max_depth:
            raise ResolutionError(
                f"Max inheritance depth ({self.max_depth}) exceeded. "
                f"Resolution stack: {' -> '.join(stack)}"
            )

        source_key = str(source_path.resolve())
        if source_key in stack:
            raise ResolutionError(
                f"Circular dependency detected: {' -> '.join(stack)} -> {source_key}"
            )

        new_stack = [*stack, source_key]

        # Separate inheritance directives from the identity's own fields
        own_data = dict(data)
        extends = own_data.pop("extends", None)
        mixin_paths = own_data.pop("mixins", [])
        overrides = own_data.pop("overrides", None)

        # Build conflict resolver from composition config
        comp_data = own_data.get("composition", {})
        conflict_config = comp_data.get("conflict_resolution", {})
        try:
            cr = ConflictResolution.model_validate(conflict_config)
        except Exception as exc:
            logger.warning(
                "Invalid conflict_resolution config in %s, using defaults: %s",
                source_path,
                exc,
            )
            cr = ConflictResolution()
        merger = ConflictResolver(cr)

        # Resolution order per spec: archetype → mixin1 → mixin2 → own fields → overrides
        # Each step layers on top, with later values winning.

        # Step 1: Start with archetype as base
        base: dict[str, Any] = {}
        if extends:
            archetype_path = self._find_file(extends, source_path)
            archetype_data = self._parser.parse_file(archetype_path)
            base = self._resolve(
                archetype_data,
                archetype_path,
                depth + 1,
                new_stack,
                trace=trace,
            )
            base.pop("archetype", None)

        # Step 2: Apply mixins in order (each layers on top)
        for mixin_ref in mixin_paths:
            mixin_path = self._find_file(mixin_ref, source_path)
            mixin_data = self._parser.parse_file(mixin_path)
            mixin_resolved = self._resolve(
                mixin_data,
                mixin_path,
                depth + 1,
                new_stack,
                trace=trace,
            )
            mixin_resolved.pop("mixin", None)
            base = merger.merge(
                base,
                mixin_resolved,
                trace=trace,
                source=f"mixin:{mixin_ref}",
            )

        # Step 3: Apply the identity's own fields (override inherited + mixin values)
        result = merger.merge(base, own_data, trace=trace, source="own") if base else own_data

        # Step 4: Apply explicit overrides block (highest priority)
        if overrides:
            result = merger.merge(result, overrides, trace=trace, source="override")

        return self._resolve_embedded_paths(result, source_path)

    def _resolve_embedded_paths(self, data: dict[str, Any], source_path: Path) -> dict[str, Any]:
        """Resolve nested path-like fields relative to the source YAML file.

        This keeps non-path strings unchanged and only rewrites values when a
        matching file or directory exists.
        """

        def walk(value: Any, *, key: str | None = None) -> Any:
            if isinstance(value, dict):
                return {k: walk(v, key=k) for k, v in value.items()}
            if isinstance(value, list):
                return [walk(item) for item in value]
            if isinstance(value, str) and key and self._looks_like_path_key(key):
                resolved = self._find_reference(value, source_path, allow_directories=True)
                return str(resolved.resolve()) if resolved else value
            return value

        return cast(dict[str, Any], walk(data))

    @staticmethod
    def _looks_like_path_key(key: str) -> bool:
        lowered = key.lower()
        return lowered == "path" or lowered == "file" or lowered.endswith(("_path", "_file"))

    def _find_file(self, ref: str, source_path: Path) -> Path:
        """Resolve a reference (extends/mixin path) to an actual file path."""
        candidate = self._find_reference(ref, source_path, allow_directories=False, yaml_only=True)
        if candidate is not None:
            return candidate

        searched = [str(c) for c in self._reference_candidates(ref, source_path, yaml_only=True)]
        raise ParseError(
            f"Cannot resolve reference '{ref}'. Searched:\n  " + "\n  ".join(searched),
            source=str(source_path),
        )

    def _find_reference(
        self,
        ref: str,
        source_path: Path,
        *,
        allow_directories: bool,
        yaml_only: bool = False,
    ) -> Path | None:
        self._validate_reference(ref, source_path)
        for candidate in self._reference_candidates(ref, source_path, yaml_only=yaml_only):
            if candidate.is_file() or (allow_directories and candidate.is_dir()):
                return candidate
        return None

    def _reference_candidates(self, ref: str, source_path: Path, *, yaml_only: bool) -> list[Path]:
        candidates: list[Path] = []

        base_dir = source_path.parent
        candidates.append(base_dir / ref)
        if yaml_only and not ref.endswith(".yaml") and not ref.endswith(".yml"):
            candidates.append(base_dir / f"{ref}.yaml")
            candidates.append(base_dir / f"{ref}.yml")

        for sp in self.search_paths:
            candidates.append(sp / ref)
            if yaml_only and not ref.endswith(".yaml") and not ref.endswith(".yml"):
                candidates.append(sp / f"{ref}.yaml")
                candidates.append(sp / f"{ref}.yml")

        return candidates

    def _validate_reference(self, ref: str, source_path: Path) -> None:
        ref_parts = Path(ref).parts
        if ".." in ref_parts or ref.startswith("/") or ref.startswith("\\"):
            raise ParseError(
                f"Invalid reference '{ref}': must be a relative path without '..' components",
                source=str(source_path),
            )
