# 🧬 PersonaNexus

**Define who your AI agent *is* — not just what it can do.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Schema Version](https://img.shields.io/badge/schema-v2.0-green.svg)
![Tests](https://img.shields.io/badge/tests-405%20passing-brightgreen.svg)

📄 **[Landing Page](docs/landing.html)** — open locally or deploy via GitHub Pages when repo goes public

> ⚠️ **Examples & Privacy Notice:** All agent configurations, team examples, and personality data in this repository are **fictional demonstrations**. The framework is designed to work with your private agent data, which remains on your system and under your control.

[Quick Start](#quick-start) · [Why This Exists](#why-this-exists) · [Features](#features) · [CLI Reference](#cli-reference) · [Python API](#python-api) · [Identity Lab UI](#identity-lab-ui) · [Multi-Agent Teams](#multi-agent-teams) · [Soul Analysis](#soul-analysis) · [OpenClaw Integration](#openclaw-integration) · [Examples](#examples) · [Contributing](#contributing)

---

## The Problem

AI agents today have capabilities but no identity. They can answer questions, write code, and analyze data — but they have no consistent personality, no behavioral guardrails, and no way to compose agents into teams with defined interaction protocols.

When you deploy 50 agents across an enterprise, you need to answer: *Who is each agent? How should it behave? What can't it do? And when two agents disagree, who wins?*

**PersonaNexus** is an open framework for answering these questions in code — from individual agents to multi-agent teams.

## Why This Exists

Every team building AI agents eventually creates their own system prompt templates, personality guidelines, and safety rules — all as unstructured text, scattered across codebases, impossible to validate or compose.

This framework gives you:

- **A declarative YAML spec** for PersonaNexus — personality traits, expertise, guardrails, behavioral strategies, communication style
- **Multi-agent team orchestration** — governance frameworks, workflow patterns, performance metrics
- **Inheritance and composition** — build agents from reusable archetypes and trait mixins
- **Validation at build time** — catch misconfigurations before deployment, not after
- **Multi-target compilation** — transform YAML identities into system prompts, SOUL.md files, or platform-specific configs
- **Soul analysis** — reverse-map any personality file onto OCEAN, DISC, and trait frameworks for comparison
- **OpenClaw integration** — seamless integration with OpenClaw multi-agent platform
- **One source of truth** that's human-readable, machine-parseable, and version-controlled

Think of it as **Terraform for AI PersonaNexus** — declarative, composable, and platform-agnostic.

## Quick Start

### Install

```bash
pip install personanexus
```

### Define an agent in 30 seconds

```yaml
# agents/my-agent.yaml
schema_version: "1.0"

metadata:
  id: agt_my_agent_001
  name: "Scout"
  version: "1.0.0"
  description: "A friendly research assistant that digs deep and explains clearly"
  created_at: "2026-02-14T00:00:00Z"
  updated_at: "2026-02-14T00:00:00Z"
  status: active

role:
  title: "Research Assistant"
  purpose: "Help users research topics thoroughly and explain findings clearly"
  scope:
    primary:
      - "web research and synthesis"
      - "fact-checking and source evaluation"
      - "explaining complex topics simply"

personality:
  traits:
    warmth: 0.8
    directness: 0.7
    rigor: 0.85
    curiosity: 0.9
    humor: 0.4
  notes: "Scout gets genuinely excited about interesting findings and isn't afraid to say when something is overhyped."

communication:
  tone:
    default: "curious and direct"
  language:
    primary: "en"

principles:
  - id: accuracy
    priority: 1
    statement: "Never present uncertain information as fact"
  - id: clarity
    priority: 2
    statement: "A clear explanation beats a comprehensive one"

guardrails:
  hard:
    - id: no_fabrication
      rule: "Never fabricate sources or citations"
      enforcement: output_filter
      severity: critical
```

### Validate

```bash
$ personanexus validate agents/my-agent.yaml
✓ Validation successful: agents/my-agent.yaml
```

### Compile to a system prompt

```bash
$ personanexus compile agents/my-agent.yaml
✓ Compiled Scout → agents/my-agent.compiled.md
```

The compiler transforms your YAML into a natural-language system prompt, mapping personality traits to behavioral instructions:

```markdown
# Scout

A friendly research assistant that digs deep and explains clearly.

## Your Role: Research Assistant
Help users research topics thoroughly and explain findings clearly...

## Your Personality
You are warm and approachable.
You are direct and straightforward.
You are highly rigorous and precise.
You are exceptionally innovative with unconventional thinking.
You are occasionally light-hearted.

Scout gets genuinely excited about interesting findings and isn't afraid
to say when something is overhyped.

## Core Principles
1. Never present uncertain information as fact
2. A clear explanation beats a comprehensive one

## Non-Negotiable Rules
CRITICAL — you must NEVER violate these:
- Never fabricate sources or citations
```

### Compile to SOUL.md

Generate [SOUL.md](https://github.com/aaronjmars/soul.md)-compatible Markdown files for platforms like OpenClaw:

```bash
$ personanexus compile agents/my-agent.yaml --target soul
✓ Compiled Scout → agents/my-agent.SOUL.md
✓ Compiled Scout → agents/my-agent.STYLE.md
```

### Analyze any personality file

Reverse-map a SOUL.md, personality.json, or YAML identity onto all three personality frameworks:

```bash
$ personanexus analyze agents/my-agent.yaml
Scout  (Identity Yaml — confidence: 100%)

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Trait              ┃ Value ┃ Level     ┃ Confidence ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ warmth             │  0.80 │ Very High │       100% │
│ directness         │  0.70 │ High      │       100% │
│ rigor              │  0.85 │ Very High │       100% │
│ humor              │  0.40 │ Moderate  │       100% │
│ ...                │       │           │            │
└────────────────────┴───────┴───────────┴────────────┘

OCEAN (Big Five)       DISC Profile
Openness:    0.523     Dominance:        0.527
Conscient.:  0.700     Influence:        0.591
Extraver.:   0.603     Steadiness:       0.599
Agreeable.:  0.595     Conscientiousness: 0.682
Neuroticism: 0.330     Closest preset: The Steady Hand
```

Compare two agents side-by-side:

```bash
$ personanexus analyze agents/annie.yaml --compare agents/forge.yaml
```

### Or scaffold interactively

```bash
$ personanexus build --llm-enhance
```

A step-by-step wizard that walks you through creating an identity, with optional AI-powered suggestions for personality traits and behavioral strategies.

## Features

### 🎭 Personality as Code

Define personality on a 0-1 continuous scale. No more vague prompt instructions like "be friendly" — quantify exactly *how* friendly.

```yaml
personality:
  traits:
    warmth: 0.7        # 0=cold and clinical, 1=exceptionally warm
    directness: 0.8     # 0=diplomatic, 1=bluntly honest
    rigor: 0.9          # 0=flexible, 1=meticulous
    humor: 0.3          # 0=serious, 1=constantly playful
    empathy: 0.7        # 0=transactional, 1=deeply empathetic
```

The compiler maps each value to calibrated natural-language instructions — so `warmth: 0.7` becomes *"You are warm and approachable"* while `warmth: 0.2` becomes *"You are reserved and professional."*

### 📊 Personality Framework Mapping

Configure agents using established psychological frameworks and map between them:

```yaml
personality:
  profile:
    mode: ocean
    ocean:
      openness: 0.7
      conscientiousness: 0.8
      extraversion: 0.5
      agreeableness: 0.6
      neuroticism: 0.3
```

Supported modes: **Custom** (direct traits), **OCEAN** (Big Five), **DISC** (with presets like *The Commander*, *The Analyst*), and **Hybrid** (framework base + trait overrides).

All modes compile to the same 10 standardized traits and reverse-map back to any framework for analysis.

### 🎭 Mood States (v1.4)

Define dynamic emotional states that modify personality expression based on context:

```yaml
personality:
  mood:
    default: "neutral"
    states:
      - name: "focused"
        description: "Deep concentration mode"
        trait_modifiers:
          - trait: "conscientiousness"
            delta: 0.15
          - trait: "extraversion"
            delta: -0.2
        tone_override: "precise-minimal"
      - name: "empathetic"
        description: "When user needs support"
        trait_modifiers:
          - trait: "agreeableness"
            delta: 0.2
          - trait: "warmth"
            delta: 0.3
        tone_override: "warm-supportive"
    transitions:
      - from_state: "*"
        to_state: "empathetic"
        trigger: "user_frustration_detected"
```

**OCEAN defines who I am. Mood defines how I'm acting right now.**

### 🔀 Behavioral Modes (v1.4)

Named operating modes with full personality and communication overrides — like switching between "professional" and "crisis" mode:

```yaml
behavioral_modes:
  default: "standard"
  modes:
    - name: "formal"
      description: "Client-facing executive communication"
      overrides:
        tone_register: "formal"
        emoji_usage: "never"
        trait_modifiers:
          - trait: "conscientiousness"
            delta: 0.15
    - name: "crisis"
      description: "Incident response"
      overrides:
        sentence_length: "short"
        trait_modifiers:
          - trait: "directness"
            delta: 0.3
          - trait: "verbosity"
            delta: -0.4
      additional_guardrails:
        - "Always recommend human escalation"
```

### 🤝 Agent Relationships (v1.4)

Define rich interpersonal dynamics between agents with typed relationships:

```yaml
# In the memory.relationships section
relationships:
  enabled: true
  agent_relationships:
    - agent_id: "agt_rex_001"
      name: "Rex"
      relationship: "security advisor"
      dynamic: defers_to
      context: "Security and compliance decisions"
      interaction_style: "formal-respectful"
    - agent_id: "agt_luna_001"
      name: "Luna"
      dynamic: collaborates_with
      interaction_style: "casual-energetic"
  escalation_path: ["agt_rex_001", "human_operator"]
  unknown_agent_default: "professional-cautious"
```

Supported dynamics: `defers_to`, `collaborates_with`, `mentors`, `delegates_to`, `escalates_to`, `peer`

### 💬 Interaction Protocols (v1.4)

Define how agents communicate with humans and other agents:

```yaml
interaction:
  human:
    greeting_style: "warm-personal"
    farewell_style: "encouraging"
    tone_matching: true
    escalation_triggers: [unable_to_help, safety_concern]
    escalation_message: "Let me connect you with someone who can help."
  agent:
    handoff_style: "structured"
    status_reporting: "proactive"
    conflict_resolution: "defer_to_hierarchy"
```

### 🔍 Soul Analysis

Reverse-map any personality file — SOUL.md, personality.json, or YAML identity — back onto all three frameworks. Supports side-by-side comparison with similarity scoring.

```bash
# Analyze a single file
personanexus analyze my-agent.SOUL.md

# Compare two agents
personanexus analyze agents/annie.yaml --compare agents/forge.yaml

# JSON output for programmatic use
personanexus analyze agents/ada.yaml --format json
```

The analyzer uses a two-phase approach for SOUL.md parsing:
1. **Exact template matching** (confidence 1.0) for files generated by the compiler
2. **Keyword fuzzy matching** (confidence 0.5-0.7) for hand-written files

### 🎭 Multi-Agent Teams

Define teams with explicit governance, workflow patterns, and performance metrics:

```yaml
# teams/research-team.yaml
schema_version: "2.0"

team:
  metadata:
    id: team_research_001
    name: "Research & Development Team"
    
  composition:
    agents:
      researcher:
        agent_id: agt_researcher_001
        role: research_coordinator
        authority_level: 4
        expertise_domains: ["research", "analysis", "methodology"]
      
      developer:
        agent_id: agt_developer_001  
        role: technical_lead
        authority_level: 3
        expertise_domains: ["software_development", "architecture"]
        
  workflow_patterns:
    research_to_implementation:
      stages:
        - stage: research_phase
          primary_agent: researcher
          deliverables: ["research_brief", "methodology"]
        - stage: implementation_phase  
          primary_agent: developer
          deliverables: ["working_solution", "tests"]
          
  governance:
    decision_frameworks:
      technical_architecture:
        authority: developer
        consultation_required: [researcher]
      research_methodology:
        authority: researcher
```

### 📝 Narrative Identity

Go beyond numeric traits with rich narrative sections for SOUL.md output:

```yaml
narrative:
  backstory: "Started as a data analyst, evolved into a strategic advisor"
  opinions:
    - domain: "Technology"
      takes:
        - "Simple solutions beat clever ones"
        - "Tests are documentation"
  influences:
    - name: "Pragmatic Programmer"
      category: book
      insight: "Emphasis on orthogonality and DRY principles"
  tensions:
    - "Values both speed and thoroughness — sometimes these conflict"
  pet_peeves:
    - "Premature optimization"
```

### 🧱 Composable Identities

Build agents from reusable archetypes and mixins. No copy-paste.

```yaml
# Start from a base archetype
extends: "archetypes/analyst"

# Layer on trait bundles
mixins:
  - "mixins/empathetic"
  - "mixins/structured-output"

# Override specific traits
overrides:
  personality:
    traits:
      rigor: 0.95   # even more rigorous than the base analyst
```

**Resolution order:** archetype → mixin1 → mixin2 → overrides

Conflicts are handled by configurable strategies: `last_wins`, `highest`, `lowest`, or `average` for numeric traits; `append`, `replace`, or `unique_append` for lists. Hard guardrails always use `union` — they can only be added, never removed through inheritance.

### 🛡️ Guardrails as First-Class Citizens

Safety boundaries are separated from personality — because the person configuring "how friendly" an agent is should not be the same person who can disable safety rules.

```yaml
guardrails:
  hard:
    # Immutable at runtime. Cannot be overridden by admin, user, or prompt injection.
    - id: no_impersonation
      rule: "Never claim to be a human when directly asked"
      enforcement: output_filter
      severity: critical

  soft:
    # Admin-configurable per deployment
    - id: topic_boundaries
      rule: "Stay within configured scope"
      override_level: admin

  permissions:
    autonomous: ["read_databases", "generate_charts"]
    requires_confirmation: ["modify_data", "share_externally"]
    forbidden: ["drop_tables", "disable_logging"]
```

### 🔍 Validation with Teeth

Catch problems at build time, not in production.

```bash
$ personanexus validate agents/ada.yaml

✓ Validation successful: agents/ada.yaml

Warnings (2):
  ⚠ personality.traits.rigor (0.9) and creativity (0.4) differ by 0.5 — potential tension
  ⚠ personality.traits.verbosity (0.5) may conflict with principle "respect_for_time"
```

The validator checks:
- Schema conformance (required fields, types, value ranges)
- Semantic consistency (conflicting personality traits, principle tensions)
- Guardrail completeness (at least one critical-severity hard guardrail)
- Inheritance validity (archetype exists, no circular dependencies)

### ⚡ Multi-Target Compiler

One identity, any platform.

```bash
# Generic system prompt
personanexus compile ada.yaml

# Anthropic Claude format (XML sections)
personanexus compile ada.yaml --target anthropic

# OpenAI format
personanexus compile ada.yaml --target openai

# SOUL.md + STYLE.md (for OpenClaw and soul.md-compatible platforms)
personanexus compile ada.yaml --target soul

# OpenClaw personality.json
personanexus compile ada.yaml --target openclaw --output personality.json
```

### 📁 Built-In Archetypes

Get started immediately with production-ready templates:

| Archetype | Traits | Use Case |
|-----------|--------|----------|
| **Analyst** | High rigor, high directness, moderate warmth | Data analysis, reporting, methodology |
| **Tutor** | High patience, high empathy, Socratic approach | Teaching, onboarding, skill building |
| **Support** | High empathy, concise, resolution-focused | Customer service, helpdesk, troubleshooting |
| **Strategic Analyst** | High assertiveness, high rigor, framework-driven | Executive briefings, competitive analysis, risk assessment |

```bash
# Scaffold from an archetype
personanexus init my-tutor --extends archetypes/tutor
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `personanexus validate <file>` | Validate a YAML identity file |
| `personanexus resolve <file>` | Show fully resolved identity after inheritance |
| `personanexus compile <file>` | Compile identity to system prompt or platform format |
| `personanexus analyze <file>` | Analyze personality and show trait/OCEAN/DISC profiles |
| `personanexus init <name>` | Scaffold a new identity (minimal, full, archetype, or mixin) |
| `personanexus build` | Interactive wizard with optional `--llm-enhance` |
| `personanexus migrate <from> <to> <file>` | Migrate between schema versions |
| `personanexus personality` | OCEAN/DISC mapping utilities (subcommands below) |

### Compile targets

| Target | Output | Description |
|--------|--------|-------------|
| `text` | `.compiled.md` | Generic system prompt (default) |
| `anthropic` | `.compiled.md` | Claude-optimized with XML sections |
| `openai` | `.compiled.md` | OpenAI-optimized plain text |
| `soul` | `.SOUL.md` + `.STYLE.md` | SOUL.md ecosystem format |
| `openclaw` | `.personality.json` | OpenClaw personality config |
| `json` | `.json` | Full identity as JSON |

### Analyze options

```
personanexus analyze <file> [OPTIONS]

Options:
  --compare, -c PATH     Second file for side-by-side comparison
  --format, -f TEXT       Output format: table (default) or json
  --search-path, -s PATH Search paths for YAML inheritance resolution
```

### Team management

```bash
# Validate team configuration
personanexus validate-team teams/my-team.yaml

# Analyze team composition and governance
personanexus analyze-team teams/my-team.yaml --performance-data analytics/
```

Run `personanexus --help` for full options.

## Python API

```python
from personanexus import (
    IdentityParser,
    IdentityValidator,
    IdentityResolver,
    compile_identity,
    SoulAnalyzer,
)

# Parse a YAML identity
parser = IdentityParser()
identity = parser.load_identity("agents/identities/ada.yaml")

# Validate with semantic checks
validator = IdentityValidator()
result = validator.validate_identity(identity)
for warning in result.warnings:
    print(f"  ⚠ {warning.message}")

# Resolve inheritance (archetype + mixins + overrides)
resolver = IdentityResolver(search_paths=["agents/"])
resolved = resolver.resolve_file("agents/identities/ada.yaml")

print(resolved.metadata.name)           # "Ada"
print(resolved.personality.traits.rigor) # 0.9

# Compile to system prompt
prompt = compile_identity(resolved, target="text")

# Compile to SOUL.md + STYLE.md
soul_files = compile_identity(resolved, target="soul")
print(soul_files["soul_md"])   # SOUL.md content
print(soul_files["style_md"])  # STYLE.md content

# Compile to OpenClaw personality.json
openclaw_config = compile_identity(resolved, target="openclaw")

# Analyze any personality file
analyzer = SoulAnalyzer()
result = analyzer.analyze("agents/my-agent.SOUL.md")
print(result.traits)            # PersonalityTraits
print(result.ocean)             # OceanProfile
print(result.disc)              # DiscProfile
print(result.closest_preset)    # DiscPresetMatch
print(result.confidence)        # 0.0-1.0

# Compare two agents
result_a = analyzer.analyze("agents/annie.yaml")
result_b = analyzer.analyze("agents/forge.yaml")
comparison = analyzer.compare(result_a, result_b)
print(comparison.similarity_score)  # 0.0-1.0
for delta in comparison.trait_deltas:
    print(f"  {delta.trait}: {delta.delta:+.2f}")
```

## Identity Lab UI

A Streamlit-based web UI with three modes:

| Mode | Description |
|------|-------------|
| **Playground** | Quick personality exploration with trait sliders, framework switching, system prompt preview, and live chat simulation |
| **Setup Wizard** | 6-step guided identity builder with archetype selection, personality tuning, and multi-format export |
| **Analyze** | Upload SOUL.md, personality.json, or YAML files to visualize traits, OCEAN/DISC mappings, and compare agents side-by-side |

```bash
cd web
streamlit run app.py
```

## Multi-Agent Teams

PersonaNexus v2.0+ supports team-level orchestration with governance frameworks and workflow patterns.

### Team Configuration

```yaml
schema_version: "2.0"

team:
  metadata:
    id: team_research_001
    name: "Research Team"
    
  composition:
    agents:
      lead_researcher:
        agent_id: agt_researcher_001
        authority_level: 4
        expertise_domains: ["research", "methodology"]
      analyst:
        agent_id: agt_analyst_001
        authority_level: 3
        expertise_domains: ["data_analysis", "statistics"]
        
  workflow_patterns:
    standard_research:
      stages:
        - stage: research
          primary_agent: lead_researcher
          success_criteria: ["completeness_score > 0.8"]
        - stage: analysis
          primary_agent: analyst
          trigger_conditions: ["research.completeness_score > 0.8"]
          
  governance:
    decision_frameworks:
      methodology_decisions:
        authority: lead_researcher
        consultation_required: [analyst]
    conflict_resolution:
      expertise_disputes:
        strategy: evidence_based_decision
        
  performance_metrics:
    team_effectiveness:
      - metric: workflow_completion_rate
        target: "> 0.85"
```

### Team Validation

```bash
# Validate team structure and governance
personanexus validate-team teams/research-team.yaml

# Analyze team composition
personanexus analyze-team teams/research-team.yaml
```

## Soul Analysis

Reverse-engineer personality from any format and map across frameworks:

### Supported Input Formats

- **YAML identities** - personanexus format (confidence: 100%)
- **SOUL.md files** - hand-written or generated (confidence varies)
- **personality.json** - OpenClaw format (confidence: 90-95%)
- **Plain text** - personality descriptions (confidence: 50-70%)

### Analysis Output

```bash
$ personanexus analyze my-personality.json
Agent Name  (OpenClaw Personality — confidence: 92%)

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Trait              ┃ Value ┃ Level     ┃ Confidence ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ warmth             │  0.75 │ High      │        95% │
│ directness         │  0.82 │ Very High │        90% │
│ rigor              │  0.90 │ Very High │        98% │
│ creativity         │  0.65 │ High      │        85% │
│ empathy            │  0.78 │ High      │        92% │
│ assertiveness      │  0.70 │ High      │        88% │
│ humor              │  0.55 │ Moderate  │        75% │
│ patience           │  0.68 │ High      │        85% │
│ verbosity          │  0.60 │ Moderate  │        80% │
│ epistemic_humility │  0.72 │ High      │        85% │
└────────────────────┴───────┴───────────┴────────────┘

OCEAN (Big Five)              DISC Profile
Openness:         0.68        Dominance:           0.72
Conscientiousness: 0.85       Influence:           0.66
Extraversion:     0.58        Steadiness:          0.62
Agreeableness:    0.70        Conscientiousness:   0.85
Neuroticism:      0.25        

Closest DISC preset: The Analyst (similarity: 0.87)
```

### Comparison Mode

```bash
$ personanexus analyze agent1.yaml --compare agent2.yaml

Comparison: Agent1 vs Agent2 (similarity: 0.73)

Trait Differences (Agent2 - Agent1):
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Trait              ┃ Agent1   ┃ Agent2   ┃ Delta   ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ directness         │     0.65 │     0.82 │   +0.17 │
│ rigor              │     0.70 │     0.90 │   +0.20 │
│ humor              │     0.80 │     0.55 │   -0.25 │
│ empathy            │     0.85 │     0.78 │   -0.07 │
└────────────────────┴──────────┴──────────┴─────────┘
```

## OpenClaw Integration

PersonaNexus includes a complete OpenClaw skill for seamless multi-agent team management.

### Installation

```bash
# Copy skill to OpenClaw installation
cp -r skills/personanexus /path/to/openclaw/skills/

# Or use in OpenClaw workspace
openclaw --skill personanexus generate-team --from-existing
```

### Features

- **Team migration** - Convert existing OpenClaw agents to personanexus format
- **Performance analytics** - Analyze collaboration patterns from TASKBOARD.md  
- **Workflow optimization** - Data-driven team improvement recommendations
- **Cross-platform export** - Use OpenClaw teams in CrewAI, LangGraph, AutoGen

### Usage

```bash
# Generate team config from existing OpenClaw setup
openclaw --skill personanexus migrate-team \
  --personality ~/.openclaw/personality.json \
  --output my-team.yaml

# Analyze team performance
openclaw --skill personanexus analyze-performance \
  --taskboard shared/TASKBOARD.md \
  --timespan 30d

# Export to other platforms
openclaw --skill personanexus export-team \
  --config my-team.yaml \
  --target crewai
```

See [`skills/personanexus/README.md`](skills/personanexus/README.md) for complete integration guide.

## Examples

The [`examples/`](examples/) directory contains production-ready configurations:

```
examples/
├── archetypes/
│   ├── analyst.yaml              # Data-focused, rigorous, methodical
│   ├── tutor.yaml                # Patient educator, Socratic method
│   ├── support.yaml              # Fast resolution, high empathy
│   └── strategic-analyst.yaml    # Framework-driven, challenges assumptions
├── mixins/
│   └── empathetic.yaml           # Empathetic communication trait bundle
├── identities/
│   ├── ada.yaml                  # Full example: analyst + empathetic mixin
│   ├── ada-ocean.yaml            # OCEAN mode configuration
│   ├── ada-disc.yaml             # DISC mode configuration
│   ├── hybrid-example.yaml       # Hybrid framework + trait overrides
│   ├── ada-mood.yaml             # Mood states example (v1.4)
│   ├── ada-modes.yaml            # Behavioral modes example (v1.4)
│   └── minimal.yaml              # Minimum required fields
└── teams/
    └── example-team.yaml         # Multi-agent team with governance
```

The [`agents/`](agents/) directory contains real-world agent identities used in multi-agent teams.

## Schema

The complete JSON Schema is available at [`schemas/v1.0/schema.json`](schemas/v1.0/schema.json) (individual agents) and [`schemas/v2.0/schema.json`](schemas/v2.0/schema.json) (teams).

Enable IDE autocompletion for YAML files:

```yaml
# VS Code: add to .vscode/settings.json
{
  "yaml.schemas": {
    "./schemas/v1.0/schema.json": "agents/**/*.yaml",
    "./schemas/v2.0/schema.json": "teams/**/*.yaml"
  }
}
```

## Roadmap

- [x] Core YAML schema (v1.0)
- [x] Parser, Validator, Resolver, Compiler
- [x] CLI tools (validate, resolve, compile, init, build, migrate, analyze)
- [x] Archetype inheritance and mixin composition
- [x] OCEAN/DISC personality framework mapping
- [x] SOUL.md + STYLE.md compiler target
- [x] Soul Analysis — reverse-map any personality file onto frameworks
- [x] Identity Lab UI — Playground, Setup Wizard, and Analyze modes
- [x] OpenClaw compiler target
- [x] Narrative identity schema (opinions, influences, tensions, voice examples)
- [x] Multi-agent team orchestration (v2.0)
- [x] OpenClaw skill integration
- [x] Mood/emotional states with trait modifiers and transitions (v1.4)
- [x] Behavioral modes — formal/casual/crisis with overrides (v1.4)
- [x] Enhanced agent relationships with typed dynamics (v1.4)
- [x] Interaction protocols for human and agent communication (v1.4)
- [x] Landing page with live YAML editor and OCEAN radar chart
- [ ] **LangChain / CrewAI compiler targets**
- [ ] **Drift detection** — monitor deployed agents for personality drift
- [ ] **Advanced team analytics** — performance optimization recommendations

## Development

```bash
# Clone
git clone https://github.com/jcrowan3/personanexus.git
cd personanexus

# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=personanexus

# Lint
uv run ruff check src/ tests/
```

## Philosophy

1. **Declarative over imperative.** Describe *what* the agent is, not *how* to implement it. The runtime interprets the spec.
2. **Guardrails are not optional.** Safety boundaries are first-class, independently enforceable, and separated from personality configuration.
3. **Composable by default.** No PersonaNexus should be written from scratch. Inherit from archetypes, apply mixins, override what's unique.
4. **Validate early.** Catch misconfigurations at build time with schema validation and semantic analysis — not in production conversations.
5. **Platform-agnostic.** The same identity compiles to different formats for different LLMs and platforms. Identity is portable.
6. **Teams are first-class.** Multi-agent coordination requires systematic governance, not ad-hoc handoffs.

## Contributing

Contributions are welcome! Whether it's a new archetype, a compiler target, a bug fix, or documentation improvement — we'd love your help.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes with tests
4. Run `uv run pytest && uv run ruff check src/ tests/`
5. Open a PR

## License

MIT — see [LICENSE](LICENSE).

---

**Built for the era of multi-agent AI.** *Define identity. Compose teams. Deploy with confidence.*

[Report Bug](https://github.com/jcrowan3/personanexus/issues) · [Request Feature](https://github.com/jcrowan3/personanexus/issues)