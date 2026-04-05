#!/usr/bin/env python3
"""
Compile a PersonaNexus team YAML into a human-readable TEAM-MANIFEST.md.

Usage:
    python scripts/compile-team-manifest.py examples/teams/openclaw-core-team.yaml -o TEAM-MANIFEST.md
    python scripts/compile-team-manifest.py examples/teams/openclaw-core-team.yaml  # prints to stdout
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_team(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_manifest(data: dict, source_path: str) -> str:
    team = data.get("team", data)
    meta = team.get("metadata", {})
    comp = team.get("composition", {})
    agents = comp.get("agents", {})
    sub_agents = comp.get("sub_agents", {})
    workflows = team.get("workflow_patterns", {})
    governance = team.get("governance", {})
    ops = data.get("operations", {})

    lines = []

    # --- Header ---
    lines.append(f"# {meta.get('name', 'Team')} — Capabilities Manifest")
    lines.append("")
    lines.append(f"*{meta.get('description', '')}*")
    lines.append("")
    lines.append(f"> **Read this on every session start.** This is how our team works — who does what,")
    lines.append(f"> when to delegate, and how to hand off work effectively.")
    lines.append("")
    lines.append(f"**Version:** {meta.get('version', '?')} | **Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')} | **Source:** `{source_path}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Team Roster ---
    lines.append("## Team Roster")
    lines.append("")
    lines.append("| Agent | Role | Authority | Key Skills |")
    lines.append("|-------|------|-----------|------------|")
    for name, agent in agents.items():
        role = agent.get("role", "").replace("_", " ").title()
        auth = agent.get("authority_level", "?")
        skills = agent.get("expertise_domains", [])
        top_skills = ", ".join(s.replace("_", " ").title() for s in skills[:4])
        if len(skills) > 4:
            top_skills += f" +{len(skills) - 4} more"
        lines.append(f"| **{name.title()}** | {role} | Level {auth} | {top_skills} |")
    lines.append("")

    # --- Sub-Agents ---
    if sub_agents:
        lines.append("### Sub-Agents (Logical)")
        lines.append("")
        lines.append("| Sub-Agent | Parent | Specialization | Description |")
        lines.append("|-----------|--------|---------------|-------------|")
        for sa_name, sa in sub_agents.items():
            parent = sa.get("parent_agent", "?").title()
            role = sa.get("role", "").replace("_", " ").title()
            desc = sa.get("description", "")
            lines.append(f"| **{sa_name.title()}** | {parent} | {role} | {desc} |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # --- Delegation Guide ---
    lines.append("## Delegation Guide")
    lines.append("")
    lines.append("*When you need help, here's who to ask:*")
    lines.append("")

    # Build delegation map from expertise domains
    domain_map = {}
    for name, agent in agents.items():
        for domain in agent.get("expertise_domains", []):
            readable = domain.replace("_", " ").title()
            if readable not in domain_map:
                domain_map[readable] = []
            domain_map[readable].append(name.title())

    # Group by primary agent
    delegation_items = []
    for domain, owners in sorted(domain_map.items()):
        primary = owners[0]
        delegation_items.append(f"- **{domain}** → {primary}")

    lines.extend(delegation_items)
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Capabilities Matrix ---
    lines.append("## Capabilities by Agent")
    lines.append("")
    for name, agent in agents.items():
        lines.append(f"### {name.title()}")
        lines.append("")

        # Skills
        domains = agent.get("expertise_domains", [])
        if domains:
            lines.append("**Expertise:**")
            for d in domains:
                lines.append(f"- {d.replace('_', ' ').title()}")
            lines.append("")

        # Capabilities
        caps = agent.get("capabilities", [])
        if caps:
            lines.append("**Tools & Capabilities:**")
            lines.append(", ".join(f"`{c}`" for c in caps))
            lines.append("")

        # Delegation rights
        rights = agent.get("delegation_rights", [])
        if rights:
            lines.append("**Delegation Rights:**")
            for r in rights:
                lines.append(f"- {r.replace('_', ' ').title()}")
            lines.append("")

        # Personality snapshot
        personality = agent.get("personality_summary", {})
        if personality:
            traits_str = " | ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in personality.items())
            lines.append(f"**Personality:** {traits_str}")
            lines.append("")

    lines.append("---")
    lines.append("")

    # --- Workflow Patterns ---
    lines.append("## Workflow Patterns")
    lines.append("")
    for wf_id, wf in workflows.items():
        wf_name = wf_id.replace("_", " ").title()
        desc = wf.get("description", "")
        duration = wf.get("estimated_duration", "?")
        stages = wf.get("stages", [])

        lines.append(f"### {wf_name}")
        lines.append(f"*{desc}* (Est. {duration})")
        lines.append("")

        for i, stage in enumerate(stages, 1):
            stage_name = stage.get("stage", "").replace("_", " ").title()
            agent_name = stage.get("primary_agent", "?").title()
            objective = stage.get("objective", "")
            deliverables = stage.get("deliverables", [])
            max_dur = stage.get("max_duration", "")
            deliv_str = ", ".join(d.replace("_", " ") for d in deliverables)
            lines.append(f"**Stage {i}: {stage_name}** ({agent_name}, max {max_dur})")
            lines.append(f"  - Objective: {objective}")
            if deliv_str:
                lines.append(f"  - Deliverables: {deliv_str}")
            lines.append("")

    lines.append("---")
    lines.append("")

    # --- Governance ---
    lines.append("## Governance")
    lines.append("")
    decision_frameworks = governance.get("decision_frameworks", {})
    if decision_frameworks:
        lines.append("### Decision Authority")
        lines.append("")
        lines.append("| Domain | Authority | Consultation | Escalation |")
        lines.append("|--------|-----------|--------------|------------|")
        for domain, fw in decision_frameworks.items():
            domain_name = domain.replace("_", " ").title()
            auth = fw.get("authority", "?").title()
            consult = ", ".join(c.title() for c in fw.get("consultation_required", []))
            escalation = ", ".join(fw.get("escalation_criteria", []))[:50]
            lines.append(f"| {domain_name} | **{auth}** | {consult or '—'} | {escalation or '—'} |")
        lines.append("")

    conflict = governance.get("conflict_resolution", {})
    if conflict:
        lines.append("### Conflict Resolution")
        lines.append("")
        for name, cr in conflict.items():
            cr_name = name.replace("_", " ").title()
            strategy = cr.get("strategy", "").replace("_", " ")
            lines.append(f"- **{cr_name}**: {strategy}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # --- Operations ---
    if ops:
        lines.append("## Operations")
        lines.append("")
        wh = ops.get("working_hours", {})
        if wh:
            lines.append(f"- **Timezone:** {wh.get('timezone', '?')}")
            lines.append(f"- **Core hours:** {wh.get('core_hours', '?')}")
            lines.append(f"- **After hours:** {wh.get('after_hours_urgency_threshold', 'P0 only')}")

        rl = ops.get("resource_limits", {})
        if rl:
            lines.append(f"- **Max concurrent workflows:** {rl.get('max_concurrent_workflows', '?')}")
            lines.append(f"- **Max workflow duration:** {rl.get('max_workflow_duration', '?')}")

        integration = ops.get("integration", {})
        if integration:
            lines.append("")
            lines.append("### Integration Points")
            for key, val in integration.items():
                lines.append(f"- **{key.replace('_', ' ').title()}:** {val}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compile team YAML to TEAM-MANIFEST.md")
    parser.add_argument("input", help="Path to team YAML file")
    parser.add_argument("-o", "--output", help="Output path (default: stdout)")
    args = parser.parse_args()

    data = load_team(args.input)
    manifest = build_manifest(data, args.input)

    if args.output:
        Path(args.output).write_text(manifest)
        print(f"Wrote {args.output} ({len(manifest)} bytes)")
    else:
        print(manifest)


if __name__ == "__main__":
    main()
