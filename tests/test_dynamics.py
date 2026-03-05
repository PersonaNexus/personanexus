"""Tests for personanexus.dynamics — mood/mode shifting engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from personanexus.dynamics import (
    DynamicSession,
    DynamicsResult,
    InteractionContext,
    apply_dynamics_to_traits,
    clamp,
    compile_with_adjusted_traits,
    context_from_state,
    evaluate_memory_influences,
    evaluate_trigger,
    evaluate_triggers,
    get_mood_by_name,
    get_mode_by_name,
    resolve_mood,
    resolve_mode,
    run_dynamics_pipeline,
)
from personanexus.memory import UserState
from personanexus.types import (
    AgentIdentity,
    DynamicMood,
    DynamicMode,
    DynamicsConfig,
    DynamicTrigger,
    MemoryInfluenceRule,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_dynamics() -> DynamicsConfig:
    return DynamicsConfig(
        default_mood="neutral",
        default_mode="stranger",
        moods=[
            DynamicMood(
                name="neutral",
                trait_deltas={},
            ),
            DynamicMood(
                name="stressed",
                trait_deltas={"warmth": -0.15, "rigor": 0.20},
                tone_override="focused-terse",
                triggers=[
                    DynamicTrigger(type="keyword", value="urgent"),
                    DynamicTrigger(type="sentiment_below", value=0.3),
                ],
            ),
            DynamicMood(
                name="enthusiastic",
                trait_deltas={"warmth": 0.15, "humor": 0.15},
                tone_override="energetic",
                triggers=[
                    DynamicTrigger(type="sentiment_above", value=0.8),
                ],
            ),
        ],
        modes=[
            DynamicMode(
                name="stranger",
                trait_overrides={"warmth": 0.40, "humor": 0.15},
                tone_override="formal",
                triggers=[DynamicTrigger(type="user_known", value=False)],
            ),
            DynamicMode(
                name="familiar",
                trait_overrides={"warmth": 0.70, "humor": 0.45},
                triggers=[
                    DynamicTrigger(type="interaction_count_above", value=5),
                    DynamicTrigger(type="trust_above", value=0.5),
                ],
            ),
        ],
        memory_influences=[
            MemoryInfluenceRule(
                condition="positive_interactions > 10",
                effect="warmth +0.10 permanent",
            ),
            MemoryInfluenceRule(
                condition="trust_score > 0.7",
                effect="unlock_mode familiar",
            ),
        ],
    )


def _make_minimal_identity(dynamics: DynamicsConfig | None = None) -> AgentIdentity:
    """Build a minimal valid identity with optional dynamics."""
    return AgentIdentity.model_validate(
        {
            "schema_version": "1.0",
            "metadata": {
                "id": "agt_test_001",
                "name": "TestBot",
                "version": "1.0.0",
                "description": "Test identity",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "active",
            },
            "role": {
                "title": "Tester",
                "purpose": "Testing dynamics",
                "scope": {"primary": ["testing"]},
            },
            "personality": {
                "traits": {
                    "warmth": 0.55,
                    "rigor": 0.85,
                    "humor": 0.30,
                    "empathy": 0.65,
                },
            },
            "communication": {"tone": {"default": "neutral"}},
            "principles": [
                {"id": "p1", "priority": 1, "statement": "Be helpful"},
            ],
            "guardrails": {
                "hard": [
                    {
                        "id": "g1",
                        "rule": "No harmful content",
                        "enforcement": "output_filter",
                        "severity": "critical",
                    }
                ]
            },
            "dynamics": dynamics.model_dump() if dynamics else None,
        }
    )


# ---------------------------------------------------------------------------
# Trigger evaluation tests
# ---------------------------------------------------------------------------


class TestTriggerEvaluation:
    def test_sentiment_below(self):
        trigger = DynamicTrigger(type="sentiment_below", value=0.3)
        ctx = InteractionContext(sentiment=0.2)
        assert evaluate_trigger(trigger, ctx) is True
        ctx.sentiment = 0.5
        assert evaluate_trigger(trigger, ctx) is False

    def test_sentiment_above(self):
        trigger = DynamicTrigger(type="sentiment_above", value=0.8)
        ctx = InteractionContext(sentiment=0.9)
        assert evaluate_trigger(trigger, ctx) is True

    def test_keyword(self):
        trigger = DynamicTrigger(type="keyword", value="urgent")
        ctx = InteractionContext(message="This is urgent!", keywords=["this", "is", "urgent"])
        assert evaluate_trigger(trigger, ctx) is True
        ctx.keywords = ["not", "here"]
        assert evaluate_trigger(trigger, ctx) is False

    def test_interaction_count_above(self):
        trigger = DynamicTrigger(type="interaction_count_above", value=5)
        ctx = InteractionContext(interaction_count=10)
        assert evaluate_trigger(trigger, ctx) is True
        ctx.interaction_count = 3
        assert evaluate_trigger(trigger, ctx) is False

    def test_user_known_true(self):
        trigger = DynamicTrigger(type="user_known", value=True)
        ctx = InteractionContext(user_known=True)
        assert evaluate_trigger(trigger, ctx) is True
        ctx.user_known = False
        assert evaluate_trigger(trigger, ctx) is False

    def test_user_known_false(self):
        trigger = DynamicTrigger(type="user_known", value=False)
        ctx = InteractionContext(user_known=False)
        assert evaluate_trigger(trigger, ctx) is True

    def test_trust_above(self):
        trigger = DynamicTrigger(type="trust_above", value=0.5)
        ctx = InteractionContext(trust_score=0.8)
        assert evaluate_trigger(trigger, ctx) is True

    def test_trust_below(self):
        trigger = DynamicTrigger(type="trust_below", value=0.3)
        ctx = InteractionContext(trust_score=0.1)
        assert evaluate_trigger(trigger, ctx) is True

    def test_unknown_trigger_type(self):
        trigger = DynamicTrigger(type="nonexistent", value="x")
        ctx = InteractionContext()
        assert evaluate_trigger(trigger, ctx) is False

    def test_evaluate_triggers_or_logic(self):
        triggers = [
            DynamicTrigger(type="keyword", value="urgent"),
            DynamicTrigger(type="sentiment_below", value=0.3),
        ]
        ctx = InteractionContext(sentiment=0.5, keywords=["urgent"])
        assert evaluate_triggers(triggers, ctx) is True

        ctx2 = InteractionContext(sentiment=0.5, keywords=["hello"])
        assert evaluate_triggers(triggers, ctx2) is False


# ---------------------------------------------------------------------------
# Mood & Mode resolution
# ---------------------------------------------------------------------------


class TestMoodModeResolution:
    def test_resolve_mood_triggered(self):
        dynamics = _make_dynamics()
        ctx = InteractionContext(keywords=["urgent"], sentiment=0.5)
        mood = resolve_mood(dynamics, ctx, "neutral")
        assert mood == "stressed"

    def test_resolve_mood_default(self):
        dynamics = _make_dynamics()
        ctx = InteractionContext(keywords=["hello"], sentiment=0.5)
        mood = resolve_mood(dynamics, ctx, "neutral")
        assert mood == "neutral"

    def test_resolve_mood_by_sentiment(self):
        dynamics = _make_dynamics()
        ctx = InteractionContext(sentiment=0.9, keywords=[])
        mood = resolve_mood(dynamics, ctx, "neutral")
        assert mood == "enthusiastic"

    def test_resolve_mode_stranger(self):
        dynamics = _make_dynamics()
        ctx = InteractionContext(user_known=False)
        mode = resolve_mode(dynamics, ctx, "stranger")
        assert mode == "stranger"

    def test_resolve_mode_familiar(self):
        dynamics = _make_dynamics()
        ctx = InteractionContext(
            interaction_count=10,
            trust_score=0.6,
            user_known=True,
        )
        mode = resolve_mode(dynamics, ctx, "stranger")
        assert mode == "familiar"

    def test_get_mood_by_name(self):
        dynamics = _make_dynamics()
        assert get_mood_by_name(dynamics, "stressed") is not None
        assert get_mood_by_name(dynamics, "nonexistent") is None

    def test_get_mode_by_name(self):
        dynamics = _make_dynamics()
        assert get_mode_by_name(dynamics, "stranger") is not None
        assert get_mode_by_name(dynamics, "nonexistent") is None


# ---------------------------------------------------------------------------
# Trait adjustment
# ---------------------------------------------------------------------------


class TestTraitAdjustment:
    def test_clamp(self):
        assert clamp(1.5) == 1.0
        assert clamp(-0.5) == 0.0
        assert clamp(0.5) == 0.5

    def test_apply_mode_overrides(self):
        dynamics = _make_dynamics()
        base = {"warmth": 0.55, "humor": 0.30, "rigor": 0.85}
        result = apply_dynamics_to_traits(base, dynamics, "neutral", "stranger")
        assert result["warmth"] == 0.40  # overridden by stranger mode
        assert result["humor"] == 0.15  # overridden by stranger mode
        assert result["rigor"] == 0.85  # unchanged

    def test_apply_mood_deltas(self):
        dynamics = _make_dynamics()
        base = {"warmth": 0.55, "rigor": 0.85}
        result = apply_dynamics_to_traits(base, dynamics, "stressed", "neutral")
        # no mode called "neutral" → only mood applied
        assert result["warmth"] == pytest.approx(0.40)  # 0.55 - 0.15
        assert result["rigor"] == pytest.approx(1.0)  # 0.85 + 0.20 clamped

    def test_apply_both_mode_and_mood(self):
        dynamics = _make_dynamics()
        base = {"warmth": 0.55, "humor": 0.30, "rigor": 0.85}
        result = apply_dynamics_to_traits(base, dynamics, "stressed", "stranger")
        # Mode first: warmth = 0.40, humor = 0.15
        # Then mood: warmth = 0.40 - 0.15 = 0.25, rigor = 0.85 + 0.20 = 1.0
        assert result["warmth"] == pytest.approx(0.25)
        assert result["humor"] == 0.15  # mode overrode, mood didn't touch
        assert result["rigor"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Memory influences
# ---------------------------------------------------------------------------


class TestMemoryInfluences:
    def test_trait_delta_applied(self):
        rules = [
            MemoryInfluenceRule(
                condition="positive_interactions > 10",
                effect="warmth +0.10 permanent",
            )
        ]
        state = UserState(user_id="u1", custom={"positive_interactions": 15})
        traits = {"warmth": 0.5}
        result, applied = evaluate_memory_influences(rules, state, traits)
        assert result["warmth"] == pytest.approx(0.6)
        assert len(applied) == 1

    def test_idempotent(self):
        rules = [
            MemoryInfluenceRule(
                condition="positive_interactions > 10",
                effect="warmth +0.10 permanent",
            )
        ]
        state = UserState(user_id="u1", custom={"positive_interactions": 15})
        state.applied_influences.append("positive_interactions > 10 -> warmth +0.10 permanent")
        traits = {"warmth": 0.5}
        result, applied = evaluate_memory_influences(rules, state, traits)
        assert result["warmth"] == 0.5  # not applied again
        assert len(applied) == 0

    def test_unlock_mode(self):
        rules = [
            MemoryInfluenceRule(
                condition="trust_score > 0.7",
                effect="unlock_mode familiar",
            )
        ]
        state = UserState(user_id="u1", trust_score=0.8)
        traits = {"warmth": 0.5}
        _, applied = evaluate_memory_influences(rules, state, traits)
        assert state.current_mode == "familiar"
        assert len(applied) == 1

    def test_condition_not_met(self):
        rules = [
            MemoryInfluenceRule(
                condition="positive_interactions > 10",
                effect="warmth +0.10 permanent",
            )
        ]
        state = UserState(user_id="u1", custom={"positive_interactions": 3})
        traits = {"warmth": 0.5}
        result, applied = evaluate_memory_influences(rules, state, traits)
        assert result["warmth"] == 0.5
        assert len(applied) == 0


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


class TestRunDynamicsPipeline:
    def test_no_dynamics(self):
        identity = _make_minimal_identity(dynamics=None)
        state = UserState(user_id="u1")
        result = run_dynamics_pipeline(identity, state, compile_prompt=False)
        assert result.active_mood == "neutral"
        assert result.active_mode == "default"

    def test_with_dynamics(self):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        state = UserState(user_id="u1")
        result = run_dynamics_pipeline(
            identity, state, message="This is urgent!", sentiment=0.2, compile_prompt=False
        )
        assert result.active_mood == "stressed"
        assert result.active_mode == "stranger"  # new user
        assert result.adjusted_traits["warmth"] < 0.55  # reduced

    def test_pipeline_compiles_prompt(self):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        state = UserState(user_id="u1")
        result = run_dynamics_pipeline(
            identity, state, message="hello", sentiment=0.5, compile_prompt=True
        )
        assert result.compiled_prompt is not None
        assert len(result.compiled_prompt) > 0


# ---------------------------------------------------------------------------
# DynamicSession
# ---------------------------------------------------------------------------


class TestDynamicSession:
    def test_session_process(self, tmp_path: Path):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        session = DynamicSession(
            identity, user_id="test_user", memory_dir=str(tmp_path / "mem")
        )
        result = session.process("hello", sentiment=0.5, compile_prompt=False)
        assert result.active_mood is not None
        assert session.state.interaction_count == 1

    def test_session_multi_turn(self, tmp_path: Path):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        session = DynamicSession(
            identity, user_id="multi", memory_dir=str(tmp_path / "mem")
        )
        for i in range(5):
            session.process("message", sentiment=0.6, positive=True, compile_prompt=False)
        assert session.state.interaction_count == 5
        assert session.state.custom.get("positive_interactions", 0) == 5

    def test_session_save_and_restore(self, tmp_path: Path):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        mem_dir = str(tmp_path / "mem")

        session1 = DynamicSession(identity, user_id="persist", memory_dir=mem_dir)
        for _ in range(3):
            session1.process("hi", sentiment=0.7, positive=True, compile_prompt=False)
        session1.save()

        session2 = DynamicSession(identity, user_id="persist", memory_dir=mem_dir)
        assert session2.state.interaction_count == 3

    def test_session_reset(self, tmp_path: Path):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        session = DynamicSession(
            identity, user_id="reset", memory_dir=str(tmp_path / "mem")
        )
        session.process("hi", sentiment=0.5, compile_prompt=False)
        session.reset()
        assert session.state.interaction_count == 0
        assert session.history == []


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------


class TestContextFromState:
    def test_basic(self):
        state = UserState(user_id="u1", interaction_count=5, trust_score=0.6)
        ctx = context_from_state(state, "hello world", 0.7)
        assert ctx.message == "hello world"
        assert ctx.sentiment == 0.7
        assert ctx.interaction_count == 5
        assert ctx.user_known is True
        assert ctx.trust_score == 0.6
        assert "hello" in ctx.keywords

    def test_new_user_not_known(self):
        state = UserState(user_id="new")
        ctx = context_from_state(state, "hi")
        assert ctx.user_known is False


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class TestDynamicsConfig:
    def test_identity_with_dynamics(self):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        assert identity.dynamics is not None
        assert len(identity.dynamics.moods) == 3
        assert len(identity.dynamics.modes) == 2
        assert len(identity.dynamics.memory_influences) == 2

    def test_identity_without_dynamics(self):
        identity = _make_minimal_identity(None)
        assert identity.dynamics is None
