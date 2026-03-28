# 🧬 PersonaNexus

**Define who your AI agent *is* — not just what it can do.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Schema Version](https://img.shields.io/badge/schema-v1.0-green.svg)
![Tests](https://img.shields.io/badge/tests-878%20passing-brightgreen.svg)

> ⚠️ **Privacy Notice:** All agent configurations in this repository are **fictional demonstrations**. Your private agent data remains on your system and under your control.

[Quick Start](#quick-start) · [Features](#features) · [CLI Reference](#cli-reference) · [Python API](#python-api) · [Examples](#examples) · [Contributing](#contributing)

---

## Why This Exists

Every team building AI agents eventually creates their own system prompt templates, personality guidelines, and safety rules — all as unstructured text, scattered across codebases, impossible to validate or compose.

PersonaNexus gives you:

- **A declarative YAML spec** for agent identity — personality traits, expertise, guardrails, communication style
- **Inheritance and composition** — build agents from reusable archetypes and trait mixins
- **Validation at build time** — catch misconfigurations before deployment
- **Multi-target compilation** — YAML → system prompts, SOUL.md files, or platform-specific configs
- **Personality framework mapping** — OCEAN (Big Five), DISC, and Jungian 16-type with bidirectional mapping
- **Soul analysis** — reverse-map any personality file onto all three frameworks for comparison
- **Multi-agent teams** — governance frameworks, workflow patterns, and team validation

Think of it as **Terraform for AI agent identity** — declarative, composable, and platform-agnostic.

## Quick Start

### Install

```bash
pip install personanexus
```

### Define an agent

```yaml
# agents/my-agent.yaml
schema_version: "1.0"

metadata:
  id: agt_scout_001
  name: "Scout"
  version: "1.0.0"
  description: "A research assistant that digs deep and explains clearly"
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

personality:
  traits:
    warmth: 0.8
    directness: 0.7
    rigor: 0.85
    humor: 0.4

communication:
  tone:
    default: "curious and direct"
  language:
    primary: "en"

principles:
  - id: accuracy
    priority: 1
    statement: "Never present uncertain information as fact"

guardrails:
  hard:
    - id: no_fabrication
      rule: "Never fabricate sources or citations"
      enforcement: output_filter
      severity: critical
```

### Validate and compile

```bash
# Validate
$ personanexus validate agents/my-agent.yaml
✓ Validation successful: agents/my-agent.yaml

# Compile to system prompt
$ personanexus compile agents/my-agent.yaml
✓ Compiled Scout → agents/my-agent.compiled.md

# Compile to SOUL.md format
$ personanexus compile agents/my-agent.yaml --target soul
✓ Compiled Scout → agents/my-agent.SOUL.md
✓ Compiled Scout → agents/my-agent.STYLE.md
```

> **Note:** If your agent uses archetype inheritance (`extends:`), add `--search-path` to compilation and analysis commands so archetypes/mixins can be resolved:
> ```bash
> personanexus compile agents/mira.yaml --search-path examples
> personanexus analyze agents/mira.yaml --search-path examples
> ```

### Analyze any personality file

```bash
$ personanexus analyze agents/my-agent.yaml
Scout  (Identity Yaml — confidence: 100%)

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Trait              ┃ Value ┃ Level     ┃ Confidence ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ warmth             │  0.80 │ Very High │       100% │
│ directness         │  0.70 │ High      │       100% │
│ ...                │       │           │            │
└────────────────────┴───────┴───────────┴────────────┘

OCEAN (Big Five)       DISC Profile             Jungian Profile
Openness:    0.523     Dominance:     0.527      E/I: 0.482
Conscient.:  0.700     Influence:     0.591      S/N: 0.530
...                    Closest: Steady Hand      Closest: ISFJ
```

### Or scaffold interactively

```bash
$ personanexus build --llm-enhance
```

## Features

### Personality as Code

Define personality on a 0–1 continuous scale across 10 standardized traits (warmth, verbosity, assertiveness, humor, empathy, directness, rigor, creativity, epistemic\_humility, patience). The compiler maps each value to calibrated natural-language instructions.

### Personality Framework Mapping

Configure agents using established psychological frameworks:

- **Custom** — set each trait directly
- **OCEAN (Big Five)** — openness, conscientiousness, extraversion, agreeableness, neuroticism
- **DISC** — with presets like *The Commander*, *The Analyst*, *The Influencer*, *The Steady Hand*
- **Jungian 16-type** — all 16 types (INTJ, ENFP, etc.) with role-based recommendations
- **Hybrid** — framework base + explicit trait overrides

All modes compile to the same 10 traits and reverse-map back to any framework for analysis.

### Composable Identities

Build agents from reusable archetypes and mixins — no copy-paste:

```yaml
extends: "archetypes/analyst"
mixins:
  - "mixins/empathetic"
overrides:
  personality:
    traits:
      rigor: 0.95
```

Conflicts are handled by configurable strategies: `last_wins`, `highest`, `lowest`, `average`. Hard guardrails always use `union` — they can only be added, never removed.

### Guardrails as First-Class Citizens

Safety boundaries are separated from personality. Hard guardrails are immutable at runtime; soft guardrails are admin-configurable per deployment.

### Multi-Target Compiler

One identity, any platform:

| Target | Output | Description |
|--------|--------|-------------|
| `text` | `.compiled.md` | Generic system prompt (default) |
| `anthropic` | `.compiled.md` | Claude-optimized with XML sections |
| `openai` | `.compiled.md` | OpenAI-optimized plain text |
| `soul` | `.SOUL.md` + `.STYLE.md` | SOUL.md ecosystem format |
| `openclaw` | `.personality.json` | OpenClaw personality config |
| `json` | `.json` | Full identity as JSON |

### Soul Analysis

Reverse-map any personality file — SOUL.md, personality.json, or YAML — onto all three frameworks. Supports side-by-side comparison with cosine similarity scoring.

### Multi-Agent Teams

Define teams with governance, workflow patterns, and performance metrics using schema v2.0:

```bash
personanexus validate-team teams/research-team.yaml
```

### Dynamic & Stateful Personality (v1.1)

Agents can adapt their personality in real-time based on context and evolve over time through memory:

```yaml
dynamics:
  default_mood: "neutral"
  default_mode: "stranger"

  moods:
    - name: "stressed"
      trait_deltas: { warmth: -0.15, rigor: +0.20 }
      triggers:
        - type: "keyword"
          value: "urgent"
        - type: "sentiment_below"
          value: 0.3

  modes:
    - name: "familiar"
      trait_overrides: { warmth: 0.70, humor: 0.45 }
      triggers:
        - type: "interaction_count_above"
          value: 5

  memory_influences:
    - condition: "positive_interactions > 10"
      effect: "warmth +0.10 permanent"
```

**Runtime flow:** Load user state → evaluate triggers → adjust traits → recompile prompt → update memory.

Per-user state is persisted as JSON files (`.personanexus/memory/`), tracking interaction count, sentiment, trust score, and custom counters.

```python
from personanexus import DynamicSession

session = DynamicSession(identity, user_id="user_123")
result = session.process("Hello!", sentiment=0.7)
print(result.active_mood, result.active_mode, result.adjusted_traits)
session.save()
```

Simulate personality shifts from the CLI:

```bash
personanexus simulate agents/mira-dynamics.yaml --user stranger --steps 10
```

### Additional Features

- **Mood states** — dynamic emotional states that modify personality expression
- **Behavioral modes** — named operating modes (formal, crisis) with overrides
- **Agent relationships** — typed dynamics (`defers_to`, `collaborates_with`, `mentors`, etc.)
- **Interaction protocols** — human and agent communication configuration
- **Narrative identity** — backstory, opinions, influences, tensions for SOUL.md output
- **Identity Lab UI** — Streamlit web UI with Playground, Setup Wizard, and Analyze modes

## CLI Reference

| Command | Description |
|---------|-------------|
| `personanexus validate <file>` | Validate a YAML identity file |
| `personanexus resolve <file>` | Show fully resolved identity after inheritance |
| `personanexus compile <file>` | Compile identity to system prompt or platform format |
| `personanexus analyze <file>` | Analyze personality → traits/OCEAN/DISC/Jungian profiles |
| `personanexus init <name>` | Scaffold a new identity |
| `personanexus build` | Interactive wizard with optional `--llm-enhance` |
| `personanexus migrate <from> <to> <file>` | Migrate between schema versions |
| `personanexus simulate <file>` | Simulate dynamic personality shifts in a mock chat loop |
| `personanexus validate-team <file>` | Validate a team configuration |
| `personanexus personality <subcommand>` | Framework mapping utilities |

### Personality subcommands

```bash
personanexus personality ocean-to-traits --openness 0.7 ...
personanexus personality disc-to-traits --dominance 0.9 ...
personanexus personality jungian-to-traits --preset intj
personanexus personality list-jungian-presets
personanexus personality jungian-recommend strategic_analysis
personanexus personality show-profile examples/identities/mira.yaml --search-path examples
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
    DynamicSession,
)

# Parse and validate
parser = IdentityParser()
identity = parser.load_identity("agents/mira.yaml")

validator = IdentityValidator()
result = validator.validate_identity(identity)

# Resolve inheritance
resolver = IdentityResolver(search_paths=["examples/"])
resolved = resolver.resolve_file("agents/mira.yaml")

# Compile
prompt = compile_identity(resolved, target="text")
soul_files = compile_identity(resolved, target="soul")

# Analyze and compare
analyzer = SoulAnalyzer()
result = analyzer.analyze("agents/my-agent.yaml")
print(result.traits, result.ocean, result.disc, result.jungian)

comparison = analyzer.compare(result_a, result_b)
print(comparison.similarity_score)

# Dynamic sessions — stateful personality that adapts per user
session = DynamicSession(resolved, user_id="user_42")
result = session.process("I need urgent help!", sentiment=0.3)
print(result.active_mood)    # e.g. "stressed"
print(result.active_mode)    # e.g. "stranger" → "familiar" as trust grows
print(result.adjusted_traits) # traits with mood/mode adjustments applied
session.save()  # persist user state to .personanexus/memory/
```

## Examples

The [`examples/`](examples/) directory contains production-ready configurations:

```
examples/
├── archetypes/          # Analyst, Tutor, Support, Strategic Analyst
├── mixins/              # Empathetic communication, Structured output
├── identities/
│   ├── mira.yaml              # Custom traits + inheritance + evaluation config
│   ├── mira-ocean.yaml        # OCEAN (Big Five) personality
│   ├── mira-disc.yaml         # DISC preset (the_analyst)
│   ├── mira-jungian.yaml      # Jungian preset (INTJ)
│   ├── disc-detailed.yaml     # DISC with explicit numeric values
│   ├── jungian-detailed.yaml  # Jungian with explicit numeric values
│   ├── hybrid-example.yaml    # OCEAN base + trait overrides
│   ├── hybrid-jungian.yaml    # Jungian base + trait overrides
│   ├── mira-mood.yaml         # Dynamic mood states
│   ├── mira-modes.yaml        # Behavioral modes (formal, crisis, etc.)
│   ├── mira-dynamics.yaml     # Dynamic personality with mood/mode shifting + memory influences
│   ├── composition-example.yaml  # Overrides + composition conflict resolution
│   ├── voice-and-memory.yaml  # Voice settings + detailed memory config
│   ├── storyteller.yaml       # Narrative identity + voice examples
│   ├── legal-advisor.yaml     # Domain-specific guardrails + behavioral modes
│   ├── support-team.yaml      # Agent relationships + escalation paths
│   ├── crisis-responder.yaml  # Mood transitions + escalation channels
│   ├── executive-assistant.yaml  # Autonomy thresholds + interaction config
│   └── ...                    # + minimal, builder-generated, multi-mixin, etc.
└── teams/               # Multi-agent team with governance
```

## Schema

JSON Schemas for IDE autocompletion: [`schemas/v1.0/schema.json`](schemas/v1.0/schema.json) (agents) and [`schemas/v2.0/schema.json`](schemas/v2.0/schema.json) (teams).

## Development

```bash
git clone https://github.com/PersonaNexus/personanexus.git
cd personanexus
uv sync --dev
uv run pytest
uv run ruff check src/ tests/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and code style guidelines.

## Related Projects

| Project | Description |
|---------|-------------|
| [**AgentForge**](https://github.com/PersonaNexus/AgentSkillFactory) | Transform job descriptions into deployable PersonaNexus agent blueprints — extracts skills, maps traits, and outputs ready-to-use identities. |
| [**Voice Packs**](https://github.com/PersonaNexus/voice-packs) | Weight-level personality adapters (LoRA) that encode authorial voice into model weights. 13 pre-trained packs, proven to reduce personality drift by up to 49% vs prompt-only. [Adapters on HuggingFace](https://huggingface.co/jcrowan3/voice-pack-adapters). |

## Trademark Notice

PersonaNexus uses established public-domain personality frameworks:

- **OCEAN (Big Five)** is based on the Five Factor Model, which is public-domain academic research.
- **DISC** refers to the behavioral model by William Moulton Marston (1928), which is in the public domain. "DiSC" (stylized) is a registered trademark of Wiley. PersonaNexus is not affiliated with or endorsed by Wiley.
- **Jungian types** refers to Carl Jung's typological theory (1921), which is in the public domain. "MBTI" and "Myers-Briggs" are registered trademarks of The Myers-Briggs Company. PersonaNexus is not affiliated with or endorsed by The Myers-Briggs Company.

## License

MIT — see [LICENSE](LICENSE).
