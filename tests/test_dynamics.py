"""Tests for personanexus.dynamics — mood/mode shifting engine."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from personanexus.dynamics import (
    DynamicSession,
    InteractionContext,
    apply_dynamics_to_traits,
    clamp,
    context_from_state,
    evaluate_memory_influences,
    evaluate_trigger,
    evaluate_triggers,
    get_mode_by_name,
    get_mood_by_name,
    resolve_mode,
    resolve_mood,
    run_dynamics_pipeline,
)
from personanexus.memory import UserState
from personanexus.types import (
    AgentIdentity,
    DynamicMode,
    DynamicMood,
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

    def test_unknown_trigger_type_rejected_by_schema(self):
        """Unknown trigger types are now rejected at schema validation time."""
        with pytest.raises(ValidationError):  # pydantic ValidationError
            DynamicTrigger(type="nonexistent", value="x")

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
        session = DynamicSession(identity, user_id="test_user", memory_dir=str(tmp_path / "mem"))
        result = session.process("hello", sentiment=0.5, compile_prompt=False)
        assert result.active_mood is not None
        assert session.state.interaction_count == 1

    def test_session_multi_turn(self, tmp_path: Path):
        dynamics = _make_dynamics()
        identity = _make_minimal_identity(dynamics)
        session = DynamicSession(identity, user_id="multi", memory_dir=str(tmp_path / "mem"))
        for _i in range(5):
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
        session = DynamicSession(identity, user_id="reset", memory_dir=str(tmp_path / "mem"))
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


# ---------------------------------------------------------------------------
# Security hardening tests
# ---------------------------------------------------------------------------


class TestDynamicsSecurityHardening:
    """Tests for adversarial inputs and schema-level validation."""

    # -- Trigger type whitelist --

    def test_invalid_trigger_type_rejected(self):
        """Arbitrary strings are rejected as trigger types."""
        with pytest.raises(ValidationError):
            DynamicTrigger(type="sql_injection; DROP TABLE;", value="x")

    def test_valid_trigger_types_accepted(self):
        """All documented trigger types are accepted."""
        for ttype in [
            "sentiment_below",
            "sentiment_above",
            "keyword",
            "interaction_count_above",
            "user_known",
            "trust_above",
            "trust_below",
            "custom",
        ]:
            trigger = DynamicTrigger(type=ttype, value=0.5)
            assert trigger.type == ttype

    # -- Trait delta bounds --

    def test_trait_delta_too_large_rejected(self):
        with pytest.raises(ValidationError):
            DynamicMood(name="bad", trait_deltas={"warmth": 999.0})

    def test_trait_delta_too_negative_rejected(self):
        with pytest.raises(ValidationError):
            DynamicMood(name="bad", trait_deltas={"warmth": -5.0})

    def test_trait_delta_boundary_accepted(self):
        mood = DynamicMood(name="edge", trait_deltas={"warmth": -1.0, "rigor": 1.0})
        assert mood.trait_deltas["warmth"] == -1.0
        assert mood.trait_deltas["rigor"] == 1.0

    # -- Trait override bounds --

    def test_trait_override_too_large_rejected(self):
        with pytest.raises(ValidationError):
            DynamicMode(name="bad", trait_overrides={"warmth": 1.5})

    def test_trait_override_negative_rejected(self):
        with pytest.raises(ValidationError):
            DynamicMode(name="bad", trait_overrides={"warmth": -0.1})

    # -- Max length constraints --

    def test_mood_name_max_length(self):
        with pytest.raises(ValidationError):
            DynamicMood(name="x" * 101)

    def test_mode_name_max_length(self):
        with pytest.raises(ValidationError):
            DynamicMode(name="x" * 101)

    def test_tone_override_max_length(self):
        with pytest.raises(ValidationError):
            DynamicMood(name="ok", tone_override="x" * 501)

    def test_condition_max_length(self):
        with pytest.raises(ValidationError):
            MemoryInfluenceRule(condition="x" * 201, effect="warmth +0.1")

    def test_effect_max_length(self):
        with pytest.raises(ValidationError):
            MemoryInfluenceRule(condition="x > 1", effect="x" * 201)

    # -- Default mood/mode validation --

    def test_default_mood_must_exist(self):
        with pytest.raises(ValidationError, match="default_mood"):
            DynamicsConfig(
                default_mood="nonexistent",
                moods=[DynamicMood(name="neutral")],
            )

    def test_default_mode_must_exist(self):
        with pytest.raises(ValidationError, match="default_mode"):
            DynamicsConfig(
                default_mode="nonexistent",
                modes=[DynamicMode(name="stranger")],
            )

    def test_empty_moods_skips_default_check(self):
        """When moods list is empty, default_mood is not validated."""
        config = DynamicsConfig(moods=[], modes=[])
        assert config.default_mood == "neutral"

    def test_clamp_min_must_be_less_than_max(self):
        with pytest.raises(ValidationError, match="trait_clamp_min"):
            DynamicsConfig(trait_clamp_min=0.8, trait_clamp_max=0.2)

    # -- unlock_mode validation in engine --

    def test_unlock_mode_invalid_target_skipped(self):
        """unlock_mode to undefined mode is skipped when valid_modes provided."""
        rules = [
            MemoryInfluenceRule(
                condition="trust_score > 0.5",
                effect="unlock_mode nonexistent_mode",
            )
        ]
        state = UserState(user_id="u1", trust_score=0.8)
        traits = {"warmth": 0.5}
        valid_modes = {"stranger", "familiar"}
        result, applied = evaluate_memory_influences(rules, state, traits, valid_modes=valid_modes)
        assert state.current_mode != "nonexistent_mode"
        assert len(applied) == 0

    def test_unlock_mode_valid_target_works(self):
        """unlock_mode to a defined mode succeeds when valid_modes provided."""
        rules = [
            MemoryInfluenceRule(
                condition="trust_score > 0.5",
                effect="unlock_mode familiar",
            )
        ]
        state = UserState(user_id="u1", trust_score=0.8)
        traits = {"warmth": 0.5}
        valid_modes = {"stranger", "familiar"}
        _, applied = evaluate_memory_influences(rules, state, traits, valid_modes=valid_modes)
        assert state.current_mode == "familiar"
        assert len(applied) == 1

    # -- Malformed conditions/effects handled safely --

    def test_malformed_condition_returns_false(self):
        """Malformed SQL-like conditions don't crash, just don't fire."""
        rules = [
            MemoryInfluenceRule(
                condition="'; DROP TABLE;--",
                effect="warmth +0.10",
            )
        ]
        state = UserState(user_id="u1")
        traits = {"warmth": 0.5}
        result, applied = evaluate_memory_influences(rules, state, traits)
        assert result["warmth"] == 0.5
        assert len(applied) == 0

    def test_malformed_effect_ignored(self):
        """Unrecognized effect format is silently ignored."""
        rules = [
            MemoryInfluenceRule(
                condition="interaction_count > 0",
                effect="execute_code os.system('rm -rf /')",
            )
        ]
        state = UserState(user_id="u1", interaction_count=5)
        traits = {"warmth": 0.5}
        result, applied = evaluate_memory_influences(rules, state, traits)
        assert result["warmth"] == 0.5
        assert len(applied) == 0

    # -- Runtime clamping always enforced --

    def test_extreme_deltas_clamped_at_runtime(self):
        """Even at boundary delta values, runtime clamping holds."""
        dynamics = DynamicsConfig(
            default_mood="extreme",
            moods=[
                DynamicMood(
                    name="extreme",
                    trait_deltas={"warmth": -1.0, "rigor": 1.0},
                ),
            ],
        )
        base = {"warmth": 0.3, "rigor": 0.8}
        result = apply_dynamics_to_traits(base, dynamics, "extreme", "nonexistent")
        assert result["warmth"] == 0.0  # clamped at 0
        assert result["rigor"] == 1.0  # clamped at 1


# ---------------------------------------------------------------------------
# Validator dynamics checks
# ---------------------------------------------------------------------------


class TestValidatorDynamicsChecks:
    """Test that the IdentityValidator catches dynamics issues."""

    def test_unknown_trait_in_mood_warns(self):
        from personanexus.validator import IdentityValidator

        dynamics = DynamicsConfig(
            default_mood="bad",
            moods=[DynamicMood(name="bad", trait_deltas={"fake_trait": 0.1})],
        )
        identity = _make_minimal_identity(dynamics)
        validator = IdentityValidator()
        result = validator.validate_identity(identity)
        warns = [w for w in result.warnings if w.type == "dynamics_unknown_trait"]
        assert len(warns) == 1
        assert "fake_trait" in warns[0].message

    def test_unknown_trait_in_mode_warns(self):
        from personanexus.validator import IdentityValidator

        dynamics = DynamicsConfig(
            default_mode="bad",
            modes=[DynamicMode(name="bad", trait_overrides={"fake_trait": 0.5})],
        )
        identity = _make_minimal_identity(dynamics)
        validator = IdentityValidator()
        result = validator.validate_identity(identity)
        warns = [w for w in result.warnings if w.type == "dynamics_unknown_trait"]
        assert len(warns) == 1

    def test_invalid_unlock_target_warns(self):
        from personanexus.validator import IdentityValidator

        dynamics = DynamicsConfig(
            default_mode="real",
            modes=[DynamicMode(name="real")],
            memory_influences=[
                MemoryInfluenceRule(
                    condition="trust_score > 0.5",
                    effect="unlock_mode ghost_mode",
                )
            ],
        )
        identity = _make_minimal_identity(dynamics)
        validator = IdentityValidator()
        result = validator.validate_identity(identity)
        warns = [w for w in result.warnings if w.type == "dynamics_invalid_unlock"]
        assert len(warns) == 1
        assert "ghost_mode" in warns[0].message

    def test_unreachable_mood_warns(self):
        from personanexus.validator import IdentityValidator

        dynamics = DynamicsConfig(
            default_mood="neutral",
            moods=[
                DynamicMood(name="neutral"),
                DynamicMood(name="orphan"),  # no triggers, not default
            ],
        )
        identity = _make_minimal_identity(dynamics)
        validator = IdentityValidator()
        result = validator.validate_identity(identity)
        warns = [w for w in result.warnings if w.type == "dynamics_unreachable"]
        assert len(warns) == 1
        assert "orphan" in warns[0].message

    def test_no_dynamics_no_warnings(self):
        from personanexus.validator import IdentityValidator

        identity = _make_minimal_identity(None)
        validator = IdentityValidator()
        result = validator.validate_identity(identity)
        dynamics_warns = [w for w in result.warnings if w.type.startswith("dynamics_")]
        assert len(dynamics_warns) == 0
