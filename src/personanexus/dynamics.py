"""Dynamic & Stateful Personality Layer — mood/mode shifting engine.

Runtime flow (per response):
  1. Load user state from persistent storage
  2. Evaluate context (message + history) to detect triggers
  3. Determine active mood & mode
  4. Apply trait deltas/overrides to base traits
  5. Evaluate memory influence rules for permanent trait changes
  6. Recompile the final system prompt with adjusted traits
  7. Update memory with new interaction data
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from personanexus.compiler import compile_identity
from personanexus.memory import (
    MemoryBackendJSON,
    UserState,
    record_interaction,
)
from personanexus.types import (
    AgentIdentity,
    DynamicMode,
    DynamicMood,
    DynamicsConfig,
    DynamicTrigger,
    MemoryInfluenceRule,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context representation
# ---------------------------------------------------------------------------


@dataclass
class InteractionContext:
    """Snapshot of the current interaction context for trigger evaluation."""

    message: str = ""
    sentiment: float = 0.5
    interaction_count: int = 0
    user_known: bool = False
    trust_score: float = 0.0
    custom: dict[str, Any] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)


def context_from_state(
    state: UserState,
    message: str = "",
    sentiment: float = 0.5,
) -> InteractionContext:
    """Build an InteractionContext from a UserState and incoming message."""
    return InteractionContext(
        message=message,
        sentiment=sentiment,
        interaction_count=state.interaction_count,
        user_known=state.interaction_count > 0,
        trust_score=state.trust_score,
        custom=dict(state.custom),
        keywords=_extract_keywords(message),
    )


def _extract_keywords(text: str) -> list[str]:
    """Extract lowercase word tokens from text."""
    return re.findall(r"[a-zA-Z]+", text.lower())


# ---------------------------------------------------------------------------
# Trigger evaluation
# ---------------------------------------------------------------------------


def evaluate_trigger(trigger: DynamicTrigger, ctx: InteractionContext) -> bool:
    """Evaluate whether a single trigger fires given the current context."""
    t = trigger.type.lower()
    v = trigger.value

    if t == "sentiment_below":
        return ctx.sentiment < float(v)
    elif t == "sentiment_above":
        return ctx.sentiment > float(v)
    elif t == "keyword":
        return str(v).lower() in ctx.keywords
    elif t == "interaction_count_above":
        return ctx.interaction_count > int(v)
    elif t == "user_known":
        expected = str(v).lower() in ("true", "1", "yes")
        return ctx.user_known == expected
    elif t == "trust_above":
        return ctx.trust_score > float(v)
    elif t == "trust_below":
        return ctx.trust_score < float(v)
    elif t == "custom":
        # value format: "key > threshold" or "key == value"
        return _evaluate_custom_trigger(str(v), ctx.custom)
    else:
        logger.warning("Unknown trigger type: %s", t)
        return False


def _compare(op: str, a: float, b: float) -> bool:
    """Compare two floats using the given operator string."""
    ops = {
        ">": a > b,
        "<": a < b,
        ">=": a >= b,
        "<=": a <= b,
        "==": a == b,
        "!=": a != b,
    }
    return ops.get(op, False)


def _evaluate_custom_trigger(expr: str, custom: dict[str, Any]) -> bool:
    """Evaluate a simple custom trigger expression like 'positive_interactions > 10'."""
    for op in (">=", "<=", "!=", "==", ">", "<"):
        if op in expr:
            parts = expr.split(op, 1)
            if len(parts) == 2:
                key = parts[0].strip()
                threshold = parts[1].strip()
                actual = custom.get(key, 0)
                try:
                    threshold_val = float(threshold)
                    actual_val = float(actual)
                except (ValueError, TypeError):
                    return str(actual) == threshold if op == "==" else str(actual) != threshold
                return _compare(op, actual_val, threshold_val)
            break
    return False


def evaluate_triggers(triggers: list[DynamicTrigger], ctx: InteractionContext) -> bool:
    """Return True if ANY trigger in the list fires (OR logic)."""
    return any(evaluate_trigger(t, ctx) for t in triggers)


# ---------------------------------------------------------------------------
# Mood & Mode resolution
# ---------------------------------------------------------------------------


def resolve_mood(
    dynamics: DynamicsConfig,
    ctx: InteractionContext,
    current_mood: str,
) -> str:
    """Determine the active mood based on triggers. Returns mood name."""
    for mood in dynamics.moods:
        if mood.triggers and evaluate_triggers(mood.triggers, ctx):
            return mood.name
    return current_mood


def resolve_mode(
    dynamics: DynamicsConfig,
    ctx: InteractionContext,
    current_mode: str,
) -> str:
    """Determine the active mode based on triggers. Returns mode name."""
    for mode in dynamics.modes:
        if mode.triggers and evaluate_triggers(mode.triggers, ctx):
            return mode.name
    return current_mode


def get_mood_by_name(dynamics: DynamicsConfig, name: str) -> DynamicMood | None:
    """Look up a mood by name."""
    for mood in dynamics.moods:
        if mood.name == name:
            return mood
    return None


def get_mode_by_name(dynamics: DynamicsConfig, name: str) -> DynamicMode | None:
    """Look up a mode by name."""
    for mode in dynamics.modes:
        if mode.name == name:
            return mode
    return None


# ---------------------------------------------------------------------------
# Trait adjustment
# ---------------------------------------------------------------------------


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))


def apply_dynamics_to_traits(
    base_traits: dict[str, float],
    dynamics: DynamicsConfig,
    mood_name: str,
    mode_name: str,
) -> dict[str, float]:
    """Apply mood deltas and mode overrides to base traits.

    Order of operations:
    1. Start with base traits
    2. Apply mode overrides (absolute values replace base)
    3. Apply mood deltas (additive on top)
    4. Clamp all values to configured bounds

    Args:
        base_traits: Dict of trait_name → value (0-1 scale).
        dynamics: The DynamicsConfig from the identity.
        mood_name: Active mood name.
        mode_name: Active mode name.

    Returns:
        New dict of adjusted traits.
    """
    result = dict(base_traits)
    lo = dynamics.trait_clamp_min
    hi = dynamics.trait_clamp_max

    # Step 1: Apply mode overrides (absolute)
    mode = get_mode_by_name(dynamics, mode_name)
    if mode:
        for trait_name, value in mode.trait_overrides.items():
            result[trait_name] = clamp(value, lo, hi)

    # Step 2: Apply mood deltas (additive)
    mood = get_mood_by_name(dynamics, mood_name)
    if mood:
        for trait_name, delta in mood.trait_deltas.items():
            current = result.get(trait_name, 0.5)
            result[trait_name] = clamp(current + delta, lo, hi)

    return result


# ---------------------------------------------------------------------------
# Memory influence evaluation
# ---------------------------------------------------------------------------


def _parse_condition(condition: str) -> tuple[str, str, float] | None:
    """Parse a condition string like 'positive_interactions > 10' or 'trust_score > 0.7'."""
    for op in (">=", "<=", "!=", "==", ">", "<"):
        if op in condition:
            parts = condition.split(op, 1)
            if len(parts) == 2:
                try:
                    return parts[0].strip(), op, float(parts[1].strip())
                except ValueError:
                    return None
            break
    return None


def _check_condition(condition: str, state: UserState) -> bool:
    """Evaluate a memory influence condition against user state."""
    parsed = _parse_condition(condition)
    if not parsed:
        return False
    key, op, threshold = parsed

    # Resolve the value from known state fields or custom dict
    known_fields = {
        "interaction_count": state.interaction_count,
        "avg_sentiment": state.avg_sentiment,
        "trust_score": state.trust_score,
    }
    actual = known_fields.get(key)
    if actual is None:
        actual = state.custom.get(key, 0)
    try:
        actual = float(actual)
    except (ValueError, TypeError):
        return False

    return _compare(op, actual, threshold)


def _parse_effect(effect: str) -> dict[str, Any]:
    """Parse an effect string.

    Supported formats:
      - "warmth +0.10 permanent" → {"type": "trait_delta", "trait": "warmth", "delta": 0.10}
      - "warmth -0.05 permanent" → {"type": "trait_delta", "trait": "warmth", "delta": -0.05}
      - "unlock_mode familiar"   → {"type": "unlock_mode", "mode": "familiar"}
    """
    parts = effect.strip().split()
    if len(parts) >= 2 and parts[0] == "unlock_mode":
        return {"type": "unlock_mode", "mode": parts[1]}

    if len(parts) >= 2:
        trait = parts[0]
        try:
            delta = float(parts[1])
            return {"type": "trait_delta", "trait": trait, "delta": delta}
        except ValueError:
            pass

    return {"type": "unknown", "raw": effect}


def evaluate_memory_influences(
    rules: list[MemoryInfluenceRule],
    state: UserState,
    base_traits: dict[str, float],
    lo: float = 0.0,
    hi: float = 1.0,
    valid_modes: set[str] | None = None,
) -> tuple[dict[str, float], list[str]]:
    """Evaluate memory influence rules and apply permanent trait changes.

    Args:
        rules: The memory_influences from DynamicsConfig.
        state: Current user state.
        base_traits: The current base traits (may be modified in place conceptually).
        lo: Minimum trait clamp.
        hi: Maximum trait clamp.
        valid_modes: Set of defined mode names for unlock_mode validation.

    Returns:
        Tuple of (adjusted_traits, list of newly applied influence descriptions).
    """
    result = dict(base_traits)
    newly_applied: list[str] = []

    for rule in rules:
        # Skip already-applied rules (idempotency for permanent effects)
        rule_key = f"{rule.condition} -> {rule.effect}"
        if rule_key in state.applied_influences:
            continue

        if _check_condition(rule.condition, state):
            effect = _parse_effect(rule.effect)
            if effect["type"] == "trait_delta":
                trait = effect["trait"]
                delta = effect["delta"]
                current = result.get(trait, 0.5)
                result[trait] = clamp(current + delta, lo, hi)
                state.applied_influences.append(rule_key)
                newly_applied.append(rule_key)
                logger.info("Memory influence applied: %s", rule_key)
            elif effect["type"] == "unlock_mode":
                mode_name = effect["mode"]
                if valid_modes is not None and mode_name not in valid_modes:
                    logger.warning(
                        "unlock_mode target '%s' is not a defined mode — skipping",
                        mode_name,
                    )
                    continue
                state.current_mode = mode_name
                state.applied_influences.append(rule_key)
                newly_applied.append(rule_key)
                logger.info("Mode unlocked via memory influence: %s", mode_name)

    return result, newly_applied


# ---------------------------------------------------------------------------
# Full runtime pipeline
# ---------------------------------------------------------------------------


@dataclass
class DynamicsResult:
    """Result of running the dynamics pipeline for one interaction."""

    adjusted_traits: dict[str, float]
    active_mood: str
    active_mode: str
    tone_override: str | None
    influences_applied: list[str]
    compiled_prompt: str | None = None


def run_dynamics_pipeline(
    identity: AgentIdentity,
    state: UserState,
    message: str = "",
    sentiment: float = 0.5,
    compile_prompt: bool = True,
    compile_target: str = "text",
) -> DynamicsResult:
    """Execute the full dynamics pipeline for a single interaction.

    Steps:
    1. Build interaction context from user state + message
    2. Resolve active mood and mode from triggers
    3. Get base traits from identity
    4. Apply mode overrides + mood deltas
    5. Evaluate memory influence rules
    6. Optionally recompile the system prompt with adjusted traits
    7. Update user state

    Args:
        identity: The loaded AgentIdentity (must have dynamics config).
        state: Current persistent user state.
        message: The incoming user message.
        sentiment: Estimated sentiment of the message (0-1).
        compile_prompt: Whether to recompile the system prompt.
        compile_target: Compilation target format.

    Returns:
        DynamicsResult with adjusted traits, active mood/mode, and optional prompt.
    """
    dynamics = identity.dynamics
    if dynamics is None:
        # No dynamics configured — return base traits unchanged
        base = identity.personality.traits.defined_traits()
        return DynamicsResult(
            adjusted_traits=base,
            active_mood="neutral",
            active_mode="default",
            tone_override=None,
            influences_applied=[],
        )

    # 1. Build context
    ctx = context_from_state(state, message, sentiment)

    # 2. Resolve mood & mode
    active_mood = resolve_mood(dynamics, ctx, state.current_mood)
    active_mode = resolve_mode(dynamics, ctx, state.current_mode)

    # 3. Get base traits
    base_traits = identity.personality.traits.defined_traits()

    # 4. Apply mood deltas + mode overrides
    adjusted = apply_dynamics_to_traits(base_traits, dynamics, active_mood, active_mode)

    # 5. Evaluate memory influences
    valid_modes = {m.name for m in dynamics.modes}
    adjusted, newly_applied = evaluate_memory_influences(
        dynamics.memory_influences,
        state,
        adjusted,
        dynamics.trait_clamp_min,
        dynamics.trait_clamp_max,
        valid_modes=valid_modes,
    )

    # Determine tone override (mood takes precedence over mode)
    tone_override = None
    mood_obj = get_mood_by_name(dynamics, active_mood)
    mode_obj = get_mode_by_name(dynamics, active_mode)
    if mood_obj and mood_obj.tone_override:
        tone_override = mood_obj.tone_override
    elif mode_obj and mode_obj.tone_override:
        tone_override = mode_obj.tone_override

    # 6. Update state
    state.current_mood = active_mood
    state.current_mode = active_mode

    # 7. Optionally recompile prompt with adjusted traits
    compiled = None
    if compile_prompt:
        compiled = compile_with_adjusted_traits(identity, adjusted, tone_override, compile_target)

    return DynamicsResult(
        adjusted_traits=adjusted,
        active_mood=active_mood,
        active_mode=active_mode,
        tone_override=tone_override,
        influences_applied=newly_applied,
        compiled_prompt=compiled,
    )


def compile_with_adjusted_traits(
    identity: AgentIdentity,
    adjusted_traits: dict[str, float],
    tone_override: str | None = None,
    target: str = "text",
) -> str:
    """Create a modified copy of the identity with adjusted traits, then compile.

    This creates a shallow copy with overridden personality traits so the
    original identity object is not mutated.
    """
    # Build a modified identity dict, override traits
    identity_dict = identity.model_dump()
    for trait_name, value in adjusted_traits.items():
        identity_dict["personality"]["traits"][trait_name] = value

    if tone_override:
        identity_dict["communication"]["tone"]["default"] = tone_override

    # Reconstruct and compile
    modified = AgentIdentity.model_validate(identity_dict)
    result = compile_identity(modified, target=target)
    if isinstance(result, dict):
        return str(result)
    return result


# ---------------------------------------------------------------------------
# High-level session helper
# ---------------------------------------------------------------------------


class DynamicSession:
    """Manages a multi-turn session with dynamics for a single user + persona.

    Caches the compiled prompt and only recompiles when the active mood, mode,
    or adjusted traits actually change between interactions.

    Usage::

        session = DynamicSession(identity, user_id="user_123")
        for message in messages:
            result = session.process(message, sentiment=0.6)
            print(result.compiled_prompt)
        session.save()
    """

    def __init__(
        self,
        identity: AgentIdentity,
        user_id: str = "default",
        memory_dir: str | None = None,
        auto_save: bool = False,
    ) -> None:
        self.identity = identity
        self.user_id = user_id
        self.backend = MemoryBackendJSON(memory_dir)
        self.state = self.backend.load(user_id)
        self.auto_save = auto_save
        self.history: list[DynamicsResult] = []
        # Prompt cache — avoids recompilation when dynamics state is unchanged
        self._cached_prompt: str | None = None
        self._cached_mood: str | None = None
        self._cached_mode: str | None = None
        self._cached_traits: dict[str, float] | None = None
        self._cached_tone_override: str | None = None

    def process(
        self,
        message: str = "",
        sentiment: float = 0.5,
        positive: bool | None = None,
        trust_delta: float = 0.0,
        compile_prompt: bool = True,
    ) -> DynamicsResult:
        """Process one interaction through the dynamics pipeline.

        Args:
            message: Incoming user message.
            sentiment: Estimated sentiment (0=negative, 1=positive).
            positive: Whether this was a positive interaction (for custom counter).
            trust_delta: Trust adjustment for this interaction.
            compile_prompt: Whether to recompile the system prompt.

        Returns:
            DynamicsResult with adjusted traits and optional compiled prompt.
        """
        result = run_dynamics_pipeline(
            self.identity,
            self.state,
            message=message,
            sentiment=sentiment,
            compile_prompt=False,  # We handle compilation with caching below
        )

        # Only recompile if dynamics state actually changed
        if compile_prompt:
            needs_recompile = (
                self._cached_prompt is None
                or result.active_mood != self._cached_mood
                or result.active_mode != self._cached_mode
                or result.adjusted_traits != self._cached_traits
                or result.tone_override != self._cached_tone_override
            )

            if needs_recompile:
                compiled = compile_with_adjusted_traits(
                    self.identity,
                    result.adjusted_traits,
                    result.tone_override,
                )
                self._cached_prompt = compiled
                self._cached_mood = result.active_mood
                self._cached_mode = result.active_mode
                self._cached_traits = dict(result.adjusted_traits)
                self._cached_tone_override = result.tone_override
                logger.debug("Prompt recompiled (dynamics state changed).")
            else:
                logger.debug("Prompt cache hit — skipping recompilation.")

            result.compiled_prompt = self._cached_prompt

        # Record the interaction in memory
        record_interaction(
            self.state,
            sentiment=sentiment,
            trust_delta=trust_delta,
            positive=positive,
        )

        self.history.append(result)

        if self.auto_save:
            self.save()

        return result

    def invalidate_cache(self) -> None:
        """Force the next process() call to recompile the prompt."""
        self._cached_prompt = None

    def save(self) -> None:
        """Persist user state to disk."""
        self.backend.save(self.state)

    def reset(self) -> None:
        """Reset user state to defaults."""
        self.state = UserState(user_id=self.user_id)
        self.history.clear()
        self._cached_prompt = None
        self._cached_mood = None
        self._cached_mode = None
        self._cached_traits = None
        self._cached_tone_override = None
