# PersonaNexus Backlog

A working backlog of product, platform, and go-to-market ideas that Coder and Forge can pick up.

## How to use this backlog

- **Coder** should take scoped items with clear file boundaries, tight acceptance criteria, and low architectural risk.
- **Forge** should take cross-cutting work, new subsystems, bigger product bets, and anything that needs design decisions across CLI, schema, runtime, tests, and web.
- Default output for execution should be a branch, commit, and PR.

## Prioritization lens

Prioritize ideas that do at least one of these:
- make PersonaNexus easier to adopt quickly
- make identities easier to trust, test, and compare
- create a stronger wedge into OpenClaw / multi-agent workflows
- open a path to a paid hosted product, registry, or team workflow

---

## P0, Near-term, Coder-ready

### 1) `personanexus doctor` for repo-wide checks
**Owner:** Coder  
**Why now:** The CLI has strong single-file commands, but teams need one command that scans a repo and tells them what is broken, missing, stale, or inconsistent. This is a strong OSS adoption feature.

**What it should do**
- recursively discover PersonaNexus files in a repo
- run validate + lint + optional compile checks
- detect unresolved `extends` / `mixins`
- optionally check for compile drift against generated artifacts
- print a clean summary and CI-friendly exit code

**Likely touch points**
- `src/personanexus/cli.py`
- `src/personanexus/validator.py`
- `src/personanexus/linter.py`
- new tests under `tests/`

**Acceptance criteria**
- `personanexus doctor .` works on a repo, not just one file
- non-zero exit when blocking issues exist
- human-readable and machine-usable summary modes

---

### 2) GitHub Action + pre-commit starter kit
**Owner:** Coder  
**Why now:** PersonaNexus becomes much more usable if validation/linting can be dropped into any repo in minutes.

**What it should include**
- reusable GitHub Action for validate/lint/compile checks
- pre-commit hook example
- docs for common repo layouts
- example CI output in README/docs

**Likely touch points**
- `.github/workflows/`
- `README.md`
- `docs/`
- maybe a `scripts/` helper

**Acceptance criteria**
- sample workflow runs in CI on PRs
- pre-commit example works locally
- docs show copy/paste setup

---

### 3) Finish the `migrate` command
**Owner:** Coder  
**Why now:** `migrate` exists in the CLI surface but is explicitly marked future use. That creates a product promise gap.

**What it should do**
- migrate between supported schema versions
- explain what changed
- preserve comments/structure as much as practical
- offer dry-run and diff output

**Likely touch points**
- `src/personanexus/cli.py`
- new migration logic under `src/personanexus/`
- `schemas/`
- tests

**Acceptance criteria**
- supported migrations actually run end-to-end
- dry-run shows intended changes
- migrated files validate cleanly

---

### 4) Compiled prompt diff mode
**Owner:** Coder  
**Why now:** The repo already has identity diffing, but users also need to see how a trait or YAML change alters the compiled system prompt.

**What it should do**
- compare two identities and show compiled prompt differences
- optionally diff by target (`text`, `openai`, `anthropic`, `soul`, `openclaw`)
- explain which trait/config changes drove the output delta

**Likely touch points**
- `src/personanexus/diff.py`
- `src/personanexus/compiler.py`
- `src/personanexus/cli.py`
- tests

**Acceptance criteria**
- one command shows YAML diff and compiled output diff together
- works across at least 2 compile targets

---

### 5) Promote the OpenClaw migrator into a supported command
**Owner:** Coder  
**Why now:** There is already an `openclaw-migrator.py` script in the repo. Turning it into a first-class command creates a much stronger bridge from existing OpenClaw agent setups into PersonaNexus.

**What it should do**
- wrap current migration logic in the main CLI
- add tests and docs
- support OpenClaw agent directories and shared task board patterns
- produce predictable output directories

**Likely touch points**
- `skills/personanexus/scripts/openclaw-migrator.py`
- `src/personanexus/cli.py`
- docs/examples/tests

**Acceptance criteria**
- one supported command can migrate a real OpenClaw workspace
- output validates cleanly
- migration guide exists in docs

---

## P1, Product improvements, good Forge work

### 6) Identity evaluation harness
**Owner:** Forge  
**Why now:** PersonaNexus is strongest when users can prove an identity behaves the way they intended, not just validate YAML shape.

**What it should do**
- define test conversations / scenarios for an identity
- score persona consistency, instruction adherence, safety/guardrails, and tone
- compare two identity versions side-by-side
- optionally run in CI

**Why it matters commercially**
This is the bridge from “persona config” to “persona quality assurance,” which is much more defensible and sellable.

**Acceptance criteria**
- users can define eval scenarios in YAML/JSON
- results show pass/fail plus score breakdown
- version A vs B comparisons are supported

---

### 7) Identity Lab project save/load/version history
**Owner:** Forge  
**Why now:** The Streamlit UI is useful, but it feels more like a demo until users can save drafts, compare versions, and reopen work.

**What it should do**
- save working identities from the web app
- reopen prior drafts
- compare versions visually
- export shareable artifacts

**Likely touch points**
- `web/app.py`
- `web/wizard.py`
- `web/analyze.py`
- new storage layer or local project model

**Acceptance criteria**
- save, reopen, and compare flows work in the web UI
- no accidental overwrites
- export path is obvious

---

### 8) Team graph and multi-agent simulator UI
**Owner:** Forge  
**Why now:** PersonaNexus has team schema support, compatibility logic, and relationship concepts. A visual simulator would make team design much more tangible.

**What it should do**
- render team structure and relationships
- simulate agent interactions/workflows
- show where authority, compatibility, or guardrails conflict
- help users design better multi-agent teams

**Why it matters commercially**
This is a strong differentiator versus “prompt template” tools.

**Acceptance criteria**
- team YAML can be visualized in the web app
- at least one simulation mode exists
- compatibility/conflict hotspots are surfaced clearly

---

### 9) Runtime API / SDK for dynamic identities
**Owner:** Forge  
**Why now:** Dynamic personality is compelling, but adoption expands if teams can call a clean runtime API instead of wiring internals themselves.

**What it should do**
- expose load, adjust, simulate, and persist behavior through a Python service layer or lightweight API
- make user-state persistence easier to plug into apps
- support context-driven recompilation cleanly

**Acceptance criteria**
- clear runtime API surface exists
- docs include example app integration
- dynamic session state can be persisted and reloaded

---

### 10) Shareable identity cards and public example gallery
**Owner:** Forge  
**Why now:** PersonaNexus needs a better viral/demo surface. Right now the examples exist, but they are not yet packaged as an experience people want to share.

**What it should do**
- generate beautiful identity summary pages/cards
- browse examples by role, archetype, framework, and traits
- deep-link from README/site into those examples

**Why it matters commercially**
Better shareability improves open-source growth and makes a hosted product more plausible.

**Acceptance criteria**
- examples are browsable in the web UI or static docs site
- identity pages are linkable and readable without local setup

---

## P2, Bigger bets, likely Forge-led

### 11) PersonaNexus Registry / Pack ecosystem
**Owner:** Forge  
**Why now:** There is already a natural path toward reusable archetypes, mixins, and domain packs. A registry turns PersonaNexus from a framework into an ecosystem.

**What it could include**
- installable archetype/mixin packs
- versioning and dependency metadata
- private and public registries
- pack trust/verification rules

**Why it matters commercially**
This is a real product surface, especially for teams and enterprise usage.

---

### 12) PersonaOps for production teams
**Owner:** Forge  
**Why now:** Once teams adopt PersonaNexus, they will want observability and governance, not just configuration.

**What it could include**
- drift/change history across deployed identities
- approval workflows for persona changes
- audit trail of guardrail edits
- deployment policy checks

**Why it matters commercially**
This opens an enterprise operations angle beyond pure open-source tooling.

---

## Suggested execution order

1. `personanexus doctor`
2. GitHub Action + pre-commit starter
3. compiled prompt diff mode
4. OpenClaw migrator as first-class command
5. identity evaluation harness
6. Identity Lab save/load/version history
7. team graph + simulator
8. runtime API / SDK

## Good first tickets to spin out immediately

If we want to create actual tickets for Coder/Forge next, start with these:
- Coder: `personanexus doctor`
- Coder: GitHub Action + pre-commit starter
- Coder: compiled prompt diff mode
- Forge: identity evaluation harness
- Forge: Identity Lab save/load/version history
