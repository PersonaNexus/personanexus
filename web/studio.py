from __future__ import annotations

import html
import os
import sys
from pathlib import Path

import streamlit as st
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from components import TRAIT_COLORS, TRAIT_LABELS, TRAIT_ORDER, render_trait_bars  # noqa: E402
from studio_helpers import _compile_safe, _load_identity_safe, _studio_agent_from_yaml  # noqa: E402
from studio_model import (  # noqa: E402
    AGENTS_DIR,
    StudioAgent,
    agent_signature,
    load_studio_agents,
)

_COMPILE_FORMATS = ["text", "anthropic", "openclaw", "soul", "json", "markdown"]


def _render_agent_card(agent: StudioAgent, selected: bool) -> None:
    selected_class = " selected" if selected else ""
    tags = "".join(f"<span>{html.escape(tag)}</span>" for tag in agent.tags[:3])
    motif = html.escape(agent.motifs[0] if agent.motifs else "adaptive field")
    signature = html.escape(agent_signature(agent))
    st.markdown(
        f"""
        <div class="studio-agent-card{selected_class}">
          <div class="agent-card-topline">
            <span class="agent-status">{html.escape(agent.status)}</span>
            <span class="agent-motif">{motif}</span>
          </div>
          <div class="agent-orb">{html.escape(agent.name[:1].upper())}</div>
          <h3>{html.escape(agent.name)}</h3>
          <p class="agent-title">{html.escape(agent.title)}</p>
          <p class="agent-description">{html.escape(agent.description[:180])}</p>
          <div class="agent-tags">{tags}</div>
          <p class="agent-signature">{signature}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_canvas(agent: StudioAgent) -> None:
    top_traits = sorted(agent.traits.items(), key=lambda item: item[1], reverse=True)[:5]
    nodes = []
    for trait, score in top_traits:
        color = TRAIT_COLORS.get(trait, "#8b5cf6")
        label = TRAIT_LABELS.get(trait, (trait, "", ""))[0]
        node_size = 56 + score * 46
        nodes.append(
            f"<div class='canvas-node' style='--node-color:{color};"
            f"--node-size:{node_size:.0f}px'>"
            f"<strong>{html.escape(label)}</strong><span>{score:.2f}</span></div>"
        )

    principles = "".join(
        f"<li>{html.escape(principle)}</li>" for principle in agent.principles[:3]
    ) or "<li>Principles appear here as this persona is authored.</li>"
    motif_chips = "".join(
        f"<span>{html.escape(motif)}</span>" for motif in agent.motifs
    )

    st.markdown(
        f"""
        <section class="studio-canvas-shell">
          <div class="canvas-hero">
            <div>
              <p class="eyebrow">Live persona canvas</p>
              <h2>{html.escape(agent.name)}</h2>
              <p>{html.escape(agent.title)}</p>
            </div>
            <div class="canvas-orb-wrap">
              <div class="canvas-orb-core">{html.escape(agent.name[:1].upper())}</div>
            </div>
          </div>
          <div class="canvas-field">{''.join(nodes)}</div>
          <div class="canvas-motifs">{motif_chips}</div>
          <div class="canvas-principles"><h4>Behavioral contract</h4><ul>{principles}</ul></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_compile_preview(agent: StudioAgent, agents_dir: Path) -> None:
    """Show compiled system-prompt output for the selected agent."""
    with st.expander("Compile preview", expanded=False):
        fmt = st.selectbox(
            "Target format",
            _COMPILE_FORMATS,
            key=f"compile_fmt_{agent.slug}",
        )
        agent_path = agents_dir / f"{agent.slug}.yaml"
        if agent.slug == "__custom__":
            raw_yaml = st.session_state.get("studio_custom_yaml", "")
            if not raw_yaml:
                st.info("Upload a YAML file above to compile it.")
                return
            try:
                data = yaml.safe_load(raw_yaml)
                from personanexus.types import AgentIdentity
                identity = AgentIdentity.model_validate(data)
                err = None
            except Exception as exc:  # noqa: BLE001
                identity, err = None, str(exc)
        elif agent_path.exists():
            identity, err = _load_identity_safe(agent_path)
        else:
            st.warning(f"Identity file not found: {agent_path.name}")
            return

        if err:
            st.error(f"Parse error: {err}")
            return

        compiled, cerr = _compile_safe(identity, fmt)
        if cerr:
            st.error(f"Compile error: {cerr}")
            return

        lang = "json" if fmt in ("openclaw", "json", "soul") else "markdown"
        st.code(compiled, language=lang)
        st.download_button(
            label=f"Download compiled ({fmt})",
            data=compiled,
            file_name=f"{agent.slug}_{fmt}.{'json' if lang == 'json' else 'txt'}",
            mime="application/json" if lang == "json" else "text/plain",
            key=f"dl_compiled_{agent.slug}_{fmt}",
            use_container_width=True,
        )


def _render_export_panel(agent: StudioAgent, agents_dir: Path) -> None:
    """Export buttons for raw YAML and all compiled formats."""
    st.markdown("#### Export persona")

    agent_path = agents_dir / f"{agent.slug}.yaml"
    is_custom = agent.slug == "__custom__"

    raw_yaml = (
        st.session_state.get("studio_custom_yaml", "")
        if is_custom
        else (agent_path.read_text(encoding="utf-8") if agent_path.exists() else "")
    )

    if not raw_yaml:
        st.caption("No source YAML available for export.")
        return

    cols = st.columns(4)
    with cols[0]:
        st.download_button(
            label="Identity (.yaml)",
            data=raw_yaml,
            file_name=f"{agent.slug}_identity.yaml",
            mime="text/yaml",
            key=f"dl_yaml_{agent.slug}",
            use_container_width=True,
        )

    if agent_path.exists() or is_custom:
        if is_custom:
            try:
                from personanexus.types import AgentIdentity
                identity = AgentIdentity.model_validate(yaml.safe_load(raw_yaml))
                load_err = None
            except Exception as exc:  # noqa: BLE001
                identity, load_err = None, str(exc)
        else:
            identity, load_err = _load_identity_safe(agent_path)

        if load_err or identity is None:
            st.caption(f"Could not load identity for compiled exports: {load_err}")
            return

        export_targets = [
            ("Prompt (.txt)", "text", "text/plain", "txt"),
            ("Anthropic (.txt)", "anthropic", "text/plain", "txt"),
            ("OpenClaw (.json)", "openclaw", "application/json", "json"),
        ]
        for i, (label, fmt, mime, ext) in enumerate(export_targets):
            compiled, cerr = _compile_safe(identity, fmt)
            if cerr or compiled is None:
                continue
            with cols[i + 1]:
                st.download_button(
                    label=label,
                    data=compiled,
                    file_name=f"{agent.slug}_{fmt}.{ext}",
                    mime=mime,
                    key=f"dl_{fmt}_{agent.slug}",
                    use_container_width=True,
                )


def _render_load_panel(agents: list[StudioAgent]) -> StudioAgent | None:
    """File uploader for loading a custom agent YAML draft. Returns a draft agent or None."""
    with st.expander("Load custom agent YAML", expanded=False):
        uploaded = st.file_uploader(
            "Upload a PersonaNexus identity YAML",
            type=["yaml", "yml"],
            key="studio_yaml_uploader",
        )
        if uploaded is not None:
            raw = uploaded.read().decode("utf-8")
            try:
                data = yaml.safe_load(raw)
            except yaml.YAMLError as exc:
                st.error(f"YAML parse error: {exc}")
                return None
            slug = Path(uploaded.name).stem or "custom"
            if slug in {a.slug for a in agents}:
                slug = f"{slug}_draft"
            try:
                draft = _studio_agent_from_yaml(data, slug="__custom__")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not build agent from YAML: {exc}")
                return None
            st.session_state["studio_custom_yaml"] = raw
            st.success(f"Loaded draft: **{draft.name}** — click Open below to inspect.")
            return draft
        return None


def render_studio() -> None:
    """Render the Studio mode."""
    agents = load_studio_agents()
    if not agents:
        st.warning("No agents found yet. Add YAML identities to the agents directory.")
        return

    if "studio_selected_agent" not in st.session_state:
        st.session_state["studio_selected_agent"] = agents[0].slug

    st.markdown(
        """
        <div class="studio-hero">
          <p class="eyebrow">PersonaNexus Studio</p>
          <h1>Design agents you can see, compare, and feel.</h1>
          <p>
            A premium workspace for browsing persona identities, inspecting their
            behavioral shape, and turning personality into an interactive artifact.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    draft_agent = _render_load_panel(agents)
    all_agents = agents if draft_agent is None else [draft_agent, *agents]

    selected_slug = st.session_state["studio_selected_agent"]
    selected_agent = next((a for a in all_agents if a.slug == selected_slug), all_agents[0])

    metric_cols = st.columns(4)
    motif_count = len({motif for agent in agents for motif in agent.motifs})
    metric_cols[0].metric("Agents", len(agents))
    metric_cols[1].metric("Visual motifs", motif_count)
    metric_cols[2].metric("Traits", len(TRAIT_ORDER))
    metric_cols[3].metric("Canvas", "Live")

    st.markdown("### Agent gallery")
    gallery_cols = st.columns(3)
    for index, agent in enumerate(all_agents):
        with gallery_cols[index % 3]:
            _render_agent_card(agent, selected=agent.slug == selected_agent.slug)
            if st.button(
                f"Open {agent.name}",
                key=f"studio_open_{agent.slug}",
                use_container_width=True,
            ):
                st.session_state["studio_selected_agent"] = agent.slug
                st.rerun()

    st.markdown("### Visual canvas")
    canvas_col, inspector_col = st.columns([1.35, 0.9], gap="large")
    with canvas_col:
        _render_canvas(selected_agent)
    with inspector_col:
        st.markdown(f"#### {selected_agent.name} trait spectrum")
        st.markdown(render_trait_bars(selected_agent.traits), unsafe_allow_html=True)
        st.markdown("#### Motif controls")
        st.caption(
            "First slice: motifs are generated from dominant traits; "
            "future editor work will make these controls editable."
        )
        for motif in selected_agent.motifs:
            st.toggle(motif.title(), value=True, key=f"motif_{selected_agent.slug}_{motif}")
        st.markdown("#### Personality packet")
        st.json(
            {
                "name": selected_agent.name,
                "tone": selected_agent.tone,
                "motifs": selected_agent.motifs,
                "traits": selected_agent.traits,
            }
        )
        _render_compile_preview(selected_agent, AGENTS_DIR)

    st.divider()
    _render_export_panel(selected_agent, AGENTS_DIR)
