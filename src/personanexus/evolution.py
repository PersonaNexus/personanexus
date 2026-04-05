"""Persona evolution engine for PersonaNexus."""

from __future__ import annotations

import hashlib
import json
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from personanexus.parser import parse_identity_file
from personanexus.personality import get_disc_preset, get_jungian_preset
from personanexus.resolver import IdentityResolver
from personanexus.types import AgentIdentity, EvolutionMode, LearningRate, ReviewMode

TOTAL_HARD_CAP = 0.30
SOFT_DELTA_KEY = "tone_guidance"


class HardDeltaRecord(BaseModel):
    delta: float
    applied_at: str


class AdjustmentRecord(BaseModel):
    id: str
    timestamp: str
    type: Literal["soft", "hard", "reset", "rollback"]
    trait: str | None = None
    change: float | None = None
    reason: str
    source: str
    signals_supporting: int = 0
    signals_opposing: int = 0


class RejectedCandidate(BaseModel):
    id: str
    timestamp: str
    type: Literal["soft", "hard"]
    trait: str | None = None
    change: float | None = None
    reason: str
    auto_rejected: bool = False


class CandidateProposal(BaseModel):
    id: str
    timestamp: str
    type: Literal["soft", "hard"]
    trait: str | None = None
    change: float | None = None
    guidance: str | None = None
    reason: str
    source: str = "manual_feedback"
    response_id: str | None = None
    feedback_message: str | None = None
    signals_supporting: int = 1
    signals_opposing: int = 0
    status: Literal["pending", "accepted", "rejected"] = "pending"


class VersionSnapshot(BaseModel):
    version: int
    timestamp: str
    soft_deltas: dict[str, str] = Field(default_factory=dict)
    hard_deltas: dict[str, HardDeltaRecord] = Field(default_factory=dict)


class EvolutionState(BaseModel):
    persona: str
    version: int = 1
    base_yaml_hash: str
    created: str
    last_updated: str
    soft_deltas: dict[str, str] = Field(default_factory=dict)
    hard_deltas: dict[str, HardDeltaRecord] = Field(default_factory=dict)
    pending_candidates: list[CandidateProposal] = Field(default_factory=list)
    adjustments: list[AdjustmentRecord] = Field(default_factory=list)
    rejected_candidates: list[RejectedCandidate] = Field(default_factory=list)
    history: list[VersionSnapshot] = Field(default_factory=list)


KEYWORD_RULES: list[dict[str, Any]] = [
    {
        "keywords": ["warmer", "more empathetic", "less harsh", "gentler", "kinder"],
        "trait": "agreeableness",
        "change": 0.10,
        "guidance": "Be slightly warmer, more empathetic, and less abrasive in tone.",
    },
    {
        "keywords": ["more concise", "too verbose", "shorter", "less wordy", "more direct"],
        "trait": None,
        "change": None,
        "guidance": "Prefer shorter, more concise answers with faster access to the main point.",
    },
    {
        "keywords": ["more careful", "more rigorous", "double-check", "less sloppy"],
        "trait": "conscientiousness",
        "change": 0.10,
        "guidance": "Be more rigorous, careful, and explicit about verification.",
    },
    {
        "keywords": ["less aggressive", "too aggressive", "too forceful"],
        "trait": "dominance",
        "change": -0.10,
        "guidance": "Reduce aggressive phrasing and soften imperative language.",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_text(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def _learning_rate_cap(rate: LearningRate) -> float:
    return {
        LearningRate.LOW: 0.05,
        LearningRate.MEDIUM: 0.15,
        LearningRate.HIGH: 0.30,
    }[rate]


def resolve_persona_path(persona: str | Path) -> Path:
    path = Path(persona)
    candidates = [path]
    if path.suffix != ".yaml":
        candidates.extend(
            [
                Path(f"{persona}.yaml"),
                Path("agents") / f"{persona}.yaml",
                Path("examples/identities") / f"{persona}.yaml",
            ]
        )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Persona not found: {persona}")


def evolution_state_path(persona_path: str | Path) -> Path:
    path = Path(persona_path)
    return path.parent / ".evolution" / f"{path.stem}.json"


def load_persona_data(persona_path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(persona_path).read_text(encoding="utf-8"))


def save_persona_data(persona_path: str | Path, data: dict[str, Any]) -> None:
    Path(persona_path).write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def create_initial_state(persona_path: str | Path) -> EvolutionState:
    path = Path(persona_path)
    now = _now_iso()
    payload = path.read_text(encoding="utf-8")
    state = EvolutionState(
        persona=path.stem,
        version=1,
        base_yaml_hash=_sha256_text(payload),
        created=now,
        last_updated=now,
        history=[VersionSnapshot(version=1, timestamp=now)],
    )
    save_evolution_state(path, state)
    return state


def load_evolution_state(persona_path: str | Path, create: bool = True) -> EvolutionState | None:
    state_path = evolution_state_path(persona_path)
    if not state_path.exists():
        return create_initial_state(persona_path) if create else None
    data = json.loads(state_path.read_text(encoding="utf-8"))
    return EvolutionState.model_validate(data)


def save_evolution_state(persona_path: str | Path, state: EvolutionState) -> None:
    state.last_updated = _now_iso()
    state_path = evolution_state_path(persona_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state.model_dump(mode="json"), indent=2), encoding="utf-8")


def ensure_evolution_enabled(persona_path: str | Path) -> dict[str, Any]:
    data = load_persona_data(persona_path)
    evolution = data.setdefault("evolution", {})
    evolution.setdefault("enabled", False)
    evolution.setdefault("mode", "soft")
    evolution.setdefault("learning_rate", "medium")
    evolution.setdefault("consensus_threshold", 3)
    evolution.setdefault("protected_traits", [])
    evolution.setdefault("judge_model", "gemma4:e4b")
    evolution.setdefault("review_mode", "prompt")
    save_persona_data(persona_path, data)
    return data


def configure_evolution(
    persona_path: str | Path,
    *,
    mode: EvolutionMode,
    learning_rate: LearningRate = LearningRate.MEDIUM,
    consensus_threshold: int = 3,
    review_mode: ReviewMode = ReviewMode.PROMPT,
) -> dict[str, Any]:
    data = ensure_evolution_enabled(persona_path)
    evolution = data.setdefault("evolution", {})
    evolution.update(
        {
            "enabled": True,
            "mode": mode.value,
            "learning_rate": learning_rate.value,
            "consensus_threshold": consensus_threshold,
            "review_mode": review_mode.value,
        }
    )
    save_persona_data(persona_path, data)
    load_evolution_state(persona_path, create=True)
    return data


def _get_evolution_config(identity: AgentIdentity) -> Any:
    return identity.evolution


def _candidate_support_count(
    state: EvolutionState,
    *,
    trait: str | None,
    change: float | None,
    guidance: str | None,
    candidate_type: str,
) -> int:
    if candidate_type == "soft":
        return (
            sum(1 for c in state.pending_candidates if c.type == "soft" and c.guidance == guidance)
            + 1
        )
    direction = 0 if change is None else (1 if change > 0 else -1)
    return (
        sum(
            1
            for c in state.pending_candidates
            if c.type == "hard"
            and c.trait == trait
            and c.change is not None
            and (1 if c.change > 0 else -1) == direction
        )
        + 1
    )


def _infer_candidate(
    feedback: str,
    *,
    source: str,
    explicit_type: str | None,
    trait: str | None,
    change: float | None,
    thumbs_down: bool,
) -> CandidateProposal:
    message = feedback.strip()
    if explicit_type == "hard" or trait or change is not None:
        return CandidateProposal(
            id=f"cand_{uuid.uuid4().hex[:8]}",
            timestamp=_now_iso(),
            type="hard",
            trait=trait,
            change=change,
            reason=message or "Manual hard-evolution feedback",
            source=source,
            feedback_message=message or None,
        )

    lowered = message.lower()
    for rule in KEYWORD_RULES:
        if any(keyword in lowered for keyword in rule["keywords"]):
            if rule["trait"] is not None:
                delta = float(rule["change"])
                if thumbs_down and delta > 0:
                    delta *= -1
                return CandidateProposal(
                    id=f"cand_{uuid.uuid4().hex[:8]}",
                    timestamp=_now_iso(),
                    type="hard",
                    trait=str(rule["trait"]),
                    change=delta,
                    guidance=str(rule["guidance"]),
                    reason=message,
                    source=source,
                    feedback_message=message,
                )
            return CandidateProposal(
                id=f"cand_{uuid.uuid4().hex[:8]}",
                timestamp=_now_iso(),
                type="soft",
                guidance=str(rule["guidance"]),
                reason=message,
                source=source,
                feedback_message=message,
            )

    return CandidateProposal(
        id=f"cand_{uuid.uuid4().hex[:8]}",
        timestamp=_now_iso(),
        type="soft",
        guidance=message or "Adjust tone based on recent feedback.",
        reason=message or "Manual soft-evolution feedback",
        source=source,
        feedback_message=message or None,
    )


def evolve_persona(
    persona: str | Path,
    *,
    feedback: str,
    source: str = "manual_feedback",
    candidate_type: Literal["soft", "hard"] | None = None,
    trait: str | None = None,
    change: float | None = None,
    thumbs_down: bool = False,
    response_id: str | None = None,
) -> CandidateProposal:
    persona_path = resolve_persona_path(persona)
    identity = parse_identity_file(persona_path)
    if not identity.evolution.enabled:
        raise ValueError("Evolution is not enabled for this persona")

    state = load_evolution_state(persona_path, create=True)
    assert state is not None

    candidate = _infer_candidate(
        feedback,
        source=source,
        explicit_type=candidate_type,
        trait=trait,
        change=change,
        thumbs_down=thumbs_down,
    )
    candidate.response_id = response_id

    if candidate.type == "hard":
        if identity.evolution.mode == EvolutionMode.SOFT:
            raise ValueError("Persona is configured for soft evolution only")
        if candidate.trait is None or candidate.change is None:
            raise ValueError("Hard evolution feedback requires a trait and change")
        cap = _learning_rate_cap(identity.evolution.learning_rate)
        if abs(candidate.change) > cap:
            candidate.change = cap if candidate.change > 0 else -cap
        if candidate.trait in identity.evolution.protected_traits:
            rejection = RejectedCandidate(
                id=candidate.id,
                timestamp=_now_iso(),
                type="hard",
                trait=candidate.trait,
                change=candidate.change,
                reason="trait is protected",
                auto_rejected=True,
            )
            state.rejected_candidates.append(rejection)
            save_evolution_state(persona_path, state)
            raise ValueError(f"Trait '{candidate.trait}' is protected and cannot evolve")
    else:
        if identity.evolution.mode == EvolutionMode.HARD:
            raise ValueError("Persona is configured for hard evolution only")

    candidate.signals_supporting = _candidate_support_count(
        state,
        trait=candidate.trait,
        change=candidate.change,
        guidance=candidate.guidance,
        candidate_type=candidate.type,
    )
    state.pending_candidates.append(candidate)
    save_evolution_state(persona_path, state)
    return candidate


def get_candidates(persona: str | Path) -> list[CandidateProposal]:
    persona_path = resolve_persona_path(persona)
    state = load_evolution_state(persona_path, create=False)
    if state is None:
        return []
    return [candidate for candidate in state.pending_candidates if candidate.status == "pending"]


def _record_snapshot(state: EvolutionState) -> None:
    state.history.append(
        VersionSnapshot(
            version=state.version,
            timestamp=_now_iso(),
            soft_deltas=deepcopy(state.soft_deltas),
            hard_deltas=deepcopy(state.hard_deltas),
        )
    )


def _append_soft_guidance(state: EvolutionState, guidance: str) -> None:
    existing = state.soft_deltas.get(SOFT_DELTA_KEY, "").strip()
    if not existing:
        state.soft_deltas[SOFT_DELTA_KEY] = guidance.strip()
    elif guidance.strip() not in existing:
        state.soft_deltas[SOFT_DELTA_KEY] = f"{existing} {guidance.strip()}".strip()


def promote_candidate(
    persona: str | Path,
    candidate_id: str,
    *,
    accept: bool,
    reject_reason: str | None = None,
) -> CandidateProposal:
    persona_path = resolve_persona_path(persona)
    identity = parse_identity_file(persona_path)
    state = load_evolution_state(persona_path, create=True)
    assert state is not None

    for candidate in state.pending_candidates:
        if candidate.id != candidate_id or candidate.status != "pending":
            continue

        if not accept:
            candidate.status = "rejected"
            state.rejected_candidates.append(
                RejectedCandidate(
                    id=candidate.id,
                    timestamp=_now_iso(),
                    type=candidate.type,
                    trait=candidate.trait,
                    change=candidate.change,
                    reason=reject_reason or "rejected by reviewer",
                )
            )
            save_evolution_state(persona_path, state)
            return candidate

        if candidate.type == "soft":
            state.version += 1
            _append_soft_guidance(state, candidate.guidance or candidate.reason)
            candidate.status = "accepted"
            state.adjustments.append(
                AdjustmentRecord(
                    id=candidate.id,
                    timestamp=_now_iso(),
                    type="soft",
                    reason=candidate.reason,
                    source=candidate.source,
                    signals_supporting=candidate.signals_supporting,
                    signals_opposing=candidate.signals_opposing,
                )
            )
            _record_snapshot(state)
            save_evolution_state(persona_path, state)
            return candidate

        assert candidate.trait is not None and candidate.change is not None
        if candidate.signals_supporting < identity.evolution.consensus_threshold:
            raise ValueError(
                f"Hard evolution requires {identity.evolution.consensus_threshold} aligned signals"
            )
        current_delta = state.hard_deltas.get(candidate.trait, HardDeltaRecord(delta=0.0, applied_at=_now_iso())).delta
        proposed_total = current_delta + candidate.change
        if abs(proposed_total) > TOTAL_HARD_CAP:
            state.rejected_candidates.append(
                RejectedCandidate(
                    id=candidate.id,
                    timestamp=_now_iso(),
                    type="hard",
                    trait=candidate.trait,
                    change=candidate.change,
                    reason="exceeds total hard-evolution cap",
                    auto_rejected=True,
                )
            )
            candidate.status = "rejected"
            save_evolution_state(persona_path, state)
            raise ValueError("Hard evolution exceeds ±0.30 total cap")

        state.version += 1
        state.hard_deltas[candidate.trait] = HardDeltaRecord(delta=proposed_total, applied_at=_now_iso())
        candidate.status = "accepted"
        state.adjustments.append(
            AdjustmentRecord(
                id=candidate.id,
                timestamp=_now_iso(),
                type="hard",
                trait=candidate.trait,
                change=candidate.change,
                reason=candidate.reason,
                source=candidate.source,
                signals_supporting=candidate.signals_supporting,
                signals_opposing=candidate.signals_opposing,
            )
        )
        _record_snapshot(state)
        save_evolution_state(persona_path, state)
        return candidate

    raise KeyError(f"Candidate not found: {candidate_id}")


def promote_all(persona: str | Path) -> tuple[list[CandidateProposal], list[str]]:
    persona_path = resolve_persona_path(persona)
    state = load_evolution_state(persona_path, create=False)
    if state is None:
        return ([], [])

    grouped: dict[tuple[str, str], CandidateProposal] = {}
    for candidate in state.pending_candidates:
        if candidate.status != "pending":
            continue
        if candidate.type == "soft":
            key = (candidate.type, candidate.guidance or candidate.reason)
        else:
            direction = "0" if candidate.change is None else ("+" if candidate.change > 0 else "-")
            key = (candidate.type, f"{candidate.trait}:{direction}")
        existing = grouped.get(key)
        if existing is None or candidate.signals_supporting > existing.signals_supporting:
            grouped[key] = candidate

    accepted: list[CandidateProposal] = []
    errors: list[str] = []
    for candidate in grouped.values():
        try:
            accepted.append(promote_candidate(persona_path, candidate.id, accept=True))
        except Exception as exc:  # pragma: no cover - exercised through CLI tests too
            errors.append(str(exc))
    return accepted, errors


def reset_evolution(persona: str | Path) -> EvolutionState:
    persona_path = resolve_persona_path(persona)
    state = load_evolution_state(persona_path, create=True)
    assert state is not None
    state.version += 1
    state.soft_deltas = {}
    state.hard_deltas = {}
    state.pending_candidates = []
    state.adjustments.append(
        AdjustmentRecord(
            id=f"reset_{uuid.uuid4().hex[:8]}",
            timestamp=_now_iso(),
            type="reset",
            reason="reset evolution state",
            source="manual",
        )
    )
    _record_snapshot(state)
    save_evolution_state(persona_path, state)
    return state


def rollback_evolution(persona: str | Path, version: int) -> EvolutionState:
    persona_path = resolve_persona_path(persona)
    state = load_evolution_state(persona_path, create=True)
    assert state is not None
    snapshot = next((entry for entry in state.history if entry.version == version), None)
    if snapshot is None:
        raise KeyError(f"Version not found: {version}")
    state.version += 1
    state.soft_deltas = deepcopy(snapshot.soft_deltas)
    state.hard_deltas = deepcopy(snapshot.hard_deltas)
    state.pending_candidates = []
    state.adjustments.append(
        AdjustmentRecord(
            id=f"rollback_{uuid.uuid4().hex[:8]}",
            timestamp=_now_iso(),
            type="rollback",
            reason=f"rollback to version {version}",
            source="manual",
        )
    )
    _record_snapshot(state)
    save_evolution_state(persona_path, state)
    return state


def _apply_soft_deltas(identity: AgentIdentity, state: EvolutionState) -> None:
    guidance = state.soft_deltas.get(SOFT_DELTA_KEY, "").strip()
    if not guidance:
        return
    existing_notes = identity.personality.notes.strip() if identity.personality.notes else ""
    evolution_note = f"Evolution guidance: {guidance}"
    if existing_notes:
        if evolution_note not in existing_notes:
            identity.personality.notes = f"{existing_notes}\n\n{evolution_note}"
    else:
        identity.personality.notes = evolution_note


def _set_trait(identity: AgentIdentity, trait: str, delta: float) -> bool:
    traits = identity.personality.traits
    if hasattr(traits, trait):
        current = getattr(traits, trait)
        current_value = 0.5 if current is None else float(current)
        setattr(traits, trait, max(0.0, min(1.0, current_value + delta)))
        return True

    profile = identity.personality.profile
    if profile.ocean is not None and hasattr(profile.ocean, trait):
        current = float(getattr(profile.ocean, trait))
        setattr(profile.ocean, trait, max(0.0, min(1.0, current + delta)))
        return True

    if profile.disc is None and profile.disc_preset:
        profile.disc = get_disc_preset(profile.disc_preset)
    if profile.disc is not None and hasattr(profile.disc, trait):
        current = float(getattr(profile.disc, trait))
        setattr(profile.disc, trait, max(0.0, min(1.0, current + delta)))
        return True

    if profile.jungian is None and profile.jungian_preset:
        profile.jungian = get_jungian_preset(profile.jungian_preset)
    if profile.jungian is not None and hasattr(profile.jungian, trait):
        current = float(getattr(profile.jungian, trait))
        setattr(profile.jungian, trait, max(0.0, min(1.0, current + delta)))
        return True

    return False


def apply_deltas(identity: AgentIdentity, state: EvolutionState | None) -> AgentIdentity:
    if state is None:
        return identity
    evolved = identity.model_copy(deep=True)
    _apply_soft_deltas(evolved, state)
    for trait, record in state.hard_deltas.items():
        _set_trait(evolved, trait, record.delta)
    return evolved


def load_identity_with_evolution(
    persona: str | Path,
    *,
    search_paths: list[Path] | None = None,
) -> AgentIdentity:
    persona_path = resolve_persona_path(persona)
    resolver = IdentityResolver(search_paths=search_paths or [])
    identity = resolver.resolve_file(persona_path)
    state = load_evolution_state(persona_path, create=False)
    return apply_deltas(identity, state)


def export_evolved_persona(
    persona: str | Path,
    output: str | Path,
    *,
    search_paths: list[Path] | None = None,
) -> Path:
    identity = load_identity_with_evolution(persona, search_paths=search_paths)
    output_path = Path(output)
    output_path.write_text(
        yaml.safe_dump(
            json.loads(identity.model_dump_json(exclude_none=True)),
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return output_path
