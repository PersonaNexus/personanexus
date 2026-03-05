# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0] - 2026-03-05

### Added

- **Dynamic & Stateful Personality Layer** — mood/mode shifting engine with per-user persistent memory
  - `DynamicsConfig` YAML section with moods (trait deltas), modes (trait overrides), and triggers
  - Trigger types: `sentiment_below`, `sentiment_above`, `keyword`, `interaction_count_above`, `user_known`, `trust_above`, `trust_below`, `custom`
  - `MemoryInfluenceRule` system for permanent trait modifications based on accumulated state (e.g. "warmth +0.10 permanent" after 10 positive interactions)
  - `DynamicSession` class for managing multi-turn stateful interactions
  - Per-user JSON-file persistence backend (`MemoryBackendJSON`) with sentiment tracking, trust scores, and custom counters
  - New module: `dynamics.py` — trigger evaluation, mood/mode resolution, trait adjustment pipeline
  - New module: `memory.py` — persistent per-user state backend
  - CLI command: `personanexus simulate` — mock chat loop showing personality shifts over time
  - OpenClaw compiler now includes `dynamics` section in `personality.json` output for runtime consumption
  - Example: `mira-dynamics.yaml` — complete dynamics configuration with 4 moods, 3 modes, and 4 memory influences
  - 51 new tests covering memory backend, triggers, mood/mode resolution, trait adjustment, memory influences, pipeline, and session management

## [1.4.1] - 2026-02-28

### Changed

- Prepare codebase for open-source release
- Fix LICENSE copyright holder (was missing project name)
- Fix SECURITY.md to use dedicated security email instead of referencing pyproject.toml
- Update README test badge to reflect actual count (878 passing)
- Update CONTRIBUTING.md test count to match reality
- Add Documentation and Changelog URLs to pyproject.toml
- Clean up example agent author fields (replace personal names with "PersonaNexus")
- Fix timezone notation in example agent timestamps
- Replace hardcoded agent names in openclaw-migrator with generic role names
- Remove binary .zip artifact from version control
- Add *.zip to .gitignore

## [1.4.0] - 2026-02-22

### Added

- **Jungian 16-Type Personality Framework** — third personality framework using Carl Jung's typological theory (1921, public domain)
  - `JungianProfile` model with 4 preference dimensions (E/I, S/N, T/F, J/P)
  - All 16 type presets (INTJ through ESFP) with 0.2/0.8 preference values
  - Forward mapping: `jungian_to_traits()` — 4 dimensions to 10 personality traits
  - Reverse mapping: `traits_to_jungian()` — 10 traits to 4 dimensions (approximate)
  - `closest_jungian_type()` — Euclidean distance matching to nearest type
  - 10 role recommendation categories mapping agent roles to suggested types
  - Interactive wizard with 3 input paths: type code, role recommendation, manual dimensions
  - CLI commands: `jungian-to-traits`, `list-jungian-presets`, `jungian-recommend`
  - `show-profile` updated with Jungian display and reverse mapping
  - Full integration: analyzer, diff, validator, builder, compiler
  - Trademark disclaimer added to README
- 83 new tests (558 total)

### Changed

- **Examples overhaul** — renamed all agents from personal names to clearly-fictional example names (Ada→Mira, Maven→Finch, Saga→Fable, Sentinel→Beacon, Parker→Reed, Dr. Lena→Dr. Voss, Juris→Lex, Clarity→Prism, Harbor→Coral, Helper→Pip); renamed 6 files (ada*.yaml → mira*.yaml)
- Fixed storyteller `voice:` section to use correct schema location `communication.voice_examples` with proper field names
- Added 4 new example files: `disc-detailed.yaml` (DISC explicit values), `jungian-detailed.yaml` (Jungian explicit values), `composition-example.yaml` (overrides + composition config), `voice-and-memory.yaml` (voice settings + detailed memory)
- Added detailed evaluation config to mira.yaml (test generators, scoring rubrics, regression diff report)
- Added autonomy threshold to executive-assistant.yaml
- Added escalation channels to crisis-responder.yaml
- Documentation cleanup: removed internal strategy docs, updated CONTRIBUTING.md tooling references
- README trimmed from 967 to ~313 lines — removed duplicated sections, stale OpenClaw skill references, phantom `analyze-team` command, and version labels from feature headings
- Added `--search-path` notes to Quick Start examples
- Fixed `__version__` in `__init__.py` (was still 1.3.0)
- Synced CI coverage threshold to 82% (was 85%, mismatched pyproject.toml)
- Fixed README badges: schema version v1.0 (was v2.0), test count 558 (was 405)
- Extracted `TRAIT_ORDER` constant in `types.py` — replaces hardcoded lists in cli, builder, analyzer (DRY)
- Extracted `_collect_jungian_input()` helper in builder — eliminates 100-line duplication between Jungian and hybrid modes
- Normalized DISC preset case in validator (now uses `.lower()` like Jungian)
- Added `SECURITY.md` with vulnerability disclosure policy

## [1.3.0] - 2026-02-16

### Added

- **SOUL.md Compiler** — new `soul` compilation target that outputs SOUL.md + STYLE.md Markdown files compatible with the [soul.md](https://github.com/aaronjmars/soul.md) ecosystem and OpenClaw's bootstrap system
  - SOUL.md sections: Name, Who I Am, Worldview, Opinions, Interests, Current Focus, Influences, Vocabulary, Tensions & Contradictions, Boundaries, Pet Peeves
  - STYLE.md sections: Voice Principles, Vocabulary, Punctuation & Formatting, Context-Specific Style, Examples, Anti-Patterns
  - Boundary deduplication across guardrails and out-of-scope items

- **Narrative Identity Schema** — new optional fields for richer personality output
  - `narrative.opinions` — domain-specific takes (e.g., Technology, Management)
  - `narrative.influences` — people, books, and concepts that shaped the agent
  - `narrative.tensions` — authentic contradictions that make personalities feel human
  - `narrative.pet_peeves` — things the agent avoids or dislikes
  - `narrative.current_focus` — active projects or areas of attention
  - `narrative.backstory` — extended background beyond metadata.description
  - `communication.voice_examples` — good/bad voice calibration samples

- **Soul Analysis** — reverse-map any personality file onto all three frameworks
  - `personanexus analyze` CLI command with table and JSON output
  - Two-phase SOUL.md parser: exact template matching (confidence 1.0) + keyword fuzzy matching (confidence 0.5-0.7)
  - PersonalityJsonParser for OpenClaw personality.json files
  - IdentityYamlParser wrapping the existing resolver
  - DISC preset matching via Euclidean distance
  - Side-by-side comparison with cosine similarity scoring
  - `SoulAnalyzer` Python API: `analyze()` and `compare()`

- **Identity Lab: Analyze Mode** — third mode in the Streamlit UI
  - File upload for SOUL.md, personality.json, or YAML
  - Tabbed results: Traits, OCEAN (Big Five), DISC Profile, Raw Data
  - Confidence badges on all trait extractions
  - Side-by-side comparison with overlapping bars and delta views
  - 3-card landing page: Playground, Setup Wizard, Analyze

- New visualization components: `render_ocean_bars()`, `render_disc_bars()`, `render_comparison_bars()`, `render_confidence_badge()`
- 73 new tests (30 for SoulCompiler, 43 for Analyzer) — 322 total

## [1.2.0] - 2026-02-15

### Added

- OCEAN (Big Five) and DISC personality framework mapping
- Bidirectional trait mapping: `ocean_to_traits()`, `disc_to_traits()`, `traits_to_ocean()`, `traits_to_disc()`
- DISC presets: The Commander, The Influencer, The Steady Hand, The Analyst
- Hybrid mode: framework base + explicit trait overrides
- `personality` CLI subcommand group with `ocean-to-traits`, `disc-to-traits`, `preset`, `show-profile` (DISC personality assessment)
- Identity Lab UI with framework selectors, archetype presets, and live chat simulation

## [1.1.0] - 2026-02-14

### Added

- Identity compiler: YAML to system prompt transformation
- Multi-target compilation: text, anthropic, openai, openclaw, json
- OpenClaw personality.json compiler target
- Interactive identity builder (`personanexus build`)
- CLI commands: compile, init, migrate

## [1.0.0] - 2026-02-13

### Added

- Core YAML schema (v1.0) for AI PersonaNexus specification
- Pydantic v2 validation models for all schema sections
- Identity parser, validator, and resolver
- Archetype inheritance and mixin composition
- Conflict resolution strategies (last_wins, highest, lowest, average)
- Hard guardrail union enforcement
- CLI commands: validate, resolve
- 100 tests with 94% coverage
