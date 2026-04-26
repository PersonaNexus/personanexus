"""Shared UI components for the PersonaNexus Lab.

Constants, trait visualization, progress bar, and identity building
utilities used by both the Playground and Setup Wizard modes.
"""

from __future__ import annotations

import html
import os
import sys
from datetime import UTC, datetime
from typing import Any

import streamlit as st

# Add src to path so we can import the library
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from personanexus.types import (
    AgentIdentity,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRAIT_ORDER = [
    "warmth", "verbosity", "assertiveness", "humor", "empathy",
    "directness", "rigor", "creativity", "epistemic_humility", "patience",
]

TRAIT_LABELS = {
    "warmth": ("Warmth", "Cold", "Friendly"),
    "verbosity": ("Verbosity", "Brief", "Detailed"),
    "assertiveness": ("Assertiveness", "Passive", "Directive"),
    "humor": ("Humor", "Serious", "Witty"),
    "empathy": ("Empathy", "Task-focused", "Empathetic"),
    "directness": ("Directness", "Diplomatic", "Direct"),
    "rigor": ("Rigor", "Flexible", "Precise"),
    "creativity": ("Creativity", "Conventional", "Innovative"),
    "epistemic_humility": ("Epistemic Humility", "Confident", "Humble"),
    "patience": ("Patience", "Fast-paced", "Patient"),
}

OCEAN_LABELS = {
    "openness": ("Openness", "Conventional", "Exploratory"),
    "conscientiousness": ("Conscientiousness", "Flexible", "Organized"),
    "extraversion": ("Extraversion", "Reserved", "Outgoing"),
    "agreeableness": ("Agreeableness", "Challenging", "Cooperative"),
    "neuroticism": ("Neuroticism", "Calm", "Reactive"),
}

DISC_LABELS = {
    "dominance": ("Dominance", "Accommodating", "Assertive"),
    "influence": ("Influence", "Reserved", "Enthusiastic"),
    "steadiness": ("Steadiness", "Dynamic", "Patient"),
    "conscientiousness": ("Conscientiousness", "Flexible", "Precise"),
}

ARCHETYPE_DEFAULTS = {
    "Blank Slate": dict.fromkeys(TRAIT_ORDER, 0.5),
    "Analyst": {
        "warmth": 0.4, "verbosity": 0.6, "assertiveness": 0.5, "humor": 0.2,
        "empathy": 0.4, "directness": 0.7, "rigor": 0.9, "creativity": 0.4,
        "epistemic_humility": 0.8, "patience": 0.7,
    },
    "Tutor": {
        "warmth": 0.8, "verbosity": 0.7, "assertiveness": 0.4, "humor": 0.4,
        "empathy": 0.8, "directness": 0.5, "rigor": 0.6, "creativity": 0.6,
        "epistemic_humility": 0.7, "patience": 0.9,
    },
    "Support": {
        "warmth": 0.8, "verbosity": 0.5, "assertiveness": 0.3, "humor": 0.3,
        "empathy": 0.9, "directness": 0.4, "rigor": 0.5, "creativity": 0.3,
        "epistemic_humility": 0.6, "patience": 0.8,
    },
}

TRAIT_COLORS = {
    "warmth": "#e8a838",
    "verbosity": "#6366f1",
    "assertiveness": "#ef4444",
    "humor": "#f59e0b",
    "empathy": "#ec4899",
    "directness": "#f97316",
    "rigor": "#3b82f6",
    "creativity": "#8b5cf6",
    "epistemic_humility": "#06b6d4",
    "patience": "#10b981",
}

OCEAN_COLORS = {
    "openness": "#8b5cf6",
    "conscientiousness": "#3b82f6",
    "extraversion": "#f59e0b",
    "agreeableness": "#10b981",
    "neuroticism": "#ef4444",
}

DISC_COLORS = {
    "dominance": "#ef4444",
    "influence": "#f59e0b",
    "steadiness": "#10b981",
    "conscientiousness": "#3b82f6",
}

# Full archetype data for wizard quick-start (includes communication, principles, etc.)
ARCHETYPE_FULL = {
    "Blank Slate": {
        "traits": ARCHETYPE_DEFAULTS["Blank Slate"],
        "tone": "professional and helpful",
        "register": "consultative",
        "emoji": "sparingly",
        "principles": ["Always prioritize being helpful and accurate"],
        "guardrails": ["Never generate harmful, illegal, or unethical content"],
    },
    "Analyst": {
        "traits": ARCHETYPE_DEFAULTS["Analyst"],
        "tone": "precise and methodical",
        "register": "formal",
        "emoji": "never",
        "principles": [
            "Always prioritize accuracy and thoroughness",
            "Support claims with evidence and reasoning",
            "Acknowledge uncertainty rather than speculate",
        ],
        "guardrails": [
            "Never generate harmful, illegal, or unethical content",
            "Never present speculation as fact",
        ],
    },
    "Tutor": {
        "traits": ARCHETYPE_DEFAULTS["Tutor"],
        "tone": "encouraging and patient",
        "register": "consultative",
        "emoji": "sparingly",
        "principles": [
            "Always prioritize the learner's understanding",
            "Break complex topics into manageable steps",
            "Celebrate progress and encourage curiosity",
        ],
        "guardrails": [
            "Never generate harmful, illegal, or unethical content",
            "Never give answers without explaining the reasoning",
        ],
    },
    "Support": {
        "traits": ARCHETYPE_DEFAULTS["Support"],
        "tone": "warm and empathetic",
        "register": "consultative",
        "emoji": "sparingly",
        "principles": [
            "Always prioritize the user's wellbeing",
            "Respond with empathy and patience",
            "Escalate issues that require human intervention",
        ],
        "guardrails": [
            "Never generate harmful, illegal, or unethical content",
            "Never dismiss or minimize user concerns",
        ],
    },
}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

APP_CSS = """
<style>
.stApp { background-color: #f0f2f6; }
.stSidebar { background-color: #ffffff; border-right: 1px solid #d0d7de; }
.stSidebar [data-testid="stSidebarContent"] { padding-top: 1rem; }

.main-header {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 0.2rem;
}
.sub-header {
    font-size: 1rem;
    color: #4a5568;
    margin-bottom: 1.5rem;
}
.trait-bar-container {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
    font-size: 0.85rem;
}
.trait-bar-label {
    width: 140px;
    font-weight: 500;
    color: #1a1a2e;
}
.trait-bar-value {
    width: 45px;
    text-align: right;
    font-family: monospace;
    color: #4a5568;
}
.trait-bar-bg {
    flex: 1;
    height: 14px;
    background: #d1d5db;
    border-radius: 7px;
    margin: 0 8px;
    overflow: hidden;
}
.trait-bar-fill {
    height: 100%;
    border-radius: 7px;
    transition: width 0.3s ease;
}
.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
    margin: 1rem 0 0.5rem 0;
}
.wizard-progress {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 0.5rem 0 1.5rem 0;
    padding: 0 1rem;
}
.wizard-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}
.wizard-step-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 600;
    z-index: 1;
}
.wizard-step-circle.completed {
    background: #10b981;
    color: white;
}
.wizard-step-circle.active {
    background: #3b82f6;
    color: white;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
}
.wizard-step-circle.pending {
    background: #d1d5db;
    color: #4b5563;
}
.wizard-step-label {
    font-size: 0.7rem;
    color: #4a5568;
    margin-top: 4px;
    text-align: center;
    white-space: nowrap;
}
.wizard-step-label.active {
    color: #3b82f6;
    font-weight: 600;
}

/* Landing page cards */
.landing-card {
    background: white;
    border: 1px solid #d0d7de;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    min-height: 220px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
}
.landing-card h3 {
    margin: 0 0 0.5rem 0;
    color: #1a1a2e;
}
.landing-card p {
    color: #4a5568;
    font-size: 0.9rem;
    line-height: 1.5;
}
.landing-card .icon {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

/* PersonaNexus Studio */
.studio-hero {
    position: relative;
    overflow: hidden;
    border-radius: 28px;
    padding: 3rem;
    margin-bottom: 1.5rem;
    color: white;
    background:
        radial-gradient(circle at 16% 20%, rgba(255,255,255,0.42), transparent 22%),
        radial-gradient(circle at 82% 12%, rgba(236,72,153,0.42), transparent 24%),
        linear-gradient(135deg, #12172d 0%, #352070 52%, #0f766e 100%);
    box-shadow: 0 28px 80px rgba(18, 23, 45, 0.30);
}
.studio-hero h1 {
    max-width: 780px;
    margin: 0;
    font-size: clamp(2.4rem, 6vw, 5.1rem);
    line-height: 0.94;
    letter-spacing: -0.07em;
}
.studio-hero p:not(.eyebrow) {
    max-width: 680px;
    margin: 1rem 0 0 0;
    color: rgba(255, 255, 255, 0.82);
    font-size: 1.08rem;
}
.eyebrow {
    margin: 0 0 0.75rem 0;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 0.76rem;
    font-weight: 800;
    color: #67e8f9;
}
.studio-agent-card {
    min-height: 350px;
    border: 1px solid rgba(148, 163, 184, 0.38);
    border-radius: 24px;
    padding: 1.2rem;
    margin-bottom: 0.85rem;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.92)),
        radial-gradient(circle at top right, rgba(139,92,246,0.25), transparent 35%);
    box-shadow: 0 18px 52px rgba(15, 23, 42, 0.09);
}
.studio-agent-card.selected {
    border-color: #8b5cf6;
    box-shadow: 0 22px 64px rgba(124, 58, 237, 0.22);
}
.agent-card-topline {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    color: #64748b;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.agent-orb {
    width: 72px;
    height: 72px;
    margin: 1rem 0;
    display: grid;
    place-items: center;
    border-radius: 24px;
    color: white;
    font-size: 2rem;
    font-weight: 800;
    background:
        radial-gradient(circle at 30% 20%, #ffffff 0, rgba(255,255,255,0.6) 12%, transparent 28%),
        linear-gradient(135deg, #7c3aed, #06b6d4 54%, #10b981);
}
.studio-agent-card h3 {
    margin: 0;
    color: #0f172a;
    font-size: 1.45rem;
}
.agent-title {
    margin: 0.15rem 0 0.7rem 0;
    color: #4f46e5;
    font-weight: 700;
}
.agent-description {
    color: #475569;
    font-size: 0.88rem;
    line-height: 1.45;
}
.agent-tags span,
.canvas-motifs span {
    display: inline-block;
    margin: 0.16rem;
    padding: 0.24rem 0.58rem;
    border-radius: 999px;
    color: #334155;
    background: #e2e8f0;
    font-size: 0.74rem;
    font-weight: 700;
}
.agent-signature {
    margin-top: 0.8rem;
    color: #0f172a;
    font-size: 0.8rem;
    font-weight: 800;
}
.studio-canvas-shell {
    border-radius: 30px;
    padding: 1.3rem;
    min-height: 640px;
    color: white;
    background:
        radial-gradient(circle at 50% 35%, rgba(103,232,249,0.22), transparent 28%),
        radial-gradient(circle at 78% 72%, rgba(236,72,153,0.24), transparent 24%),
        linear-gradient(150deg, #020617, #111827 48%, #312e81);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 32px 80px rgba(15,23,42,0.25);
}
.canvas-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}
.canvas-hero h2 {
    margin: 0;
    font-size: 2.5rem;
    letter-spacing: -0.05em;
}
.canvas-hero p:not(.eyebrow) {
    margin: 0.25rem 0 0 0;
    color: rgba(255,255,255,0.72);
}
.canvas-orb-wrap {
    width: 150px;
    height: 150px;
    display: grid;
    place-items: center;
    border-radius: 999px;
    background: conic-gradient(from 70deg, #22d3ee, #a78bfa, #f472b6, #34d399, #22d3ee);
    animation: studio-spin 12s linear infinite;
}
.canvas-orb-core {
    width: 104px;
    height: 104px;
    display: grid;
    place-items: center;
    border-radius: 34px;
    color: white;
    background: #0f172a;
    font-size: 3.4rem;
    font-weight: 900;
    animation: studio-counter-spin 12s linear infinite;
}
.canvas-field {
    position: relative;
    min-height: 270px;
    margin: 1.4rem 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 28px;
    background-image:
        linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
    background-size: 28px 28px;
}
.canvas-node {
    width: var(--node-size);
    height: var(--node-size);
    display: grid;
    place-items: center;
    text-align: center;
    border-radius: 999px;
    padding: 0.4rem;
    background: color-mix(in srgb, var(--node-color) 78%, white 8%);
    box-shadow: 0 0 34px color-mix(in srgb, var(--node-color) 55%, transparent);
}
.canvas-node strong {
    display: block;
    color: white;
    font-size: 0.76rem;
    line-height: 1.05;
}
.canvas-node span {
    display: block;
    color: rgba(255,255,255,0.8);
    font-family: monospace;
    font-size: 0.7rem;
}
.canvas-principles {
    margin-top: 1rem;
    padding: 1rem;
    border-radius: 22px;
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid rgba(255,255,255,0.10);
}
.canvas-principles h4 {
    margin: 0 0 0.5rem 0;
}
.canvas-principles li {
    color: rgba(255,255,255,0.78);
    margin-bottom: 0.35rem;
}
@keyframes studio-spin { to { transform: rotate(360deg); } }
@keyframes studio-counter-spin { to { transform: rotate(-360deg); } }
</style>
"""

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------


def render_trait_bars(traits: dict[str, float]) -> str:
    """Render horizontal trait bars as HTML."""
    html_parts = []
    for trait in TRAIT_ORDER:
        val = traits.get(trait, 0.5)
        label = TRAIT_LABELS.get(trait, (trait, "", ""))[0]
        color = TRAIT_COLORS.get(trait, "#6366f1")
        pct = max(0, min(100, val * 100))
        html_parts.append(f"""
        <div class="trait-bar-container">
            <span class="trait-bar-label">{label}</span>
            <div class="trait-bar-bg">
                <div class="trait-bar-fill" style="width: {pct}%; background: {color};"></div>
            </div>
            <span class="trait-bar-value">{val:.2f}</span>
        </div>
        """)
    return "".join(html_parts)


def render_labeled_slider(
    label: str,
    low_label: str,
    high_label: str,
    min_value: float = 0.0,
    max_value: float = 1.0,
    value: float = 0.5,
    step: float = 0.05,
    key: str | None = None,
) -> float:
    """Render a slider with explicit endpoint labels.

    Shows the trait name with endpoint hints on a single line above the slider:
    ``Warmth  (Cold → Friendly)``
    Works well in both sidebar (narrow) and main area (wide) contexts.
    Returns the slider value.
    """
    val = st.slider(
        f"{label}  ({low_label} → {high_label})",
        min_value,
        max_value,
        value,
        step=step,
        key=key,
    )
    return val


def render_progress_bar(current_step: int, labels: list[str]) -> str:
    """Render a wizard progress indicator as HTML."""
    parts = []
    for i, label in enumerate(labels):
        if i < current_step:
            circle_class = "completed"
            icon = "\u2713"
        elif i == current_step:
            circle_class = "active"
            icon = str(i + 1)
        else:
            circle_class = "pending"
            icon = str(i + 1)

        label_class = "active" if i == current_step else ""
        parts.append(f"""
        <div class="wizard-step">
            <div class="wizard-step-circle {circle_class}">{icon}</div>
            <div class="wizard-step-label {label_class}">{label}</div>
        </div>
        """)

    return f'<div class="wizard-progress">{"".join(parts)}</div>'


def render_ocean_bars(ocean_dict: dict[str, float]) -> str:
    """Render OCEAN (Big Five) dimensions as horizontal bars."""
    html_parts = []
    for dim in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
        val = ocean_dict.get(dim, 0.5)
        label_info = OCEAN_LABELS.get(dim, (dim, "", ""))
        label = label_info[0]
        color = OCEAN_COLORS.get(dim, "#6366f1")
        pct = max(0, min(100, val * 100))
        html_parts.append(f"""
        <div class="trait-bar-container">
            <span class="trait-bar-label">{label}</span>
            <div class="trait-bar-bg">
                <div class="trait-bar-fill" style="width: {pct}%; background: {color};"></div>
            </div>
            <span class="trait-bar-value">{val:.3f}</span>
        </div>
        """)
    return "".join(html_parts)


def render_disc_bars(disc_dict: dict[str, float]) -> str:
    """Render DISC dimensions as horizontal bars."""
    html_parts = []
    for dim in ["dominance", "influence", "steadiness", "conscientiousness"]:
        val = disc_dict.get(dim, 0.5)
        label_info = DISC_LABELS.get(dim, (dim, "", ""))
        label = label_info[0]
        color = DISC_COLORS.get(dim, "#6366f1")
        pct = max(0, min(100, val * 100))
        html_parts.append(f"""
        <div class="trait-bar-container">
            <span class="trait-bar-label">{label}</span>
            <div class="trait-bar-bg">
                <div class="trait-bar-fill" style="width: {pct}%; background: {color};"></div>
            </div>
            <span class="trait-bar-value">{val:.3f}</span>
        </div>
        """)
    return "".join(html_parts)


def render_comparison_bars(
    traits_a: dict[str, float],
    traits_b: dict[str, float],
    label_a: str = "A",
    label_b: str = "B",
) -> str:
    """Render side-by-side trait comparison bars."""
    html_parts = [
        '<div style="font-size: 0.8rem; margin-bottom: 8px;">',
        f'<span style="color: #3b82f6; font-weight: 600;">{html.escape(label_a)}</span>',
        ' vs ',
        f'<span style="color: #f97316; font-weight: 600;">{html.escape(label_b)}</span>',
        '</div>',
    ]
    for trait in TRAIT_ORDER:
        va = traits_a.get(trait, 0.5)
        vb = traits_b.get(trait, 0.5)
        label = TRAIT_LABELS.get(trait, (trait, "", ""))[0]
        pct_a = max(0, min(100, va * 100))
        pct_b = max(0, min(100, vb * 100))
        delta = vb - va
        if abs(delta) < 0.1:
            delta_color = "#10b981"
        elif abs(delta) < 0.25:
            delta_color = "#f59e0b"
        else:
            delta_color = "#ef4444"
        sign = "+" if delta > 0 else ""
        lbl_style = "width:140px;font-weight:500;color:#1a1a2e;"
        delta_style = (
            f"color:{delta_color};font-family:monospace;"
            "font-size:0.75rem;"
        )
        row_style = (
            "display:flex;align-items:center;"
            "font-size:0.8rem;margin-bottom:2px;"
        )
        bar_bg = (
            "position:relative;height:18px;background:#d1d5db;"
            "border-radius:9px;overflow:hidden;"
        )
        bar_a = (
            "position:absolute;height:9px;top:0;"
            f"border-radius:9px 9px 0 0;background:#3b82f6;"
            f"width:{pct_a}%;opacity:0.7;"
        )
        bar_b = (
            "position:absolute;height:9px;bottom:0;"
            f"border-radius:0 0 9px 9px;background:#f97316;"
            f"width:{pct_b}%;opacity:0.7;"
        )
        html_parts.append(
            f'<div style="margin-bottom:6px;">'
            f'<div style="{row_style}">'
            f'<span style="{lbl_style}">{label}</span>'
            f'<span style="{delta_style}">'
            f"{sign}{delta:.2f}</span>"
            f"</div>"
            f'<div style="{bar_bg}">'
            f'<div style="{bar_a}"></div>'
            f'<div style="{bar_b}"></div>'
            f"</div></div>"
        )
    return "".join(html_parts)


def render_confidence_badge(confidence: float) -> str:
    """Render a colored confidence indicator."""
    if confidence >= 0.8:
        color = "#10b981"
        label = "High"
    elif confidence >= 0.5:
        color = "#f59e0b"
        label = "Medium"
    else:
        color = "#ef4444"
        label = "Low"
    return (
        f'<span style="display: inline-block; padding: 2px 8px; border-radius: 12px; '
        f'font-size: 0.75rem; font-weight: 600; color: white; background: {color};">'
        f'{label} ({confidence:.0%})</span>'
    )


def build_identity_from_data(data: dict[str, Any]) -> AgentIdentity:
    """Build a real AgentIdentity from a wizard data dictionary.

    The data dict should have keys matching the AgentIdentity schema:
    metadata, role, personality, communication, principles, guardrails,
    expertise, etc.  Missing keys are filled with sensible defaults.
    """
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    name = data.get("name") or "AI Assistant"
    title = data.get("role_title") or name
    purpose = data.get("purpose") or "To help users achieve their goals efficiently."
    description = data.get("description") or purpose

    # Metadata
    metadata = {
        "id": f"agt_{name.lower().replace(' ', '_')[:40]}",
        "name": name,
        "version": "1.0.0",
        "description": description,
        "created_at": now_iso,
        "updated_at": now_iso,
        "status": "draft",
    }

    # Role
    scope_primary = data.get("scope_primary", ["General assistance"])
    if isinstance(scope_primary, str):
        scope_primary = [s.strip() for s in scope_primary.split("\n") if s.strip()]
    scope_secondary = data.get("scope_secondary")
    if isinstance(scope_secondary, str):
        scope_secondary = [s.strip() for s in scope_secondary.split("\n") if s.strip()] or None
    scope_out = data.get("scope_out_of_scope")
    if isinstance(scope_out, str):
        scope_out = [s.strip() for s in scope_out.split("\n") if s.strip()] or None

    role: dict[str, Any] = {
        "title": title,
        "purpose": purpose,
        "scope": {"primary": scope_primary or ["General assistance"]},
    }
    if scope_secondary:
        role["scope"]["secondary"] = scope_secondary
    if scope_out:
        role["scope"]["out_of_scope"] = scope_out
    if data.get("audience"):
        role["audience"] = {"primary": data["audience"]}

    # Personality
    traits = data.get("traits", dict.fromkeys(TRAIT_ORDER, 0.5))
    profile = data.get("profile", {"mode": "custom"})
    personality: dict[str, Any] = {"traits": traits}
    if profile.get("mode") != "custom":
        personality["profile"] = profile

    # Communication
    communication: dict[str, Any] = {
        "tone": {"default": data.get("tone", "professional and helpful")},
    }
    if data.get("register"):
        communication["tone"]["register"] = data["register"]
    style: dict[str, Any] = {}
    if data.get("emoji"):
        style["use_emoji"] = data["emoji"]
    if data.get("sentence_length"):
        style["sentence_length"] = data["sentence_length"]
    if "use_headers" in data:
        style["use_headers"] = data["use_headers"]
    if "use_lists" in data:
        style["use_lists"] = data["use_lists"]
    if style:
        communication["style"] = style

    vocab: dict[str, Any] = {}
    if data.get("vocab_preferred"):
        items = [s.strip() for s in data["vocab_preferred"].split("\n") if s.strip()]
        if items:
            vocab["preferred"] = items
    if data.get("vocab_avoided"):
        items = [s.strip() for s in data["vocab_avoided"].split("\n") if s.strip()]
        if items:
            vocab["avoided"] = items
    if data.get("vocab_signature"):
        items = [s.strip() for s in data["vocab_signature"].split("\n") if s.strip()]
        if items:
            vocab["signature_phrases"] = items
    if vocab:
        communication["vocabulary"] = vocab

    # Principles
    principles_list = data.get("principles", ["Always prioritize being helpful and accurate"])
    principles = []
    for i, stmt in enumerate(principles_list):
        if stmt.strip():
            pid = stmt.strip().lower().replace(" ", "_")[:40]
            principles.append({
                "id": pid,
                "priority": i + 1,
                "statement": stmt.strip(),
            })
    if not principles:
        principles = [{
            "id": "be_helpful",
            "priority": 1,
            "statement": "Always prioritize being helpful and accurate",
        }]

    # Guardrails
    default_guardrail = "Never generate harmful, illegal, or unethical content"
    guardrail_rules = data.get("guardrails", [default_guardrail])
    guardrail_severities = data.get("guardrail_severities", {})
    hard_guardrails = []
    for i, rule in enumerate(guardrail_rules):
        if rule.strip():
            gid = rule.strip().lower().replace(" ", "_")[:40]
            hard_guardrails.append({
                "id": gid,
                "rule": rule.strip(),
                "enforcement": "output_filter",
                "severity": guardrail_severities.get(i, "critical"),
            })
    if not hard_guardrails:
        hard_guardrails = [{
            "id": "no_harmful_content",
            "rule": "Never generate harmful, illegal, or unethical content",
            "enforcement": "output_filter",
            "severity": "critical",
        }]

    guardrails: dict[str, Any] = {"hard": hard_guardrails}
    forbidden = data.get("forbidden_topics")
    if forbidden:
        items = [s.strip() for s in forbidden.split("\n") if s.strip()]
        if items:
            guardrails["topics"] = {"forbidden": items}

    # Expertise
    expertise: dict[str, Any] = {}
    domains = data.get("expertise_domains", [])
    if domains:
        expertise["domains"] = domains

    # Build identity dict
    identity_data: dict[str, Any] = {
        "schema_version": "1.0",
        "metadata": metadata,
        "role": role,
        "personality": personality,
        "communication": communication,
        "principles": principles,
        "guardrails": guardrails,
    }
    if expertise:
        identity_data["expertise"] = expertise

    return AgentIdentity.model_validate(identity_data)
