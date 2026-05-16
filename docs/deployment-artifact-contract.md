# PersonaNexus Public Deployment Artifact Contract

**Initiative:** 0a10bb0b — PersonaNexus public deployment contract and Studio export path  
**Packet:** e524c8b2 — Define the public PersonaNexus deployment artifact contract  
**Author:** Builder  
**Date:** 2026-05-15  
**Status:** Architecture analysis — ready for implementation review

---

## 1. Purpose

This document defines the **public deployment artifact contract** for PersonaNexus: what artifacts the project produces, who consumes them, what stability each artifact carries, and how Studio export fits into the public deployment picture.

It is the authoritative reference for:
- What is versioned, released, and considered stable
- What consumers can depend on across releases
- How Studio export artifacts relate to the broader deployment surface
- What implementation work is needed to reach a clean, shippable contract

---

## 2. Artifact Inventory (current state)

| Artifact | Location | Consumer | Public? | Versioned? |
|----------|----------|----------|---------|-----------|
| Python package (`personanexus`) | PyPI | Developers, AgentForge | ✅ | ✅ semver |
| CLI (`personanexus` command) | ships with package | Power users, CI | ✅ | ✅ (with package) |
| JSON Schema v1.0 | `schemas/v1.0/schema.json` | IDE tooling, validators | ✅ (in repo) | 🔴 no independent hosting |
| JSON Schema v2.0 | `schemas/v2.0/schema.json` | IDE tooling, validators | ✅ (in repo) | 🔴 no independent hosting |
| Website (personanexus.ai) | `docs/` → Netlify | Everyone | ✅ | 🟡 auto-deploy on main |
| Studio (local) | `web/studio.py` | Local users | 🔴 local only | 🔴 not deployed |
| Studio export artifacts | Studio download buttons | Studio users | 🔴 local only | 🟡 format-versioned |
| Packs (skills + galleries) | `packs/` | OpenClaw users | 🔴 partial (ClawHub?) | 🔴 no contract |
| Skill ZIPs | repo root (`*.zip`) | OpenClaw users | 🟡 (in repo) | 🔴 no contract |
| CHANGELOG | `CHANGELOG.md` | Contributors, users | ✅ | ✅ |

**Summary of gaps:**
- Schema files have no stable public URL — consumers must pin a git ref
- Studio is not publicly hosted — export artifacts exist only in local sessions
- Packs and skill ZIPs have no distribution contract or versioning policy
- No artifact signing or integrity verification

---

## 3. Tier Classification

### Tier 1 — Stable, Semver-governed (break only on major)

These artifacts are the public API. A breaking change requires a major version bump.

- **Python package public API**: `AgentIdentity`, `compile_identity()`, `parse_identity_file()`, all `types.py` Pydantic models, CLI commands (`validate`, `compile`, `build`, `lint`, `eval`, `diff`, `analyze`)
- **JSON Schema v1.0** (frozen): `schema_version: "1.0"` files are valid forever against this schema; no changes permitted
- **Compiled output formats**: the structure of outputs from `compile_identity(target=...)` for `text`, `anthropic`, `openclaw`, `soul`, `json` targets — consumers (AgentForge, OpenClaw, Streamlit Studio) depend on these

### Tier 2 — Stable, minor-version additions only (no removal without deprecation cycle)

- **CLI flag signatures**: existing flags on stable commands don't disappear without a deprecation notice in at least one minor release
- **JSON Schema v2.0**: additions allowed in minor releases; removals/renames require a v3.0 or explicit deprecation marker
- **`compile_identity()` targets**: existing targets (`langchain`, `crewai`, `autogen`, `markdown`) are supported but may gain new fields in minor releases

### Tier 3 — Experimental / no stability guarantee

- **Studio UI** (`web/studio.py`, `web/app.py`): layout, component names, and session state keys can change freely
- **`evolve_export` / `dynamics` / `drift`**: useful features, not yet promoted to Tier 1 — may change API shape
- **Packs / Skills**: format and distribution not yet contracted
- **`--apply-evolution` flag**: experimental, may change semantics

---

## 4. Studio Export Path Contract

### 4.1 What Studio currently exports

The Studio exposes four download buttons per agent (implemented in `web/studio.py:_render_export_panel`):

| Button label | Format | MIME | Extension |
|---|---|---|---|
| Identity (.yaml) | raw source YAML | text/yaml | .yaml |
| Prompt (.txt) | `compile_identity(target="text")` | text/plain | .txt |
| Anthropic (.txt) | `compile_identity(target="anthropic")` | text/plain | .txt |
| OpenClaw (.json) | `compile_identity(target="openclaw")` | application/json | .json |

Note: `soul`, `json`, `markdown`, `langchain`, `crewai`, `autogen` targets exist in the compiler but are not yet surfaced in Studio export.

### 4.2 Gaps in the current Studio export path

1. **No export manifest** — there is no file that records which identity was exported, at what schema version, with which compile target, and at what timestamp. Downstream tools (AgentForge, OpenClaw) receive a bare YAML or JSON file with no provenance.

2. **No export bundle** — users must click four separate buttons. A single "Export deployment bundle" action should produce a ZIP containing:
   - `identity.yaml` (source)
   - `system-prompt.txt` (text target)
   - `openclaw-config.json` (openclaw target)
   - `soul.md` + `style.md` (soul target)
   - `manifest.json` (provenance record — see §4.3)

3. **No hosted Studio** — the export path only exists for users running Studio locally. Public users at personanexus.ai see the static marketing page, not an interactive Studio. A hosted Studio (Streamlit Community Cloud or equivalent) would expose export to everyone.

4. **Export targets not surfaced** — `soul` target (SOUL.md + STYLE.md) is a key output for OpenClaw agents but not available in Studio export panel. Neither is `markdown` or `json` (the structured JSON with prompt layers).

5. **No schema version in export filename** — a file named `scout_identity.yaml` gives no indication of schema version; downstream tools must parse the YAML to find `schema_version`.

### 4.3 Export Manifest Contract

Each deployment bundle should include `manifest.json`:

```json
{
  "personanexus_version": "1.5.0",
  "schema_version": "1.0",
  "exported_at": "2026-05-15T19:00:00Z",
  "source_file": "scout.yaml",
  "identity_id": "agt_scout_001",
  "identity_name": "Scout",
  "compile_targets": ["text", "anthropic", "openclaw", "soul"],
  "bundle_contents": [
    "identity.yaml",
    "system-prompt.txt",
    "anthropic-prompt.txt",
    "openclaw-config.json",
    "soul.md",
    "style.md",
    "manifest.json"
  ],
  "compile_warnings": [],
  "sha256": {
    "identity.yaml": "<hash>",
    "openclaw-config.json": "<hash>"
  }
}
```

This manifest is the provenance record. AgentForge and OpenClaw can consume it to confirm they received the right artifact at the right version.

### 4.4 Schema URL Contract

Schema files need a stable public URL so tools can reference them without pinning a git hash.

**Proposed canonical URLs:**

```
https://personanexus.ai/schemas/v1.0/schema.json   (frozen)
https://personanexus.ai/schemas/v2.0/schema.json   (current stable)
https://personanexus.ai/schemas/latest/schema.json  (redirect → current)
```

Implementation: add `schemas/` to the Netlify publish directory (currently only `docs/` is published). Either move schemas into `docs/schemas/` or update `netlify.toml` to serve both.

---

## 5. Public Deployment Architecture

```
                    ┌─────────────────────────────────────┐
                    │         personanexus.ai              │
                    │  (Netlify, publish: docs/)           │
                    │                                      │
                    │  /           → marketing page        │
                    │  /schemas/v1.0/schema.json → schema  │
                    │  /schemas/v2.0/schema.json → schema  │
                    │  /schemas/latest → redirect          │
                    └──────────────┬──────────────────────┘
                                   │
               ┌───────────────────┴───────────────────┐
               │                                       │
    ┌──────────▼──────────┐             ┌──────────────▼────────────┐
    │  PyPI package        │             │  Studio (hosted)           │
    │  personanexus 1.5.0  │             │  (Streamlit Cloud or equiv)│
    │                      │             │                            │
    │  Tier 1 public API   │             │  Export: 4-button panel   │
    │  + CLI               │             │  → bundle ZIP + manifest  │
    │  + all compile       │             │  → SOUL.md target added   │
    │    targets           │             │  Inputs: YAML upload,     │
    └──────────────────────┘             │  gallery browse, wizard   │
                                         └────────────────────────────┘
                    │
    ┌───────────────▼──────────────────────────────────────┐
    │  ClawHub / OpenClaw skill distribution               │
    │  (packs/ skills, versioned ZIP + pack.yaml)         │
    │  Contract: TBD (needs separate design packet)        │
    └──────────────────────────────────────────────────────┘
```

---

## 6. Breaking Change Policy

### What triggers a major version bump (X.0.0)

- Removing or renaming any `AgentIdentity` field or nested model
- Changing the output schema of any Tier 1 compile target
- Removing a CLI command or flag from a stable command
- Changing `schema_version: "1.0"` validation behavior

### What is permitted in minor versions (1.X.0)

- New optional fields in `AgentIdentity` (with defaults)
- New compile targets
- New CLI commands
- New schema v2.0 optional fields
- Adding fields to OpenClaw JSON output
- Changes to Tier 3 (experimental) features without notice

### What is permitted in patch versions (1.0.X)

- Bug fixes that don't change the output of stable compile targets
- Documentation corrections
- Test-only changes

---

## 7. Implementation Work Required

Listed in priority order. Each item maps to a potential follow-on packet.

### P0 — Schema public hosting (low effort, high leverage)
- Move or symlink `schemas/v1.0/` and `schemas/v2.0/` into `docs/schemas/`
- Update `netlify.toml` if needed
- Add `$schema` field to all example YAML files pointing to the hosted URL
- **Effort:** ~2h | **Owner:** Coder

### P0 — Export manifest in Studio bundle (medium effort)
- Implement `manifest.json` generation in `_render_export_panel`
- Add "Export deployment bundle" ZIP button alongside individual format buttons
- Add SOUL.md target to Studio export panel
- **Effort:** ~4h | **Owner:** Coder | **Files:** `web/studio.py`, `web/components.py`

### P1 — Hosted Studio deployment
- Deploy `web/` to Streamlit Community Cloud (or Railway / Render)
- Add "Open Studio →" link from personanexus.ai homepage
- Ensure schema import works in hosted environment (no local filesystem YAML required for the gallery — embed examples)
- **Effort:** ~1 day | **Owner:** Forge (infra) | **Decision needed:** which hosting platform

### P1 — Stability tiers documented publicly
- Add `docs/stability.md` based on §3 of this document
- Surface in README under "API stability"
- **Effort:** ~2h | **Owner:** Coder

### P2 — Pack/skill distribution contract
- Define `pack.yaml` schema + versioning policy for `packs/`
- Determine ClawHub vs. GitHub Releases vs. npm-style registry
- **Effort:** design packet needed | **Owner:** Forge

### P2 — Schema version in export filenames
- Change `{slug}_identity.yaml` → `{slug}_identity_v{schema_version}.yaml`
- Add `personanexus_version` field to compiled OpenClaw JSON
- **Effort:** ~1h | **Owner:** Coder

---

## 8. Success Criteria (when the contract is "done")

A user or downstream tool can:

1. **Point a JSON Schema validator** at `https://personanexus.ai/schemas/v2.0/schema.json` and validate a YAML file without touching the repo
2. **Download a deployment bundle** from Studio that includes identity YAML + compiled outputs + a `manifest.json` recording provenance
3. **Read `docs/stability.md`** to know which APIs are safe to depend on across releases
4. **Integrate with AgentForge** using the OpenClaw JSON artifact with confidence that its structure won't change in a minor version

---

## 9. Decisions Needed Before Implementation

1. **Studio hosting platform** — Streamlit Community Cloud (free, easy) vs. Railway/Render (more control)? This unblocks P1.
2. **Schema URL structure** — move schemas into `docs/schemas/` (simplest) or update Netlify config to serve two publish dirs?
3. **Pack distribution** — ClawHub (OpenClaw registry) or GitHub Releases with a manifest? This requires a separate architecture decision.
4. **`manifest.json` sha256 scope** — hash just the YAML, or all bundle artifacts?

---

_Builder, 2026-05-15_
