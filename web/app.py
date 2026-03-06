"""PersonaNexus Lab — Interactive personality design and simulation.

A Streamlit-based UI for designing AI agent personalities using the
personanexus framework. Supports a quick Playground mode and a full
Setup Wizard with multi-step guided identity building.
"""

import html
import json
import logging
import os
import sys

import streamlit as st
import yaml

logger = logging.getLogger(__name__)

# Add src and web to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from components import (  # noqa: E402
    APP_CSS,
    ARCHETYPE_DEFAULTS,
    DISC_LABELS,
    OCEAN_LABELS,
    TRAIT_LABELS,
    TRAIT_ORDER,
    render_labeled_slider,
    render_trait_bars,
)

from personanexus.compiler import SystemPromptCompiler, compile_identity  # noqa: E402
from personanexus.personality import (  # noqa: E402
    disc_to_traits,
    get_disc_preset,
    list_disc_presets,
    ocean_to_traits,
)
from personanexus.types import (  # noqa: E402
    AgentIdentity,
    DiscProfile,
    OceanProfile,
)

# ---------------------------------------------------------------------------
# Page config & styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PersonaNexus Lab",
    layout="wide",
    page_icon="🧬",
    initial_sidebar_state="auto",
)

st.markdown(APP_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------


def _render_landing() -> None:
    """Render a clean landing page with three mode-selection cards."""
    st.markdown(
        "<div style='text-align:center;padding:3rem 0 1.5rem 0'>"
        "<h1 style='font-size:2.5rem;font-weight:700;color:#1a1a2e;margin:0'>"
        "🧬 Identity Lab"
        "</h1>"
        "<p style='font-size:1.1rem;color:#4a5568;margin-top:0.5rem'>"
        "Design AI Agent Personalities"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_play, col_wiz, col_analyze = st.columns(3)

    with col_play:
        st.markdown(
            '<div class="landing-card">'
            '<div class="icon">⚡</div>'
            "<h3>Playground</h3>"
            "<p>Quick personality exploration. Adjust traits, preview "
            "system prompts, and experiment with different frameworks.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Open Playground",
            key="landing_playground",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["app_mode"] = "Playground"
            st.rerun()

    with col_wiz:
        st.markdown(
            '<div class="landing-card">'
            '<div class="icon">🧙</div>'
            "<h3>Setup Wizard</h3>"
            "<p>Guided identity builder. Walk through 6 steps to create "
            "a complete PersonaNexus with export.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Start Wizard",
            key="landing_wizard",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state["app_mode"] = "Setup Wizard"
            st.rerun()

    with col_analyze:
        st.markdown(
            '<div class="landing-card">'
            '<div class="icon">🔬</div>'
            "<h3>Analyze</h3>"
            "<p>Upload a SOUL.md, personality.json, or YAML file to "
            "map it onto personality frameworks and compare agents.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Start Analysis",
            key="landing_analyze",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state["app_mode"] = "Analyze"
            st.rerun()


# ---------------------------------------------------------------------------
# Mode routing
# ---------------------------------------------------------------------------

app_mode = st.session_state.get("app_mode")

if app_mode is None:
    _render_landing()
    st.stop()

# "Home" button when inside a mode
if st.button("← Home", key="nav_home"):
    st.session_state["app_mode"] = None
    # Clear wizard state so landing page is clean
    for k in list(st.session_state.keys()):
        if k.startswith("wiz_") or k.startswith("_wiz_"):
            del st.session_state[k]
    if "wizard_data" in st.session_state:
        del st.session_state["wizard_data"]
    if "wizard_step" in st.session_state:
        del st.session_state["wizard_step"]
    st.rerun()

if app_mode == "Setup Wizard":
    try:
        from wizard import render_wizard
        render_wizard()
    except Exception as e:
        st.error("An error occurred while loading the wizard. Check logs for details.")
        logger.exception("Wizard error: %s", e)
    st.stop()

if app_mode == "Analyze":
    try:
        from analyze import render_analyze
        render_analyze()
    except Exception as e:
        st.error("An error occurred while loading the analyzer. Check logs for details.")
        logger.exception("Analyze error: %s", e)
    st.stop()


# ---------------------------------------------------------------------------
# Playground Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="main-header">🧬 Playground</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Quick personality exploration</div>',
        unsafe_allow_html=True,
    )

    # -- Personality mode --
    st.markdown('<div class="section-label">Personality Framework</div>', unsafe_allow_html=True)
    mode = st.radio(
        "Mode",
        ["Custom", "OCEAN", "DISC", "Hybrid"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # -- Archetype preset (for Custom mode) --
    if mode == "Custom":
        st.markdown('<div class="section-label">Archetype Preset</div>', unsafe_allow_html=True)

        # Initialise archetype tracking on first run
        if "_last_archetype" not in st.session_state:
            st.session_state["_last_archetype"] = "Blank Slate"

        archetype = st.selectbox(
            "Archetype",
            list(ARCHETYPE_DEFAULTS.keys()),
            label_visibility="collapsed",
        )
        defaults = ARCHETYPE_DEFAULTS[archetype]

        # Detect archetype change and apply new defaults on next rerun
        archetype_changed = st.session_state.get("_last_archetype") != archetype
        if archetype_changed:
            st.session_state["_last_archetype"] = archetype
            st.session_state["_apply_archetype"] = archetype

        # Apply pending archetype defaults before widget creation
        if st.session_state.pop("_apply_archetype", None):
            defaults_to_apply = ARCHETYPE_DEFAULTS[archetype]
            for trait in TRAIT_ORDER:
                st.session_state[f"custom_{trait}"] = defaults_to_apply.get(trait, 0.5)
    else:
        defaults = ARCHETYPE_DEFAULTS["Blank Slate"]

    # -- Mode-specific inputs --
    traits_dict: dict[str, float] = {}
    profile_dict: dict = {}

    if mode == "Custom":
        st.markdown('<div class="section-label">Personality Traits</div>', unsafe_allow_html=True)
        for trait in TRAIT_ORDER:
            label, low, high = TRAIT_LABELS[trait]
            traits_dict[trait] = render_labeled_slider(
                label, low, high,
                value=defaults.get(trait, 0.5),
                step=0.05,
                key=f"custom_{trait}",
            )
        profile_dict = {"mode": "custom"}

        # Trigger rerun after archetype change so sliders pick up new session state
        if archetype_changed:
            st.rerun()

    elif mode == "OCEAN":
        st.markdown(
            '<div class="section-label">OCEAN (Big Five) Dimensions</div>',
            unsafe_allow_html=True,
        )
        ocean_scores: dict[str, float] = {}
        for dim, (label, low, high) in OCEAN_LABELS.items():
            ocean_scores[dim] = render_labeled_slider(
                label, low, high,
                value=0.5, step=0.05, key=f"ocean_{dim}",
            )
        traits_dict = ocean_to_traits(OceanProfile(**ocean_scores))
        profile_dict = {"mode": "ocean", "ocean": ocean_scores}

    elif mode == "DISC":
        st.markdown('<div class="section-label">DISC Profile</div>', unsafe_allow_html=True)
        presets = list_disc_presets()
        preset_options = list(presets.keys()) + ["Custom..."]
        selected = st.selectbox("Preset", preset_options, key="disc_preset")

        if selected != "Custom...":
            disc_profile = get_disc_preset(selected)
            st.info(
                f"**{selected}**: D={disc_profile.dominance}, "
                f"I={disc_profile.influence}, S={disc_profile.steadiness}, "
                f"C={disc_profile.conscientiousness}"
            )
            traits_dict = disc_to_traits(disc_profile)
            profile_dict = {"mode": "disc", "disc_preset": selected}
        else:
            disc_scores: dict[str, float] = {}
            for dim, (label, low, high) in DISC_LABELS.items():
                disc_scores[dim] = render_labeled_slider(
                    label, low, high,
                    value=0.5, step=0.05, key=f"disc_{dim}",
                )
            traits_dict = disc_to_traits(DiscProfile(**disc_scores))
            profile_dict = {"mode": "disc", "disc": disc_scores}

    elif mode == "Hybrid":
        st.markdown('<div class="section-label">Base Framework</div>', unsafe_allow_html=True)
        framework = st.radio(
            "Framework", ["OCEAN", "DISC"], horizontal=True,
            label_visibility="collapsed", key="hybrid_framework",
        )

        base_traits: dict[str, float] = {}
        if framework == "OCEAN":
            ocean_scores = {}
            for dim, (label, low, high) in OCEAN_LABELS.items():
                ocean_scores[dim] = render_labeled_slider(
                    label, low, high,
                    value=0.5, step=0.05, key=f"hybrid_ocean_{dim}",
                )
            base_traits = ocean_to_traits(OceanProfile(**ocean_scores))
            profile_dict = {
                "mode": "hybrid",
                "ocean": ocean_scores,
                "override_priority": "explicit_wins",
            }
        else:
            disc_scores = {}
            for dim, (label, low, high) in DISC_LABELS.items():
                disc_scores[dim] = render_labeled_slider(
                    label, low, high,
                    value=0.5, step=0.05, key=f"hybrid_disc_{dim}",
                )
            base_traits = disc_to_traits(DiscProfile(**disc_scores))
            profile_dict = {
                "mode": "hybrid",
                "disc": disc_scores,
                "override_priority": "explicit_wins",
            }

        st.markdown('<div class="section-label">Trait Overrides</div>', unsafe_allow_html=True)
        st.caption("Adjust any trait to override the computed value")
        for trait in TRAIT_ORDER:
            label, low, high = TRAIT_LABELS[trait]
            computed_val = base_traits.get(trait, 0.5)
            traits_dict[trait] = render_labeled_slider(
                label, low, high,
                value=round(computed_val, 2),
                step=0.05,
                key=f"hybrid_trait_{trait}",
            )

    # -- Role definition --
    st.markdown('<div class="section-label">Role Definition</div>', unsafe_allow_html=True)
    role_title = st.text_input("Role Title", value="AI Assistant", key="role_title")
    role_purpose = st.text_area(
        "Purpose", value="To help users achieve their goals efficiently.",
        height=80, key="role_purpose",
    )


# ---------------------------------------------------------------------------
# Build identity & compile
# ---------------------------------------------------------------------------


def build_identity(
    traits: dict[str, float],
    profile: dict,
    title: str,
    purpose: str,
) -> AgentIdentity:
    """Build a real AgentIdentity from UI values."""
    personality_data: dict = {"traits": traits}
    if profile.get("mode") != "custom":
        personality_data["profile"] = profile

    identity_data = {
        "schema_version": "1.0",
        "metadata": {
            "id": "agt_identity_lab_001",
            "name": title,
            "version": "1.0.0",
            "description": purpose,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "draft",
        },
        "role": {
            "title": title,
            "purpose": purpose,
            "scope": {"primary": ["General assistance"]},
        },
        "personality": personality_data,
        "communication": {
            "tone": {"default": "professional and helpful"},
        },
        "principles": [
            {
                "id": "be_helpful",
                "priority": 1,
                "statement": "Always prioritize being helpful and accurate",
            },
            {
                "id": "be_safe",
                "priority": 2,
                "statement": "Never generate harmful or misleading content",
            },
        ],
        "guardrails": {
            "hard": [
                {
                    "id": "no_harmful_content",
                    "rule": "Never generate harmful, illegal, or unethical content",
                    "enforcement": "output_filter",
                    "severity": "critical",
                },
            ],
        },
    }
    return AgentIdentity.model_validate(identity_data)


# Build identity
try:
    identity = build_identity(traits_dict, profile_dict, role_title, role_purpose)
    compiler = SystemPromptCompiler()
    system_prompt = compiler.compile(identity)
    build_error = None
except Exception as e:
    system_prompt = f"# Error building identity\n\n{e}"
    identity = None
    build_error = str(e)


# ---------------------------------------------------------------------------
# Trait visualization helper
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.markdown(f'<div class="main-header">🧬 {html.escape(role_title)}</div>', unsafe_allow_html=True)

mode_badge = {
    "Custom": "Custom Traits",
    "OCEAN": "OCEAN (Big Five)",
    "DISC": "DISC",
    "Hybrid": "Hybrid",
}
badge_text = html.escape(mode_badge[mode])
st.markdown(
    f'<div class="sub-header">Personality Mode: '
    f"<strong>{badge_text}</strong></div>",
    unsafe_allow_html=True,
)

if build_error:
    st.error(f"Identity build error: {build_error}")

# -- Trait visualization --
st.markdown("#### Computed Personality Traits")
st.markdown(render_trait_bars(traits_dict), unsafe_allow_html=True)

st.divider()

# -- Two-column layout --
col_preview, col_chat = st.columns([1, 1])

with col_preview:
    st.markdown("#### System Prompt Preview")
    st.code(system_prompt, language="markdown")

    # Export buttons
    st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)
    col_dl1, col_dl2, col_dl3, col_dl4 = st.columns(4)

    with col_dl1:
        st.download_button(
            label="Prompt (.txt)",
            data=system_prompt,
            file_name=f"{role_title.lower().replace(' ', '_')}_prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_dl2:
        # OpenClaw JSON export
        if identity:
            openclaw_data = compile_identity(identity, target="openclaw")
            openclaw_json = json.dumps(openclaw_data, indent=2, ensure_ascii=False)
        else:
            openclaw_json = "{}"
        st.download_button(
            label="OpenClaw (.json)",
            data=openclaw_json,
            file_name=f"{role_title.lower().replace(' ', '_')}.personality.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_dl3:
        # SOUL.md export
        if identity:
            soul_data = compile_identity(identity, target="soul")
            soul_md = soul_data["soul_md"] + "\n\n---\n\n" + soul_data["style_md"]
        else:
            soul_md = ""
        st.download_button(
            label="Soul (.md)",
            data=soul_md,
            file_name=f"{role_title.lower().replace(' ', '_')}.SOUL.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col_dl4:
        # YAML identity spec export
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
            label="Identity (.yaml)",
            data=identity_yaml,
            file_name=f"{role_title.lower().replace(' ', '_')}_identity.yaml",
            mime="text/yaml",
            use_container_width=True,
        )

with col_chat:
    st.markdown("#### Chat Simulation")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Say something to your agent..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Call OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                    ] + st.session_state.messages,
                    temperature=0.7,
                )
                reply = response.choices[0].message.content
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )
                with st.chat_message("assistant"):
                    st.write(reply)
            except Exception as e:
                st.error(f"Chat error: {e}")
        else:
            st.info(
                "Set the `OPENAI_API_KEY` environment variable to enable "
                "live chat simulation with GPT-4o."
            )

    # Clear chat button
    if st.session_state.messages and st.button(
        "Clear Chat", use_container_width=True
    ):
        st.session_state.messages = []
        st.rerun()
