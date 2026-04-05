# Persona Evolution Engine — MVP Design

**Status:** Design, pre-implementation
**Target:** v1.5.0
**Owner:** Forge

## Problem

PersonaNexus personas are static. Users want agents that adapt to their style
over time without losing the declarative identity guarantees PersonaNexus
provides (schema, governance, audit trail).

## Solution

A **two-loop evolution system** layered on the existing `Evolution` governance
schema (types.py already has `immutable_fields`, `runtime_mutable_fields`,
`drift_detection`).

### Loop 1 — Soft Evolution (prompt-level)
- Adjusts **tone/phrasing guidance** in the compiled prompt only.
- Does NOT touch OCEAN/DISC/Jungian trait scores.
- Low-risk, fast feedback cycle.
- Good for "be warmer", "more concise", "less formal".

### Loop 2 — Hard Evolution (trait-level)
- Adjusts OCEAN/DISC/Jungian scores within ±0.3 bounds.
- Gated behind **consensus** (≥3 consistent signals pointing same direction).
- Writes to audit log with full provenance.
- Good for "genuinely too aggressive" — structural personality drift.

## Architecture

```
┌─────────────────┐
│ Conversation    │
│ transcripts     │───┐
└─────────────────┘   │
                      ▼
              ┌───────────────────┐
              │ LLM-as-judge      │ (nightly)
              │ proposes deltas   │
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐
              │ Candidate queue   │ ← manual feedback also lands here
              │ .evolution/       │   ("too aggressive", thumbs down)
              │ candidates.jsonl  │
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐
              │ User reviews      │ (CLI or UI)
              │ accept/reject/edit│
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐
              │ Apply to persona  │
              │ .evolution/       │
              │ <name>.json       │
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐
              │ Compile with      │
              │ evolution deltas  │
              │ applied           │
              └───────────────────┘
```

## YAML Schema (new, added to existing personas)

```yaml
evolution:
  enabled: false                  # default off
  mode: soft                      # soft | hard | both
  learning_rate: medium           # low (±0.05) | medium (±0.15) | high (±0.3)
  consensus_threshold: 3          # min aligned signals before hard evolution
  protected_traits:               # never change these
    - core_values
    - ethics
  judge_model: gemma4:e4b         # local Ollama model for LLM-as-judge
  review_mode: prompt             # prompt | auto — user approval required?
```

## Evolution Log Format (`.evolution/<persona>.json`)

```json
{
  "persona": "elena",
  "version": 3,
  "base_yaml_hash": "sha256:abc123...",
  "created": "2026-04-01T12:00:00Z",
  "last_updated": "2026-04-05T09:15:00Z",
  "soft_deltas": {
    "tone_guidance": "Be slightly warmer in openings. Avoid imperatives."
  },
  "hard_deltas": {
    "agreeableness": {"delta": 0.15, "applied_at": "2026-04-03T..."},
    "conscientiousness": {"delta": -0.10, "applied_at": "2026-04-04T..."}
  },
  "adjustments": [
    {
      "id": "adj_001",
      "timestamp": "2026-04-03T08:00:00Z",
      "type": "hard",
      "trait": "agreeableness",
      "change": 0.15,
      "reason": "user: more empathetic",
      "source": "manual_feedback",
      "signals_supporting": 3,
      "signals_opposing": 0
    }
  ],
  "rejected_candidates": [
    {"trait": "openness", "change": -0.5, "reason": "exceeds cap", "auto_rejected": true}
  ]
}
```

## CLI

```bash
# Enable evolution on a persona
personanexus evolve enable <persona> --mode soft

# Give feedback
personanexus evolve feedback <persona> "too aggressive in that response"
personanexus evolve feedback <persona> --thumbs-down --response-id abc123

# Review pending candidates
personanexus evolve pending <persona>

# Promote candidates to active deltas
personanexus evolve promote <persona> --accept-all
personanexus evolve promote <persona> adj_001 --accept

# Roll back
personanexus evolve reset <persona>               # wipe all deltas
personanexus evolve rollback <persona> --version 2  # go back N versions

# Export evolved persona as new YAML
personanexus evolve export <persona> --output elena-v3.yaml

# Run nightly LLM-as-judge review
personanexus evolve review <persona> --transcripts <dir>
```

## Python API

```python
from personanexus.evolution import evolve_persona, apply_deltas, get_candidates

# Load persona with evolution applied
persona = load("elena.yaml", apply_evolution=True)

# Give feedback
evolve_persona("elena", feedback="too aggressive", source="user")

# Get pending candidates
candidates = get_candidates("elena")
```

## Safety Rails

1. **Caps** — per-trait change bounded by `learning_rate`:
   - low: ±0.05, medium: ±0.15, high: ±0.30
2. **Protected traits** — listed fields NEVER change
3. **Consensus** — hard evolution requires ≥N aligned signals
4. **Audit** — every change logged with source + reasoning
5. **Reversible** — `reset` wipes deltas, base YAML is source of truth
6. **Disabled by default** — opt-in per persona

## Validation Loop (bonus — wire to AI Gateway)

Use the AI Gateway's arena mode to A/B test evolution:

```bash
personanexus evolve compare <persona> \
  --pre-version 2 --post-version 3 \
  --prompts test-prompts.txt \
  --via ai-gateway
```

Sends same prompts to both versions via the Gateway's arena API, user picks
the winner, results feed back into evolution log as signals.

## MVP Scope (v1.5.0)

**In scope:**
- YAML schema extension
- `.evolution/<persona>.json` format
- Manual feedback CLI (`evolve feedback`, `evolve pending`, `evolve promote`)
- Soft evolution (prompt-level deltas)
- Hard evolution with caps + consensus
- `evolve reset` / `evolve rollback`
- Python API: `evolve_persona()`, `get_candidates()`, `apply_deltas()`
- 15+ unit tests

**Deferred to v1.6.0:**
- LLM-as-judge nightly review
- Community-shared evolution presets
- Arena-mode A/B validation

**Deferred to future:**
- Cloud sync
- Multi-user evolution (different users evolving same persona differently)

## Non-Goals

- Machine learning / gradient-based learning
- Cloud-based training
- Automatic evolution without review (unless `review_mode: auto`)
- Changing identity core (principal, role)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Over-adaptation / drift | ±0.3 max total change, caps per learning_rate |
| User confusion | "Evolution is optional, always reversible" docs + banner |
| Feedback gaming | Consensus threshold for hard changes |
| Silent personality drift | Every delta logged, `drift_detection` alerts on cumulative change |
| Breaking existing personas | Default `enabled: false`, no-op when disabled |

## Test Plan

- Unit: delta calculation, cap enforcement, consensus check
- Integration: full loop (feedback → candidate → promote → apply → compile)
- Regression: persona without evolution produces identical compiled prompt
- E2E: `evolve reset` returns to base YAML exactly
