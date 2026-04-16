"""Evolution Lab UI for reviewing and guiding persona evolution."""

from __future__ import annotations

import html
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from components import TRAIT_ORDER, render_comparison_bars, render_trait_bars

from personanexus.evolution import (
    configure_evolution,
    evolution_state_path,
    evolve_persona,
    export_evolved_persona,
    load_evolution_state,
    load_identity_with_evolution,
    promote_candidate,
    reset_evolution,
    resolve_persona_path,
    rollback_evolution,
)
from personanexus.parser import parse_identity_file
from personanexus.types import EvolutionMode, LearningRate, ReviewMode

DEFAULT_PERSONA_DIRS = [
    Path("examples/identities"),
    Path("examples/archetypes"),
    Path("agents"),
]

HARD_TRAIT_OPTIONS = TRAIT_ORDER + [
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
    "dominance",
    "influence",
    "steadiness",
]


def _discover_personas() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for base in DEFAULT_PERSONA_DIRS:
        if not base.exists():
            continue
        for path in sorted(base.glob("*.yaml")):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(resolved)
    return paths


def _persona_label(path: Path) -> str:
    try:
        rel = path.relative_to(Path.cwd())
        return str(rel)
    except ValueError:
        return str(path)


def _trait_dict(identity) -> dict[str, float]:
    traits = identity.personality.traits
    values: dict[str, float] = {}
    for trait in TRAIT_ORDER:
        value = getattr(traits, trait, None)
        values[trait] = 0.5 if value is None else float(value)
    return values


def _render_config_panel(persona_path: Path, identity) -> None:
    evo = identity.evolution
    st.markdown("#### Evolution Configuration")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Enabled", "Yes" if evo.enabled else "No")
    col2.metric("Mode", evo.mode.value)
    col3.metric("Learning Rate", evo.learning_rate.value)
    col4.metric("Consensus", str(evo.consensus_threshold))

    with st.expander("Configure evolution", expanded=not evo.enabled):
        mode = st.selectbox(
            "Mode",
            [mode.value for mode in EvolutionMode],
            index=[mode.value for mode in EvolutionMode].index(evo.mode.value),
            key="evolution_mode_select",
        )
        learning_rate = st.selectbox(
            "Learning rate",
            [rate.value for rate in LearningRate],
            index=[rate.value for rate in LearningRate].index(evo.learning_rate.value),
            key="evolution_learning_rate_select",
        )
        review_mode = st.selectbox(
            "Review mode",
            [review.value for review in ReviewMode],
            index=[review.value for review in ReviewMode].index(evo.review_mode.value),
            key="evolution_review_mode_select",
        )
        consensus = st.number_input(
            "Consensus threshold",
            min_value=1,
            max_value=10,
            value=int(evo.consensus_threshold),
            step=1,
            key="evolution_consensus_threshold",
        )
        if st.button("Save evolution settings", type="primary", use_container_width=True):
            configure_evolution(
                persona_path,
                mode=EvolutionMode(mode),
                learning_rate=LearningRate(learning_rate),
                consensus_threshold=int(consensus),
                review_mode=ReviewMode(review_mode),
            )
            st.success("Evolution settings saved.")
            st.rerun()


def _render_trait_viewer(base_identity, evolved_identity, state) -> None:
    base_traits = _trait_dict(base_identity)
    evolved_traits = _trait_dict(evolved_identity)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Base persona traits")
        st.markdown(render_trait_bars(base_traits), unsafe_allow_html=True)
    with right:
        st.markdown("#### Evolved persona traits")
        st.markdown(render_trait_bars(evolved_traits), unsafe_allow_html=True)

    st.markdown("#### Trait deltas")
    st.markdown(
        render_comparison_bars(base_traits, evolved_traits, "Base", "Evolved"),
        unsafe_allow_html=True,
    )

    guidance = state.soft_deltas.get("tone_guidance", "").strip()
    if guidance:
        st.markdown("#### Active soft guidance")
        st.info(guidance)

    st.markdown("#### Active hard deltas")
    if state.hard_deltas:
        for trait, record in sorted(state.hard_deltas.items()):
            sign = "+" if record.delta > 0 else ""
            st.markdown(
                f"- **{html.escape(trait)}**: `{sign}{record.delta:.2f}`"
                f" applied at `{record.applied_at}`"
            )
    else:
        st.caption("No hard deltas have been accepted yet.")


def _render_feedback_form(persona_path: Path, identity) -> None:
    st.markdown("#### Submit feedback")
    st.caption("Queue a soft or hard evolution candidate for review.")

    feedback_text = st.text_area(
        "Feedback",
        placeholder="Examples: be more concise, warmer in openings, less aggressive",
        key="evolution_feedback_text",
    )
    candidate_mode = st.radio(
        "Candidate type",
        ["auto", "soft", "hard"],
        horizontal=True,
        key="evolution_candidate_mode",
    )
    thumbs_down = st.checkbox(
        "Treat as negative feedback / thumbs down",
        key="evolution_thumbs_down",
    )

    trait = None
    change = None
    if candidate_mode == "hard":
        trait = st.selectbox("Trait", HARD_TRAIT_OPTIONS, key="evolution_hard_trait")
        change = st.slider(
            "Requested change",
            min_value=-0.30,
            max_value=0.30,
            value=0.10,
            step=0.05,
            key="evolution_hard_change",
        )

    disabled = not identity.evolution.enabled
    if disabled:
        st.warning("Enable evolution first to submit feedback.")

    if st.button("Queue candidate", type="primary", use_container_width=True, disabled=disabled):
        if not feedback_text.strip():
            st.error("Feedback text is required.")
            return
        kwargs = {
            "feedback": feedback_text.strip(),
            "thumbs_down": thumbs_down,
        }
        if candidate_mode != "auto":
            kwargs["candidate_type"] = candidate_mode
        if candidate_mode == "hard":
            kwargs["trait"] = trait
            kwargs["change"] = change
        try:
            candidate = evolve_persona(persona_path, **kwargs)
            st.success(f"Queued {candidate.type} candidate {candidate.id}.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _render_candidate_review(persona_path: Path, state) -> None:
    st.markdown("#### Pending candidates")
    pending = [candidate for candidate in state.pending_candidates if candidate.status == "pending"]
    if not pending:
        st.info("No pending candidates.")
        return

    for candidate in pending:
        with st.container(border=True):
            st.markdown(
                f"**{candidate.id}**, {candidate.type.upper()} candidate, "
                f"created `{candidate.timestamp}`"
            )
            st.markdown(f"- Reason: {candidate.reason}")
            if candidate.guidance:
                st.markdown(f"- Guidance: {candidate.guidance}")
            if candidate.trait and candidate.change is not None:
                sign = "+" if candidate.change > 0 else ""
                st.markdown(f"- Proposed change: `{candidate.trait}` {sign}{candidate.change:.2f}")
            st.markdown(
                f"- Signals: support `{candidate.signals_supporting}`"
                f", oppose `{candidate.signals_opposing}`"
            )

            col_accept, col_reject = st.columns(2)
            with col_accept:
                if st.button("Accept", key=f"accept_{candidate.id}", use_container_width=True):
                    try:
                        promote_candidate(persona_path, candidate.id, accept=True)
                        st.success(f"Accepted {candidate.id}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            with col_reject:
                if st.button("Reject", key=f"reject_{candidate.id}", use_container_width=True):
                    try:
                        promote_candidate(persona_path, candidate.id, accept=False)
                        st.success(f"Rejected {candidate.id}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))


def _render_history(persona_path: Path, state) -> None:
    st.markdown("#### Evolution history")
    col1, col2, col3 = st.columns(3)
    col1.metric("Current version", str(state.version))
    col2.metric("Adjustments", str(len(state.adjustments)))
    col3.metric("Rejected", str(len(state.rejected_candidates)))

    with st.expander("Version snapshots", expanded=True):
        if state.history:
            for snapshot in reversed(state.history):
                st.markdown(
                    f"- **v{snapshot.version}** at `{snapshot.timestamp}`"
                    f", soft deltas `{len(snapshot.soft_deltas)}`"
                    f", hard deltas `{len(snapshot.hard_deltas)}`"
                )
        else:
            st.caption("No snapshots yet.")

    with st.expander("Adjustment log", expanded=True):
        if state.adjustments:
            for adj in reversed(state.adjustments):
                parts = [f"**{adj.type}**", f"`{adj.timestamp}`", html.escape(adj.reason)]
                if adj.trait and adj.change is not None:
                    sign = "+" if adj.change > 0 else ""
                    parts.append(f"{html.escape(adj.trait)} {sign}{adj.change:.2f}")
                st.markdown(" - ".join(parts))
        else:
            st.caption("No accepted adjustments yet.")

    with st.expander("Rejected candidates"):
        if state.rejected_candidates:
            for rejected in reversed(state.rejected_candidates):
                st.markdown(
                    f"- **{rejected.id}** `{rejected.timestamp}`: {html.escape(rejected.reason)}"
                )
        else:
            st.caption("No rejected candidates.")

    st.markdown("#### Maintenance")
    ops1, ops2 = st.columns(2)
    with ops1:
        rollback_version = st.number_input(
            "Rollback to version",
            min_value=1,
            max_value=max(1, int(state.version)),
            value=max(1, int(state.version)),
            step=1,
            key="evolution_rollback_version",
        )
        if st.button("Rollback", use_container_width=True):
            try:
                rollback_evolution(persona_path, int(rollback_version))
                st.success(f"Rolled back to snapshot version {rollback_version}.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with ops2:
        export_target = evolution_state_path(persona_path).with_name(
            f"{persona_path.stem}-evolved.yaml"
        )
        if st.button("Export evolved YAML", use_container_width=True):
            out = export_evolved_persona(persona_path, export_target)
            st.success(f"Exported evolved YAML to {out}")
        if st.button("Reset evolution state", use_container_width=True):
            reset_evolution(persona_path)
            st.success("Evolution state reset.")
            st.rerun()


def render_evolution() -> None:
    st.markdown(
        '<div class="main-header">🧬 Evolution Lab</div>'
        '<div class="sub-header">Review persona drift, queue feedback, and '
        "approve evolution candidates</div>",
        unsafe_allow_html=True,
    )

    discovered = _discover_personas()
    options = [_persona_label(path) for path in discovered]
    selected = ""
    if options:
        default_index = (
            options.index("examples/identities/mira.yaml")
            if "examples/identities/mira.yaml" in options
            else 0
        )
        selected = st.selectbox("Persona", options, index=default_index)
    else:
        st.info("No bundled personas were found, but you can still enter a path manually below.")
    manual_path = st.text_input(
        "Or enter a persona path",
        value="",
        placeholder="examples/identities/mira.yaml",
    )

    persona_ref = manual_path.strip() or selected
    if not persona_ref:
        return

    try:
        persona_path = resolve_persona_path(persona_ref)
        base_identity = parse_identity_file(persona_path)
        evolved_identity = load_identity_with_evolution(persona_path)
        state = load_evolution_state(persona_path, create=True)
        assert state is not None
    except Exception as exc:
        st.error(f"Could not load persona: {exc}")
        return

    st.caption(f"Loaded `{persona_path}`")
    _render_config_panel(persona_path, base_identity)

    tabs = st.tabs(["Trait Viewer", "Feedback", "Candidate Review", "History"])
    with tabs[0]:
        _render_trait_viewer(base_identity, evolved_identity, state)
    with tabs[1]:
        _render_feedback_form(persona_path, base_identity)
    with tabs[2]:
        _render_candidate_review(persona_path, state)
    with tabs[3]:
        _render_history(persona_path, state)
