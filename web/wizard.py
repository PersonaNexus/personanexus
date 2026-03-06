"""Setup Wizard — Multi-step guided identity builder.

A 6-step wizard that walks users through building a complete AgentIdentity
with live preview, model configuration, and multi-format export.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import streamlit as st
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from components import (  # noqa: E402
    ARCHETYPE_DEFAULTS,
    ARCHETYPE_FULL,
    DISC_LABELS,
    OCEAN_LABELS,
    TRAIT_LABELS,
    TRAIT_ORDER,
    build_identity_from_data,
    render_labeled_slider,
    render_trait_bars,
)
from model_config import ModelConfig, render_model_config, run_chat  # noqa: E402

from personanexus.compiler import SystemPromptCompiler, compile_identity  # noqa: E402
from personanexus.personality import (  # noqa: E402
    disc_to_traits,
    get_disc_preset,
    list_disc_presets,
    ocean_to_traits,
)
from personanexus.types import AgentIdentity, DiscProfile, OceanProfile  # noqa: E402

# ---------------------------------------------------------------------------
# Step metadata
# ---------------------------------------------------------------------------

STEP_LABELS = [
    "Role & Basics",
    "Personality",
    "Communication",
    "Principles & Guardrails",
    "Expertise",
    "Model & Export",
]
NUM_STEPS = len(STEP_LABELS)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def _wiz() -> dict[str, Any]:
    """Return (or initialise) the wizard data dict in session state."""
    if "wizard_data" not in st.session_state:
        st.session_state["wizard_data"] = _default_wizard_data()
    return st.session_state["wizard_data"]


def _step() -> int:
    return st.session_state.get("wizard_step", 0)


def _set_step(n: int) -> None:
    st.session_state["wizard_step"] = max(0, min(n, NUM_STEPS - 1))


def _default_wizard_data() -> dict[str, Any]:
    """Sensible defaults for a brand-new wizard session."""
    return {
        # Step 1 — Role & Basics
        "name": "",
        "role_title": "",
        "purpose": "",
        "description": "",
        "scope_primary": "",
        "audience": "",
        # Step 2 — Personality
        "traits": dict.fromkeys(TRAIT_ORDER, 0.5),
        "profile": {"mode": "custom"},
        # Step 3 — Communication
        "tone": "professional and helpful",
        "register": "consultative",
        "emoji": "sparingly",
        "sentence_length": "mixed",
        "use_headers": True,
        "use_lists": True,
        "vocab_preferred": "",
        "vocab_avoided": "",
        "vocab_signature": "",
        # Step 4 — Principles & Guardrails
        "principles": ["Always prioritize being helpful and accurate"],
        "guardrails": ["Never generate harmful, illegal, or unethical content"],
        "guardrail_severities": {0: "critical"},
        "forbidden_topics": "",
        # Step 5 — Expertise
        "expertise_domains": [],
        # Step 6 — Model
        "model_config": ModelConfig().to_dict(),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def render_wizard() -> None:
    """Render the full setup wizard in the main content area."""
    step = _step()

    # Progress bar using Streamlit columns
    step_cols = st.columns(NUM_STEPS)
    for i, (col, label) in enumerate(zip(step_cols, STEP_LABELS, strict=False)):
        with col:
            circle = (
                "display:inline-block;width:32px;height:32px;"
                "border-radius:50%;line-height:32px;"
                "font-weight:600;font-size:0.8rem"
            )
            if i < step:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span style='{circle};"
                    f"background:#10b981;color:white'>"
                    f"\u2713</span><br>"
                    f"<span style='font-size:0.7rem;"
                    f"color:#4a5568'>{label}</span></div>",
                    unsafe_allow_html=True,
                )
            elif i == step:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span style='{circle};"
                    f"background:#3b82f6;color:white;"
                    f"box-shadow:0 0 0 3px "
                    f"rgba(59,130,246,0.3)'>"
                    f"{i+1}</span><br>"
                    f"<span style='font-size:0.7rem;"
                    f"color:#3b82f6;font-weight:600'>"
                    f"{label}</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span style='{circle};"
                    f"background:#d1d5db;color:#4b5563'>"
                    f"{i+1}</span><br>"
                    f"<span style='font-size:0.7rem;"
                    f"color:#4a5568'>{label}</span></div>",
                    unsafe_allow_html=True,
                )

    # Render current step
    renderers = [
        _render_step_role,
        _render_step_personality,
        _render_step_communication,
        _render_step_principles,
        _render_step_expertise,
        _render_step_model_export,
    ]
    renderers[step]()

    # Navigation
    st.divider()
    col_prev, col_spacer, col_next = st.columns([1, 4, 1])
    with col_prev:
        if step > 0 and st.button(
            "\u2190 Previous", use_container_width=True
        ):
            _set_step(step - 1)
            st.rerun()
    with col_next:
        if (
            step < NUM_STEPS - 1
            and st.button(
                "Next \u2192", type="primary",
                use_container_width=True,
            )
            and _validate_step(step)
        ):
            _set_step(step + 1)
            st.rerun()


# ---------------------------------------------------------------------------
# Step 1 — Role & Basics
# ---------------------------------------------------------------------------


def _render_step_role() -> None:
    data = _wiz()
    st.markdown("### Step 1: Role & Basics")
    st.caption("Define who your agent is and what it does.")

    # Quick-start
    st.markdown('<div class="section-label">Quick Start</div>', unsafe_allow_html=True)
    quick = st.selectbox(
        "Start from archetype",
        ["(Start from scratch)"] + list(ARCHETYPE_FULL.keys()),
        key="wiz_quickstart",
        label_visibility="collapsed",
    )
    if quick != "(Start from scratch)":
        arch = ARCHETYPE_FULL[quick]
        if st.button(f'Apply "{quick}" preset', type="secondary"):
            # Update wizard data dict
            data["traits"] = dict(arch["traits"])
            data["tone"] = arch["tone"]
            data["register"] = arch["register"]
            data["emoji"] = arch["emoji"]
            data["principles"] = list(arch["principles"])
            data["guardrails"] = list(arch["guardrails"])
            data["guardrail_severities"] = dict.fromkeys(range(len(arch["guardrails"])), "critical")

            # Pre-seed Step 2 slider widget keys so they reflect the preset
            for trait in TRAIT_ORDER:
                st.session_state[f"wiz_t_{trait}"] = arch["traits"].get(trait, 0.5)

            # Sync Step 2 archetype dropdown to match
            if quick in ARCHETYPE_DEFAULTS:
                st.session_state["wiz_archetype"] = quick
                st.session_state["_wiz_last_arch"] = quick

            # Pre-seed Step 3 communication widget keys
            st.session_state["wiz_tone"] = arch["tone"]
            st.session_state["wiz_register"] = arch["register"]
            st.session_state["wiz_emoji"] = arch["emoji"]

            # Store for visual feedback
            st.session_state["_wiz_preset_applied"] = quick
            st.rerun()

    # Show feedback if a preset was just applied
    if "_wiz_preset_applied" in st.session_state:
        applied = st.session_state["_wiz_preset_applied"]
        if applied in ARCHETYPE_FULL:
            arch_data = ARCHETYPE_FULL[applied]
            trait_count = sum(
                1 for v in arch_data["traits"].values() if abs(v - 0.5) > 0.01
            )
            st.info(
                f'✅ Preset "{applied}" applied: {trait_count} traits customized, '
                f'tone="{arch_data["tone"]}", register="{arch_data["register"]}". '
                f"Values are pre-loaded in Steps 2\u20133."
            )

    st.divider()

    data["name"] = st.text_input(
        "Agent Name *",
        value=data.get("name", ""),
        placeholder="e.g. Ada, CodeBot, Clara",
        key="wiz_name",
    )
    data["role_title"] = st.text_input(
        "Role Title",
        value=data.get("role_title", ""),
        placeholder="e.g. AI Research Assistant, Customer Support Agent",
        key="wiz_role_title",
    )
    data["purpose"] = st.text_area(
        "Purpose *",
        value=data.get("purpose", ""),
        placeholder="What is the primary goal of this agent?",
        height=80,
        key="wiz_purpose",
    )
    data["description"] = st.text_area(
        "Description",
        value=data.get("description", ""),
        placeholder="A brief description of the agent (optional)",
        height=60,
        key="wiz_description",
    )

    col_scope, col_audience = st.columns(2)
    with col_scope:
        data["scope_primary"] = st.text_area(
            "Primary Scope (one per line)",
            value=data.get("scope_primary", ""),
            placeholder="e.g.\nCode review\nDebugging\nDocumentation",
            height=100,
            key="wiz_scope",
        )
    with col_audience:
        data["audience"] = st.text_input(
            "Target Audience",
            value=data.get("audience", ""),
            placeholder="e.g. Software developers, Students, General public",
            key="wiz_audience",
        )


# ---------------------------------------------------------------------------
# Step 2 — Personality
# ---------------------------------------------------------------------------


def _render_step_personality() -> None:
    data = _wiz()
    st.markdown("### Step 2: Personality")
    st.caption("Choose a personality framework and adjust trait values.")

    col_config, col_viz = st.columns([1, 1])

    with col_config:
        mode = st.radio(
            "Framework",
            ["Custom", "OCEAN", "DISC", "Hybrid"],
            horizontal=True,
            key="wiz_pers_mode",
        )

        traits: dict[str, float] = {}
        profile: dict[str, Any] = {}

        if mode == "Custom":
            st.markdown('<div class="section-label">Archetype Preset</div>', unsafe_allow_html=True)

            if "_wiz_last_arch" not in st.session_state:
                st.session_state["_wiz_last_arch"] = "Blank Slate"

            archetype = st.selectbox(
                "Archetype",
                list(ARCHETYPE_DEFAULTS.keys()),
                label_visibility="collapsed",
                key="wiz_archetype",
            )
            defaults = ARCHETYPE_DEFAULTS[archetype]

            arch_changed = st.session_state.get("_wiz_last_arch") != archetype
            if arch_changed:
                st.session_state["_wiz_last_arch"] = archetype
                st.session_state["_wiz_apply_arch"] = archetype

            if st.session_state.pop("_wiz_apply_arch", None):
                for trait in TRAIT_ORDER:
                    st.session_state[f"wiz_t_{trait}"] = defaults.get(trait, 0.5)

            for trait in TRAIT_ORDER:
                label, low, high = TRAIT_LABELS[trait]
                traits[trait] = render_labeled_slider(
                    label, low, high,
                    value=defaults.get(trait, 0.5),
                    step=0.05,
                    key=f"wiz_t_{trait}",
                )
            profile = {"mode": "custom"}

            if arch_changed:
                st.rerun()

        elif mode == "OCEAN":
            st.markdown('<div class="section-label">OCEAN Dimensions</div>', unsafe_allow_html=True)
            ocean_scores: dict[str, float] = {}
            for dim, (label, low, high) in OCEAN_LABELS.items():
                ocean_scores[dim] = render_labeled_slider(
                    label, low, high,
                    value=0.5, step=0.05, key=f"wiz_ocean_{dim}",
                )
            traits = ocean_to_traits(OceanProfile(**ocean_scores))
            profile = {"mode": "ocean", "ocean": ocean_scores}

        elif mode == "DISC":
            st.markdown('<div class="section-label">DISC Profile</div>', unsafe_allow_html=True)
            presets = list_disc_presets()
            preset_options = list(presets.keys()) + ["Custom..."]
            selected = st.selectbox("Preset", preset_options, key="wiz_disc_preset")

            if selected != "Custom...":
                disc_profile = get_disc_preset(selected)
                st.info(
                    f"**{selected}**: D={disc_profile.dominance}, "
                    f"I={disc_profile.influence}, S={disc_profile.steadiness}, "
                    f"C={disc_profile.conscientiousness}"
                )
                traits = disc_to_traits(disc_profile)
                profile = {"mode": "disc", "disc_preset": selected}
            else:
                disc_scores: dict[str, float] = {}
                for dim, (label, low, high) in DISC_LABELS.items():
                    disc_scores[dim] = render_labeled_slider(
                        label, low, high,
                        value=0.5, step=0.05, key=f"wiz_disc_{dim}",
                    )
                traits = disc_to_traits(DiscProfile(**disc_scores))
                profile = {"mode": "disc", "disc": disc_scores}

        elif mode == "Hybrid":
            framework = st.radio(
                "Base Framework", ["OCEAN", "DISC"],
                horizontal=True, key="wiz_hybrid_fw",
            )
            base_traits: dict[str, float] = {}
            if framework == "OCEAN":
                ocean_scores = {}
                for dim, (label, low, high) in OCEAN_LABELS.items():
                    ocean_scores[dim] = render_labeled_slider(
                        label, low, high,
                        value=0.5, step=0.05, key=f"wiz_hyb_o_{dim}",
                    )
                base_traits = ocean_to_traits(OceanProfile(**ocean_scores))
                profile = {
                    "mode": "hybrid",
                    "ocean": ocean_scores,
                    "override_priority": "explicit_wins",
                }
            else:
                disc_scores = {}
                for dim, (label, low, high) in DISC_LABELS.items():
                    disc_scores[dim] = render_labeled_slider(
                        label, low, high,
                        value=0.5, step=0.05, key=f"wiz_hyb_d_{dim}",
                    )
                base_traits = disc_to_traits(DiscProfile(**disc_scores))
                profile = {
                    "mode": "hybrid",
                    "disc": disc_scores,
                    "override_priority": "explicit_wins",
                }

            st.markdown('<div class="section-label">Trait Overrides</div>', unsafe_allow_html=True)
            for trait in TRAIT_ORDER:
                label, low, high = TRAIT_LABELS[trait]
                computed = base_traits.get(trait, 0.5)
                traits[trait] = render_labeled_slider(
                    label, low, high,
                    value=round(computed, 2),
                    step=0.05, key=f"wiz_hyb_t_{trait}",
                )

        data["traits"] = traits
        data["profile"] = profile

    with col_viz:
        st.markdown("#### Computed Traits")
        st.markdown(render_trait_bars(traits), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Step 3 — Communication
# ---------------------------------------------------------------------------


def _render_step_communication() -> None:
    data = _wiz()
    st.markdown("### Step 3: Communication Style")
    st.caption("Define how your agent communicates.")

    col_tone, col_style = st.columns(2)

    with col_tone:
        st.markdown('<div class="section-label">Tone</div>', unsafe_allow_html=True)
        data["tone"] = st.text_input(
            "Default tone",
            value=data.get("tone", "professional and helpful"),
            placeholder="e.g. professional and helpful, warm and casual",
            key="wiz_tone",
        )
        data["register"] = st.selectbox(
            "Register",
            ["intimate", "casual", "consultative", "formal", "frozen"],
            index=["intimate", "casual", "consultative", "formal", "frozen"].index(
                data.get("register", "consultative")
            ),
            key="wiz_register",
        )
        data["emoji"] = st.selectbox(
            "Emoji usage",
            ["never", "sparingly", "frequently"],
            index=["never", "sparingly", "frequently"].index(
                data.get("emoji", "sparingly")
            ),
            key="wiz_emoji",
        )

    with col_style:
        st.markdown('<div class="section-label">Style</div>', unsafe_allow_html=True)
        data["sentence_length"] = st.selectbox(
            "Sentence length",
            ["short", "mixed", "long"],
            index=["short", "mixed", "long"].index(
                data.get("sentence_length", "mixed")
            ),
            key="wiz_sentence_len",
        )
        data["use_headers"] = st.checkbox(
            "Use section headers in responses",
            value=data.get("use_headers", True),
            key="wiz_headers",
        )
        data["use_lists"] = st.checkbox(
            "Use bullet lists in responses",
            value=data.get("use_lists", True),
            key="wiz_lists",
        )

    st.divider()
    st.markdown('<div class="section-label">Vocabulary</div>', unsafe_allow_html=True)
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        data["vocab_preferred"] = st.text_area(
            "Preferred phrases (one per line)",
            value=data.get("vocab_preferred", ""),
            height=100,
            key="wiz_vocab_pref",
            placeholder="e.g.\nLet me help you with that\nGreat question",
        )
    with col_v2:
        data["vocab_avoided"] = st.text_area(
            "Avoided phrases (one per line)",
            value=data.get("vocab_avoided", ""),
            height=100,
            key="wiz_vocab_avoid",
            placeholder="e.g.\nAs an AI\nI cannot",
        )
    with col_v3:
        data["vocab_signature"] = st.text_area(
            "Signature phrases (one per line)",
            value=data.get("vocab_signature", ""),
            height=100,
            key="wiz_vocab_sig",
            placeholder="e.g.\nHappy to help!\nLet's dive in",
        )


# ---------------------------------------------------------------------------
# Step 4 — Principles & Guardrails
# ---------------------------------------------------------------------------


def _render_step_principles() -> None:
    data = _wiz()
    st.markdown("### Step 4: Principles & Guardrails")
    st.caption("Define core values and safety boundaries.")

    # --- Principles ---
    st.markdown('<div class="section-label">Core Principles</div>', unsafe_allow_html=True)
    st.caption("The guiding values for your agent (priority order).")

    principles = data.get("principles", ["Always prioritize being helpful and accurate"])

    # Render existing principles
    to_remove_p = None
    for i, p in enumerate(principles):
        col_text, col_btn = st.columns([5, 1])
        with col_text:
            new_val = st.text_input(
                f"Principle {i + 1}",
                value=p,
                key=f"wiz_prin_{i}",
                label_visibility="collapsed",
                placeholder=f"Principle {i + 1}",
            )
            principles[i] = new_val
        with col_btn:
            if len(principles) > 1 and st.button(
                "\u2716", key=f"wiz_rm_prin_{i}", help="Remove"
            ):
                to_remove_p = i

    if to_remove_p is not None:
        principles.pop(to_remove_p)
        data["principles"] = principles
        st.rerun()

    if st.button("+ Add Principle", key="wiz_add_prin"):
        principles.append("")
        data["principles"] = principles
        st.rerun()

    data["principles"] = principles

    st.divider()

    # --- Guardrails ---
    st.markdown('<div class="section-label">Hard Guardrails</div>', unsafe_allow_html=True)
    st.caption("Rules the agent must never violate.")

    guardrails = data.get("guardrails", ["Never generate harmful, illegal, or unethical content"])
    severities = data.get("guardrail_severities", {})

    to_remove_g = None
    for i, g in enumerate(guardrails):
        col_text, col_sev, col_btn = st.columns([4, 1.5, 0.5])
        with col_text:
            new_val = st.text_input(
                f"Guardrail {i + 1}",
                value=g,
                key=f"wiz_guard_{i}",
                label_visibility="collapsed",
                placeholder=f"Guardrail rule {i + 1}",
            )
            guardrails[i] = new_val
        with col_sev:
            sev_options = ["critical", "high", "medium", "low"]
            current_sev = severities.get(i, "critical")
            idx = sev_options.index(current_sev) if current_sev in sev_options else 0
            severities[i] = st.selectbox(
                "Severity",
                sev_options,
                index=idx,
                key=f"wiz_guard_sev_{i}",
                label_visibility="collapsed",
            )
        with col_btn:
            if len(guardrails) > 1 and st.button(
                "\u2716", key=f"wiz_rm_guard_{i}", help="Remove"
            ):
                to_remove_g = i

    if to_remove_g is not None:
        guardrails.pop(to_remove_g)
        # Reindex severities
        new_sev = {}
        j = 0
        for k in sorted(severities):
            if k != to_remove_g:
                new_sev[j] = severities[k]
                j += 1
        data["guardrails"] = guardrails
        data["guardrail_severities"] = new_sev
        st.rerun()

    if st.button("+ Add Guardrail", key="wiz_add_guard"):
        guardrails.append("")
        severities[len(guardrails) - 1] = "high"
        data["guardrails"] = guardrails
        data["guardrail_severities"] = severities
        st.rerun()

    data["guardrails"] = guardrails
    data["guardrail_severities"] = severities

    st.divider()

    # --- Forbidden topics ---
    st.markdown(
        '<div class="section-label">Forbidden Topics (optional)</div>',
        unsafe_allow_html=True,
    )
    data["forbidden_topics"] = st.text_area(
        "Topics the agent should never discuss (one per line)",
        value=data.get("forbidden_topics", ""),
        height=80,
        key="wiz_forbidden",
        placeholder="e.g.\nPolitics\nReligion\nCompetitor products",
        label_visibility="collapsed",
    )


# ---------------------------------------------------------------------------
# Step 5 — Expertise & Behavior
# ---------------------------------------------------------------------------


def _render_step_expertise() -> None:
    data = _wiz()
    st.markdown("### Step 5: Expertise & Behavior")
    st.caption("Define what your agent is knowledgeable about.")

    # --- Expertise Domains ---
    st.markdown('<div class="section-label">Expertise Domains</div>', unsafe_allow_html=True)

    domains = data.get("expertise_domains", [])

    to_remove = None
    for i, d in enumerate(domains):
        col_name, col_level, col_cat, col_btn = st.columns([3, 1.5, 1.5, 0.5])
        with col_name:
            d["name"] = st.text_input(
                "Domain name",
                value=d.get("name", ""),
                key=f"wiz_exp_name_{i}",
                label_visibility="collapsed",
                placeholder="e.g. Python, Data Science",
            )
        with col_level:
            d["level"] = st.slider(
                "Level",
                0.0, 1.0, d.get("level", 0.7),
                step=0.1,
                key=f"wiz_exp_level_{i}",
            )
        with col_cat:
            cats = ["primary", "secondary", "tertiary"]
            idx = cats.index(d.get("category", "primary")) if d.get("category") in cats else 0
            d["category"] = st.selectbox(
                "Category",
                cats,
                index=idx,
                key=f"wiz_exp_cat_{i}",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button("\u2716", key=f"wiz_rm_exp_{i}", help="Remove"):
                to_remove = i

    if to_remove is not None:
        domains.pop(to_remove)
        data["expertise_domains"] = domains
        st.rerun()

    if st.button("+ Add Domain", key="wiz_add_exp"):
        domains.append({"name": "", "level": 0.7, "category": "primary"})
        data["expertise_domains"] = domains
        st.rerun()

    data["expertise_domains"] = domains

    if not domains:
        st.info(
            "No expertise domains defined yet. "
            "Click **+ Add Domain** to add one, or skip this step."
        )


# ---------------------------------------------------------------------------
# Step 6 — Model & Export
# ---------------------------------------------------------------------------


def _render_step_model_export() -> None:
    data = _wiz()
    st.markdown("### Step 6: Model & Export")
    st.caption("Configure the target model and review your PersonaNexus.")

    # Try to build the identity
    try:
        identity = build_identity_from_data(data)
        compiler = SystemPromptCompiler()
        system_prompt = compiler.compile(identity)
        build_error = None
    except Exception as e:
        identity = None
        system_prompt = f"# Error building identity\n\n{e}"
        build_error = str(e)

    col_config, col_preview = st.columns([1, 1.5])

    with col_config:
        st.markdown('<div class="section-label">Target Model</div>', unsafe_allow_html=True)
        model_cfg = render_model_config(key_prefix="wiz_mc")
        data["model_config"] = model_cfg.to_dict()

        # Token estimate
        if system_prompt and not build_error:
            word_count = len(system_prompt.split())
            token_est = int(word_count * 1.3)
            st.metric("Estimated tokens", f"~{token_est:,}")

    with col_preview:
        st.markdown(
            '<div class="section-label">System Prompt Preview</div>',
            unsafe_allow_html=True,
        )

        if build_error:
            st.error(f"Build error: {build_error}")

        # Section editors
        edit_mode = st.toggle("Edit sections", value=False, key="wiz_edit_toggle")

        if edit_mode and identity and not build_error:
            # Editable section-by-section view
            _render_section_editors(identity, compiler, data)
        else:
            # Read-only compiled prompt
            st.code(system_prompt, language="markdown")

    # Export section
    st.divider()
    st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)

    name_slug = data.get("name", "agent").lower().replace(" ", "_") or "agent"

    col_d1, col_d2, col_d3, col_d4 = st.columns(4)

    with col_d1:
        st.download_button(
            "Prompt (.txt)",
            data=system_prompt,
            file_name=f"{name_slug}_prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_d2:
        if identity:
            openclaw_data = compile_identity(identity, target="openclaw")
            # Override model config with wizard selections
            openclaw_data["model_config"] = data.get("model_config", {})
            openclaw_json = json.dumps(openclaw_data, indent=2, ensure_ascii=False)
        else:
            openclaw_json = "{}"
        st.download_button(
            "OpenClaw (.json)",
            data=openclaw_json,
            file_name=f"{name_slug}.personality.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_d3:
        if identity:
            identity_yaml = yaml.dump(
                json.loads(identity.model_dump_json(exclude_none=True)),
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        else:
            identity_yaml = ""
        st.download_button(
            "Identity (.yaml)",
            data=identity_yaml,
            file_name=f"{name_slug}_identity.yaml",
            mime="text/yaml",
            use_container_width=True,
        )

    with col_d4:
        if identity:
            soul_data = compile_identity(identity, target="soul")
            soul_md = soul_data["soul_md"] + "\n\n---\n\n" + soul_data["style_md"]
        else:
            soul_md = ""
        st.download_button(
            "Soul (.md)",
            data=soul_md,
            file_name=f"{name_slug}.SOUL.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # Chat simulation
    st.divider()
    st.markdown('<div class="section-label">Chat Simulation</div>', unsafe_allow_html=True)
    _render_chat(system_prompt, model_cfg)


# ---------------------------------------------------------------------------
# Section editors (for Step 6 edit mode)
# ---------------------------------------------------------------------------


def _render_section_editors(
    identity: AgentIdentity,
    compiler: SystemPromptCompiler,
    data: dict[str, Any],
) -> None:
    """Render expandable section editors for fine-tuning the prompt."""
    overrides = st.session_state.get("wiz_section_overrides", {})

    # Role section
    with st.expander("Role & Purpose", expanded=False):
        role_text = f"## Your Role: {identity.role.title}\n\n{identity.role.purpose}"
        if identity.role.scope and identity.role.scope.primary:
            role_text += "\n\nSpecialization:\n" + "\n".join(
                f"- {s}" for s in identity.role.scope.primary
            )
        overrides["role"] = st.text_area(
            "Role section",
            value=overrides.get("role", role_text),
            height=120,
            key="wiz_edit_role",
            label_visibility="collapsed",
        )

    # Personality section (read-only)
    with st.expander("Personality (auto-generated)", expanded=False):
        st.caption("Personality is generated from your trait settings in Step 2.")
        st.markdown(render_trait_bars(data.get("traits", {})), unsafe_allow_html=True)

    # Communication section
    with st.expander("Communication Style", expanded=False):
        comm_text = f"Default tone: {data.get('tone', 'professional and helpful')}"
        if data.get("register"):
            comm_text += f"\nRegister: {data['register']}"
        if data.get("emoji"):
            comm_text += f"\nEmoji: {data['emoji']}"
        overrides["communication"] = st.text_area(
            "Communication section",
            value=overrides.get("communication", comm_text),
            height=100,
            key="wiz_edit_comm",
            label_visibility="collapsed",
        )

    # Principles section
    with st.expander("Principles", expanded=False):
        prin_text = "\n".join(
            f"{i+1}. {p}" for i, p in enumerate(data.get("principles", []))
            if p.strip()
        )
        overrides["principles"] = st.text_area(
            "Principles section",
            value=overrides.get("principles", prin_text),
            height=100,
            key="wiz_edit_prin",
            label_visibility="collapsed",
        )

    # Guardrails section
    with st.expander("Guardrails", expanded=False):
        guard_text = "CRITICAL \u2014 you must NEVER violate these:\n" + "\n".join(
            f"- {g}" for g in data.get("guardrails", []) if g.strip()
        )
        overrides["guardrails"] = st.text_area(
            "Guardrails section",
            value=overrides.get("guardrails", guard_text),
            height=100,
            key="wiz_edit_guard",
            label_visibility="collapsed",
        )

    st.session_state["wiz_section_overrides"] = overrides

    # Show compiled preview with note
    st.caption(
        "Section edits affect the **text export** only. "
        "YAML and JSON exports use structured data."
    )


# ---------------------------------------------------------------------------
# Chat simulation (reusable for Step 6)
# ---------------------------------------------------------------------------


def _render_chat(system_prompt: str, model_cfg: ModelConfig) -> None:
    """Render a chat simulation area."""
    if "wiz_messages" not in st.session_state:
        st.session_state["wiz_messages"] = []

    messages = st.session_state["wiz_messages"]

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Say something to your agent...", key="wiz_chat_input"):
        messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        reply = run_chat(system_prompt, messages, model_cfg)
        if reply:
            messages.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.write(reply)

    if messages and st.button(
        "Clear Chat", key="wiz_clear_chat", use_container_width=True
    ):
        st.session_state["wiz_messages"] = []
        st.rerun()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_step(step: int) -> bool:
    """Validate the current step. Returns True if OK to proceed."""
    data = _wiz()

    if step == 0:  # Role & Basics
        if not data.get("name", "").strip():
            st.error("Agent name is required.")
            return False
        if not data.get("purpose", "").strip():
            st.error("Purpose is required.")
            return False
        return True

    if step == 1:  # Personality
        traits = data.get("traits", {})
        non_default = [t for t, v in traits.items() if abs(v - 0.5) > 0.01]
        if len(non_default) < 2:
            st.warning(
                "Consider adjusting at least 2 traits from their "
                "default values for a more distinctive personality."
            )
        return True

    if step == 2:  # Communication
        return True  # All optional with sensible defaults

    if step == 3:  # Principles & Guardrails
        principles = [p for p in data.get("principles", []) if p.strip()]
        if not principles:
            st.error("At least one principle is required.")
            return False
        guardrails = [g for g in data.get("guardrails", []) if g.strip()]
        if not guardrails:
            st.error("At least one guardrail is required.")
            return False
        return True

    if step == 4:  # Expertise
        return True  # Optional

    return True
