"""Soul Analysis panel — Upload and analyze agent personality files.

Accepts SOUL.md, personality.json, or personanexus YAML files and
maps them to all three personality frameworks (traits, OCEAN, DISC).
"""

from __future__ import annotations

import html
import json
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

# Add src to path so we can import the library
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from components import (
    DISC_LABELS,
    OCEAN_LABELS,
    render_comparison_bars,
    render_confidence_badge,
    render_disc_bars,
    render_ocean_bars,
    render_trait_bars,
)

from personanexus.analyzer import AnalyzerError, SoulAnalyzer


def render_analyze() -> None:
    """Render the soul analysis panel."""
    st.markdown(
        '<div class="main-header">🔬 Soul Analysis</div>'
        '<div class="sub-header">Upload a personality file to analyze traits and framework mappings</div>',
        unsafe_allow_html=True,
    )

    # --- File uploads ---
    col_up1, col_up2 = st.columns(2)

    with col_up1:
        st.markdown("**Primary file**")
        file_a = st.file_uploader(
            "Upload a SOUL.md, personality.json, or identity YAML",
            type=["md", "json", "yaml", "yml"],
            key="analyze_file_a",
            label_visibility="collapsed",
        )

    with col_up2:
        st.markdown("**Comparison file** *(optional)*")
        file_b = st.file_uploader(
            "Upload a second file for comparison",
            type=["md", "json", "yaml", "yml"],
            key="analyze_file_b",
            label_visibility="collapsed",
        )

    if not file_a:
        st.info("Upload a SOUL.md, personality.json, or personanexus YAML file to get started.")
        return

    # --- Analyze primary file ---
    analyzer = SoulAnalyzer()

    result_a = _analyze_uploaded(analyzer, file_a)
    if result_a is None:
        return

    result_b = None
    if file_b:
        result_b = _analyze_uploaded(analyzer, file_b)

    # --- Display results ---
    if result_b:
        _render_comparison(analyzer, result_a, result_b)
    else:
        _render_single(result_a)


def _analyze_uploaded(analyzer: SoulAnalyzer, uploaded_file) -> AnalysisResult | None:
    """Write uploaded file to temp dir and analyze it."""

    try:
        with tempfile.TemporaryDirectory() as tmp:
            # Sanitize filename: strip directory components to prevent path traversal
            safe_name = Path(uploaded_file.name).name
            if not safe_name:
                safe_name = "upload.yaml"
            tmp_path = Path(tmp) / safe_name
            tmp_path.write_bytes(uploaded_file.getvalue())
            return analyzer.analyze(tmp_path)
    except AnalyzerError as exc:
        st.error(f"Analysis failed: {exc}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None


def _render_single(result) -> None:
    """Render analysis for a single file."""
    name = result.agent_name or "Unknown Agent"
    fmt = result.source_format.value.replace("_", " ").title()

    # Header with confidence badge
    st.markdown(
        f"### {html.escape(name)}  "
        f'<span style="font-size: 0.85rem; color: #586069;">({html.escape(fmt)})</span>  '
        + render_confidence_badge(result.confidence),
        unsafe_allow_html=True,
    )

    # Tabs
    tab_traits, tab_ocean, tab_disc, tab_raw = st.tabs(
        ["Traits", "OCEAN (Big Five)", "DISC Profile", "Raw Data"]
    )

    traits_dict = result.traits.defined_traits()
    ocean_dict = result.ocean.model_dump()
    disc_dict = result.disc.model_dump()

    with tab_traits:
        st.markdown("#### Personality Traits")
        st.markdown(render_trait_bars(traits_dict), unsafe_allow_html=True)

        # Per-trait confidence details
        with st.expander("Extraction details"):
            for ext in result.trait_extractions:
                conf_color = "#10b981" if ext.confidence >= 0.8 else "#f59e0b" if ext.confidence >= 0.5 else "#ef4444"
                source = f' — *{ext.source_text}*' if ext.source_text else ""
                st.markdown(
                    f"- **{ext.name}**: {ext.value:.2f} "
                    f'<span style="color: {conf_color};">({ext.confidence:.0%})</span>'
                    f"{source}",
                    unsafe_allow_html=True,
                )

    with tab_ocean:
        st.markdown("#### OCEAN (Big Five) Profile")
        st.markdown(render_ocean_bars(ocean_dict), unsafe_allow_html=True)
        st.caption("Reverse-mapped from extracted traits using weighted-sum approximation.")

        # Dimension descriptions
        with st.expander("Dimension details"):
            for dim, (label, low, high) in OCEAN_LABELS.items():
                val = ocean_dict[dim]
                st.markdown(f"- **{label}** ({val:.3f}): {low} ← → {high}")

    with tab_disc:
        st.markdown("#### DISC Profile")
        st.markdown(render_disc_bars(disc_dict), unsafe_allow_html=True)

        if result.closest_preset:
            preset = result.closest_preset
            label = preset.preset_name.replace("_", " ").title()
            dist_color = "#10b981" if preset.distance < 0.3 else "#f59e0b" if preset.distance < 0.6 else "#ef4444"
            st.markdown(
                f'**Closest preset:** {label} '
                f'<span style="color: {dist_color};">(distance: {preset.distance:.3f})</span>',
                unsafe_allow_html=True,
            )

        st.caption("Reverse-mapped from extracted traits using weighted-sum approximation.")

        with st.expander("Dimension details"):
            for dim, (label, low, high) in DISC_LABELS.items():
                val = disc_dict[dim]
                st.markdown(f"- **{label}** ({val:.3f}): {low} ← → {high}")

    with tab_raw:
        st.markdown("#### Analysis Result (JSON)")
        st.json(json.loads(result.model_dump_json()))


def _render_comparison(analyzer, result_a, result_b) -> None:
    """Render side-by-side comparison of two analysis results."""
    comparison = analyzer.compare(result_a, result_b)

    name_a = result_a.agent_name or "File A"
    name_b = result_b.agent_name or "File B"

    st.markdown(
        f"### {name_a} vs {name_b}  "
        f'<span style="font-size: 0.9rem; color: #586069;">'
        f"Similarity: {comparison.similarity_score:.1%}</span>",
        unsafe_allow_html=True,
    )

    # Comparison tabs
    tab_traits, tab_ocean, tab_disc, tab_details = st.tabs(
        ["Trait Comparison", "OCEAN Comparison", "DISC Comparison", "Individual Details"]
    )

    traits_a = result_a.traits.defined_traits()
    traits_b = result_b.traits.defined_traits()

    with tab_traits:
        st.markdown("#### Trait Comparison")
        st.markdown(
            render_comparison_bars(traits_a, traits_b, name_a, name_b),
            unsafe_allow_html=True,
        )

    with tab_ocean:
        st.markdown("#### OCEAN Comparison")
        ocean_a = result_a.ocean.model_dump()
        ocean_b = result_b.ocean.model_dump()
        col_oa, col_ob = st.columns(2)
        with col_oa:
            st.markdown(f"**{name_a}**")
            st.markdown(render_ocean_bars(ocean_a), unsafe_allow_html=True)
        with col_ob:
            st.markdown(f"**{name_b}**")
            st.markdown(render_ocean_bars(ocean_b), unsafe_allow_html=True)

        # Delta table
        st.markdown("**Deltas**")
        delta_parts = []
        for dim in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
            d = comparison.ocean_deltas[dim]
            color = "#10b981" if abs(d) < 0.05 else "#f59e0b" if abs(d) < 0.15 else "#ef4444"
            sign = "+" if d > 0 else ""
            label = OCEAN_LABELS[dim][0]
            delta_parts.append(
                f'<span style="margin-right: 16px;">{label}: '
                f'<span style="color: {color}; font-family: monospace;">{sign}{d:.3f}</span></span>'
            )
        st.markdown("".join(delta_parts), unsafe_allow_html=True)

    with tab_disc:
        st.markdown("#### DISC Comparison")
        disc_a = result_a.disc.model_dump()
        disc_b = result_b.disc.model_dump()
        col_da, col_db = st.columns(2)
        with col_da:
            st.markdown(f"**{name_a}**")
            st.markdown(render_disc_bars(disc_a), unsafe_allow_html=True)
            if result_a.closest_preset:
                label = result_a.closest_preset.preset_name.replace("_", " ").title()
                st.caption(f"Closest: {label}")
        with col_db:
            st.markdown(f"**{name_b}**")
            st.markdown(render_disc_bars(disc_b), unsafe_allow_html=True)
            if result_b.closest_preset:
                label = result_b.closest_preset.preset_name.replace("_", " ").title()
                st.caption(f"Closest: {label}")

    with tab_details:
        st.markdown("#### Individual Results")
        col_ia, col_ib = st.columns(2)
        with col_ia:
            st.markdown(f"**{name_a}**")
            st.markdown(render_trait_bars(traits_a), unsafe_allow_html=True)
            st.markdown(
                "Confidence: " + render_confidence_badge(result_a.confidence),
                unsafe_allow_html=True,
            )
        with col_ib:
            st.markdown(f"**{name_b}**")
            st.markdown(render_trait_bars(traits_b), unsafe_allow_html=True)
            st.markdown(
                "Confidence: " + render_confidence_badge(result_b.confidence),
                unsafe_allow_html=True,
            )
