"""Tests for personanexus.memory — per-user persistent state backend."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from personanexus.memory import (
    MemoryBackendJSON,
    UserState,
    increment_custom,
    record_interaction,
    update_sentiment,
    update_trust,
)


class TestUserState:
    def test_defaults(self):
        state = UserState(user_id="u1")
        assert state.interaction_count == 0
        assert state.avg_sentiment == 0.5
        assert state.trust_score == 0.0
        assert state.current_mood == "neutral"
        assert state.current_mode == "stranger"
        assert state.custom == {}
        assert state.applied_influences == []

    def test_roundtrip(self):
        state = UserState(user_id="u2", interaction_count=5, trust_score=0.7)
        d = state.to_dict()
        restored = UserState.from_dict(d)
        assert restored.user_id == "u2"
        assert restored.interaction_count == 5
        assert restored.trust_score == 0.7


class TestUpdateFunctions:
    def test_update_sentiment_first(self):
        state = UserState(user_id="u1")
        update_sentiment(state, 0.8)
        assert state.avg_sentiment == 0.8

    def test_update_sentiment_exponential(self):
        state = UserState(user_id="u1", interaction_count=1, avg_sentiment=0.5)
        update_sentiment(state, 1.0, alpha=0.5)
        assert state.avg_sentiment == pytest.approx(0.75)

    def test_update_sentiment_clamped(self):
        state = UserState(user_id="u1")
        update_sentiment(state, 1.5)
        # First call: interaction_count=0 → set directly to clamped 1.0
        assert state.avg_sentiment == 1.0
        # Simulate having had at least 1 interaction for EMA to kick in
        state.interaction_count = 1
        update_sentiment(state, -0.5)
        # clamped input to 0.0, then: 0.3 * 0.0 + 0.7 * 1.0 = 0.7
        assert state.avg_sentiment == pytest.approx(0.7)

    def test_update_trust(self):
        state = UserState(user_id="u1", trust_score=0.5)
        update_trust(state, 0.3)
        assert state.trust_score == pytest.approx(0.8)

    def test_update_trust_clamped(self):
        state = UserState(user_id="u1", trust_score=0.9)
        update_trust(state, 0.5)
        assert state.trust_score == 1.0
        update_trust(state, -2.0)
        assert state.trust_score == 0.0

    def test_increment_custom(self):
        state = UserState(user_id="u1")
        increment_custom(state, "positive_interactions")
        assert state.custom["positive_interactions"] == 1
        increment_custom(state, "positive_interactions", 5)
        assert state.custom["positive_interactions"] == 6

    def test_record_interaction(self):
        state = UserState(user_id="u1")
        record_interaction(state, sentiment=0.8, trust_delta=0.1, positive=True)
        assert state.interaction_count == 1
        assert state.custom["positive_interactions"] == 1
        assert state.trust_score == pytest.approx(0.1)

    def test_record_interaction_negative(self):
        state = UserState(user_id="u1")
        record_interaction(state, sentiment=0.2, positive=False)
        assert state.custom["negative_interactions"] == 1


class TestMemoryBackendJSON:
    def test_load_new_user(self, tmp_path: Path):
        backend = MemoryBackendJSON(tmp_path / "mem")
        state = backend.load("new_user")
        assert state.user_id == "new_user"
        assert state.interaction_count == 0

    def test_save_and_load(self, tmp_path: Path):
        backend = MemoryBackendJSON(tmp_path / "mem")
        state = UserState(user_id="test_user", interaction_count=10, trust_score=0.75)
        backend.save(state)

        loaded = backend.load("test_user")
        assert loaded.user_id == "test_user"
        assert loaded.interaction_count == 10
        assert loaded.trust_score == 0.75

    def test_delete(self, tmp_path: Path):
        backend = MemoryBackendJSON(tmp_path / "mem")
        state = UserState(user_id="del_user")
        backend.save(state)
        assert backend.delete("del_user") is True
        assert backend.delete("del_user") is False

    def test_list_users(self, tmp_path: Path):
        backend = MemoryBackendJSON(tmp_path / "mem")
        assert backend.list_users() == []
        backend.save(UserState(user_id="a"))
        backend.save(UserState(user_id="b"))
        assert len(backend.list_users()) == 2

    def test_corrupt_file(self, tmp_path: Path):
        backend = MemoryBackendJSON(tmp_path / "mem")
        # Save then corrupt
        state = UserState(user_id="corrupt")
        backend.save(state)
        path = backend._path_for("corrupt")
        path.write_text("not json", encoding="utf-8")
        loaded = backend.load("corrupt")
        assert loaded.user_id == "corrupt"
        assert loaded.interaction_count == 0
