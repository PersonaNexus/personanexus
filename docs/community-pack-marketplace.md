# Community Pack Marketplace — MVP Design

**Status:** Design, pre-implementation
**Target:** v1.5.0 (after Persona Evolution Engine lands)
**Depends on:** `docs/persona-evolution-engine.md` — pack format reuses evolution export
**Owner:** Forge

## Problem

PersonaNexus ships with a schema + compiler but no shared content library.
Users who build good personas/boards have no way to share them. Without a
marketplace, the catalog grows linearly with core maintainers. With one,
it can grow with the community.

## Solution

A **GitHub-native marketplace**: `/packs/` folder in the main repo, PR-based
contributions, GitHub Action validation, static gallery page. No backend.

Built on the same content model as Evolution Engine so personas, evolutions,
and packs are interchangeable artifacts.

## Architecture

```
/packs/
├── official/                          # curated by maintainers
│   ├── boards/
│   │   └── generic-board/
│   │       ├── pack.json
│   │       ├── persona.yaml
│   │       └── README.md
│   └── personas/
│       └── chief-of-staff/
│           ├── pack.json
│           ├── persona.yaml
│           └── README.md
├── community/                         # PR-contributed
│   └── <author>/
│       └── <pack-name>/
│           ├── pack.json
│           ├── persona.yaml
│           ├── .evolution/            # optional evolution deltas
│           │   └── deltas.json
│           └── README.md
└── _gallery/
    ├── index.json                     # auto-generated catalog
    └── README.md                      # links to website gallery
```

## Pack Metadata (`pack.json`)

```json
{
  "name": "startup-board",
  "author": "jcrowan3",
  "version": "1.0.0",
  "license": "MIT",
  "description": "5-member strategic board for startup founders — PM, Sales, Finance, Legal, Product.",
  "tags": ["board", "startup", "strategy", "advisory"],
  "category": "boards",
  "requires_personanexus": ">=1.5.0",
  "evolved_from": "official/boards/generic-board@1.2.0",
  "evolution_deltas": ".evolution/deltas.json",
  "homepage": "https://github.com/jcrowan3/personanexus",
  "example_usage": "README.md#example",
  "created": "2026-04-05",
  "stats": {
    "install_count": 0,
    "stars": 0
  }
}
```

Required fields: `name`, `author`, `version`, `license`, `description`, `category`, `requires_personanexus`.
Optional: `evolved_from`, `evolution_deltas`, `stats`, `homepage`.

## CLI

```bash
# Browse catalog (reads from GitHub or cached local /packs/)
personanexus pack list
personanexus pack list --category boards
personanexus pack list --tag startup
personanexus pack search "chief of staff"

# View pack details before installing
personanexus pack show startup-board
personanexus pack show jcrowan3/startup-board  # namespaced form

# Install (fetches from GitHub, caches to ~/.personanexus/packs/)
personanexus pack install startup-board
personanexus pack install jcrowan3/startup-board --version 1.0.0
personanexus pack install startup-board --dry-run  # preview compiled prompt

# List installed
personanexus pack installed

# Update / remove
personanexus pack update startup-board
personanexus pack remove startup-board

# Export your persona as a pack (submit PR)
personanexus pack create elena --output ./my-pack/
personanexus pack publish ./my-pack/  # creates PR to main repo
```

## Namespacing

Official packs: `official/boards/generic-board` or shorthand `generic-board`
Community packs: `<author>/<name>` — e.g. `jcrowan3/startup-board`

When ambiguous, CLI prefers official. User can force community via namespace.

## GitHub Action Validations

`.github/workflows/validate-pack.yml` runs on PRs touching `/packs/community/`:

| Check | Required |
|-------|----------|
| `pack.json` present and parses | Yes |
| `persona.yaml` present and parses | Yes |
| Directory name matches `author/pack-name` in metadata | Yes |
| Version is valid semver | Yes |
| `persona.yaml` validates against PersonaNexus schema | Yes |
| `persona.yaml` compiles successfully to a system prompt | Yes |
| No restricted fields (e.g. embedded tokens, shell commands) | Yes |
| `README.md` exists with non-empty description | Yes |
| `evolved_from` reference exists if present | Yes |
| Version hasn't been published before (no overwrites) | Yes |
| Compiled prompt under 8000 tokens | Warning |
| At least one example usage in README | Warning |

On failure: PR gets a comment with the specific errors. Contributor fixes and pushes.

## Trust Model

**Personas compile to system prompts that control agent behavior.** A malicious
pack could inject instructions. Mitigations:

1. **`--dry-run` shows the compiled prompt** before any install completes.
2. **Prompt injection scan** in the GitHub Action (flags suspicious patterns:
   "ignore previous instructions", "you are now", URL fetching, tool-use).
3. **First-party vs community badge** in the gallery — official packs have a
   stronger guarantee.
4. **No code execution in packs** — packs are YAML + JSON + Markdown only. No
   scripts, no hooks, no importable Python.

## Installation Flow

```
personanexus pack install jcrowan3/startup-board
  ├── Resolve: GitHub API → /packs/community/jcrowan3/startup-board/
  ├── Download: pack.json, persona.yaml, deltas.json, README.md
  ├── Verify: re-validate against schema locally
  ├── Show: author, version, description, compiled prompt preview
  ├── Prompt: "Install to ~/.personanexus/packs/ ? [y/N]"
  ├── Copy: to local cache
  ├── Optionally: copy persona.yaml to working dir
  └── Log: ~/.personanexus/pack-install.log
```

## Gallery (static page)

Generated from `/packs/_gallery/index.json`, which is rebuilt by the GitHub
Action on merge. Gallery page lives at `personanexus.ai/packs`.

Shows:
- Search + tag filters
- Grid of packs with author, description, install count
- Click through to detail page (README + pack.json + persona.yaml preview)
- Copy-paste install command

No backend. Static JSON + JavaScript filter.

## Relationship to Evolution Engine

A pack is **a persona optionally with evolution deltas applied**. This means:

- **Export an evolved persona → publish as a pack** — `personanexus evolve export elena --as-pack` bundles the base YAML + evolution deltas into a pack directory ready to PR.
- **Install a pack, enable evolution** — the pack's evolution deltas become the starting point for further user evolution.
- **Evolution chain visibility** — the `evolved_from` field lets the gallery show "this pack was evolved from generic-board v1.2.0".

This keeps the content model unified: **persona + deltas is the only artifact.**

## MVP Scope (v1.5.0)

**In scope:**
- `/packs/` directory structure with 3 official seed packs
- `pack.json` schema + validation
- GitHub Action for PR validation
- CLI commands: `list`, `show`, `install`, `installed`, `remove`, `search`
- `pack create` (export working persona as pack) + `pack publish` (create PR)
- Static gallery index JSON (auto-generated by Action)
- 10+ unit tests + integration test for GitHub fetch

**3 official seed packs at launch:**
1. `official/boards/strategic-advisory-council` (based on Sentinel's BOD idea)
2. `official/personas/chief-of-staff` (Nova-style)
3. `official/frameworks/ocean-disc-bridge` (example of a framework pack)

**Deferred to v1.6.0:**
- Web gallery page on personanexus.ai
- One-click install from gallery (browser extension or copy-link UX)
- Telemetry / install counts (opt-in)
- Community ratings / stars

**Deferred to future:**
- Pack dependency system (one pack depends on another)
- Versioned pack upgrades with migration notes
- Private pack registries for teams

## Non-Goals

- Backend service / database
- User accounts (GitHub identity is enough)
- Paid packs / monetization
- Arbitrary code in packs

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Low-quality packs clutter catalog | Required README, schema validation, tag filtering |
| Prompt injection via community packs | Pattern scan in Action, `--dry-run`, official/community badge |
| Duplicate/conflicting pack names | Namespace = `<author>/<name>`, Action checks uniqueness |
| Breaking changes to schema strand old packs | `requires_personanexus` version gate, deprecation warnings |
| Contributor friction | `pack create` + `pack publish` CLI automates 90% of PR prep |
| Gallery becomes stale / out-of-date | Action regenerates `_gallery/index.json` on every merge |

## Test Plan

**Unit:**
- pack.json schema validation
- Directory name ↔ metadata name match
- Semver parsing
- Injection pattern detection

**Integration:**
- `pack install` fetches from GitHub raw content and caches locally
- `pack create` roundtrips: export → install → compile → matches original
- Action validates a known-good PR passes, known-bad PR fails

**E2E:**
- Submit mock PR with invalid pack → Action comments with specific errors
- Submit mock PR with valid pack → Action passes, gallery updates on merge

## Open Questions

1. **Install cache location** — `~/.personanexus/packs/` or project-local?
   Proposal: both. Global cache, project can symlink/copy.

2. **Offline install** — should `personanexus pack install` work offline if
   the pack is cached? Proposal: yes, `--offline` flag, defaults to fresh fetch.

3. **Fork workflow** — if I want to modify a community pack, what's the UX?
   Proposal: `pack fork <name>` copies to `community/<my-author>/<name>-fork/`
   and opens a draft PR.
