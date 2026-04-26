from __future__ import annotations

import html

import streamlit as st
from components import TRAIT_COLORS, TRAIT_LABELS, TRAIT_ORDER, render_trait_bars
from studio_model import StudioAgent, agent_signature, load_studio_agents


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


def render_studio() -> None:
    """Render the Studio mode."""
    agents = load_studio_agents()
    if not agents:
        st.warning("No agents found yet. Add YAML identities to the agents directory.")
        return

    if "studio_selected_agent" not in st.session_state:
        st.session_state["studio_selected_agent"] = agents[0].slug

    selected_slug = st.session_state["studio_selected_agent"]
    selected_agent = next((agent for agent in agents if agent.slug == selected_slug), agents[0])

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

    metric_cols = st.columns(4)
    motif_count = len({motif for agent in agents for motif in agent.motifs})
    metric_cols[0].metric("Agents", len(agents))
    metric_cols[1].metric("Visual motifs", motif_count)
    metric_cols[2].metric("Traits", len(TRAIT_ORDER))
    metric_cols[3].metric("Canvas", "Live")

    st.markdown("### Agent gallery")
    gallery_cols = st.columns(3)
    for index, agent in enumerate(agents):
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
