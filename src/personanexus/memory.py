"""Persistent per-user memory backend for the dynamic personality layer.

Stores interaction history, sentiment, trust scores, and custom keys per user.
Default backend: JSON files in .personanexus/memory/<user_hash>.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default storage root (relative to CWD or overridden)
DEFAULT_MEMORY_DIR = Path(".personanexus") / "memory"


@dataclass
class UserState:
    """In-memory representation of a single user's persistent state."""

    user_id: str
    interaction_count: int = 0
    avg_sentiment: float = 0.5
    trust_score: float = 0.0
    current_mood: str = "neutral"
    current_mode: str = "stranger"
    custom: dict[str, Any] = field(default_factory=dict)
    applied_influences: list[str] = field(default_factory=list)
    last_updated: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "interaction_count": self.interaction_count,
            "avg_sentiment": self.avg_sentiment,
            "trust_score": self.trust_score,
            "current_mood": self.current_mood,
            "current_mode": self.current_mode,
            "custom": self.custom,
            "applied_influences": self.applied_influences,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserState:
        return cls(
            user_id=data.get("user_id", "unknown"),
            interaction_count=data.get("interaction_count", 0),
            avg_sentiment=data.get("avg_sentiment", 0.5),
            trust_score=data.get("trust_score", 0.0),
            current_mood=data.get("current_mood", "neutral"),
            current_mode=data.get("current_mode", "stranger"),
            custom=data.get("custom", {}),
            applied_influences=data.get("applied_influences", []),
            last_updated=data.get("last_updated", 0.0),
        )


def _user_hash(user_id: str) -> str:
    """Produce a filesystem-safe hash for a user ID."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


class MemoryBackendJSON:
    """Simple JSON-file-per-user persistence backend.

    Files are stored at ``<memory_dir>/<user_hash>.json``.
    """

    def __init__(self, memory_dir: Path | str | None = None) -> None:
        self.memory_dir = Path(memory_dir) if memory_dir else DEFAULT_MEMORY_DIR

    def _path_for(self, user_id: str) -> Path:
        return self.memory_dir / f"{_user_hash(user_id)}.json"

    def load(self, user_id: str) -> UserState:
        """Load user state from disk, returning defaults for new users."""
        path = self._path_for(user_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return UserState.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                logger.warning("Corrupt state file for user %s, resetting.", user_id)
        return UserState(user_id=user_id)

    def save(self, state: UserState) -> None:
        """Persist user state to disk."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(state.user_id)
        state.last_updated = time.time()
        path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

    def delete(self, user_id: str) -> bool:
        """Delete a user's state file. Returns True if it existed."""
        path = self._path_for(user_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_users(self) -> list[str]:
        """List hashed user IDs that have stored state."""
        if not self.memory_dir.exists():
            return []
        return [p.stem for p in self.memory_dir.glob("*.json")]


def update_sentiment(state: UserState, new_sentiment: float, alpha: float = 0.3) -> None:
    """Update the running average sentiment with exponential smoothing.

    Args:
        state: The user state to update.
        new_sentiment: New sentiment score (0.0 = very negative, 1.0 = very positive).
        alpha: Smoothing factor (higher = more weight to recent).
    """
    new_sentiment = max(0.0, min(1.0, new_sentiment))
    if state.interaction_count == 0:
        state.avg_sentiment = new_sentiment
    else:
        state.avg_sentiment = alpha * new_sentiment + (1 - alpha) * state.avg_sentiment


def update_trust(state: UserState, delta: float) -> None:
    """Adjust trust score, clamped to [0, 1]."""
    state.trust_score = max(0.0, min(1.0, state.trust_score + delta))


def increment_custom(state: UserState, key: str, amount: int = 1) -> None:
    """Increment a custom counter in user state."""
    current = state.custom.get(key, 0)
    if not isinstance(current, (int, float)):
        current = 0
    state.custom[key] = current + amount


def record_interaction(
    state: UserState,
    sentiment: float = 0.5,
    trust_delta: float = 0.0,
    positive: bool | None = None,
) -> None:
    """Record a single interaction, updating counts, sentiment, and trust.

    Args:
        state: User state to update.
        sentiment: Sentiment score of this interaction (0-1).
        trust_delta: How much to adjust trust by.
        positive: If True, also increment 'positive_interactions' counter.
    """
    state.interaction_count += 1
    update_sentiment(state, sentiment)
    if trust_delta != 0.0:
        update_trust(state, trust_delta)
    if positive is True:
        increment_custom(state, "positive_interactions")
    elif positive is False:
        increment_custom(state, "negative_interactions")
