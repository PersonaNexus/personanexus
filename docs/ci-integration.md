# CI integration

PersonaNexus ships a reusable composite GitHub Action and a starter pre-commit
configuration so any repository that stores identity YAML files can gate
changes on the same checks PersonaNexus uses internally.

There are two pieces:

- **GitHub Action** at `PersonaNexus/personanexus/.github/actions/personanexus-check`
  for CI on PRs and pushes.
- **Pre-commit config** at [`examples/ci/.pre-commit-config.yaml`](../examples/ci/.pre-commit-config.yaml)
  for local pre-commit hooks.

Both wrap the same CLI commands (`personanexus doctor`, `personanexus lint`),
so behavior is consistent between local commits and CI.

## GitHub Action

### Quick start

Drop the sample workflow at [`examples/ci/github-workflow.yml`](../examples/ci/github-workflow.yml)
into your repo as `.github/workflows/personanexus.yml`:

```yaml
name: PersonaNexus
on:
  pull_request:
    branches: [main]
jobs:
  personanexus-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: PersonaNexus/personanexus/.github/actions/personanexus-check@main
        with:
          path: agents
          check-compile: 'true'
          compile-target: 'text,anthropic'
```

Pin `@main` to a tag (e.g. `@v1`) once you have settled on a release version.

### Inputs

| Input | Default | Purpose |
|---|---|---|
| `path` | `agents` | Directory (or single file) of identities to check. |
| `python-version` | `3.12` | Python version installed in the runner. |
| `personanexus-version` | _(latest)_ | Pin a specific release (e.g. `1.2.0` or `>=1.0,<2`). |
| `search-path` | _(empty)_ | Newline-separated extra resolver paths for archetypes/mixins. |
| `lint-severity` | `warning` | Minimum lint severity to surface (`info`, `warning`, `error`). |
| `fail-on-lint` | `false` | If `true`, treat any `[WARNING]`/`[ERROR]` as a failure. |
| `check-compile` | `false` | Also verify identities compile to the targets below. |
| `compile-target` | `text` | Comma-separated targets (e.g. `text,anthropic`). |
| `token-budget` | `3000` | Token budget passed to the compiler when `check-compile=true`. |

### Common repo layouts

#### Layout A — everything under `agents/`

```
my-repo/
├── agents/
│   ├── support-bot.yaml
│   └── research-assistant.yaml
└── .github/workflows/personanexus.yml
```

```yaml
- uses: PersonaNexus/personanexus/.github/actions/personanexus-check@main
  with:
    path: agents
```

#### Layout B — identities and shared archetypes side by side

```
my-repo/
├── personas/
│   ├── support-bot.yaml
│   └── research-assistant.yaml
└── shared/
    ├── archetypes/
    └── mixins/
```

```yaml
- uses: PersonaNexus/personanexus/.github/actions/personanexus-check@main
  with:
    path: personas
    search-path: |
      shared/archetypes
      shared/mixins
```

#### Layout C — single identity file

```yaml
- uses: PersonaNexus/personanexus/.github/actions/personanexus-check@main
  with:
    path: agents/my-agent.yaml
    check-compile: 'true'
```

## Pre-commit hook

Install pre-commit once (`pip install pre-commit`), copy
[`examples/ci/.pre-commit-config.yaml`](../examples/ci/.pre-commit-config.yaml)
to your repo root, and run:

```bash
pre-commit install
```

The starter hooks scope themselves to `agents/**/*.yaml`. Edit the `files:`
regex if your identities live somewhere else.

The hooks assume `personanexus` is on your `PATH` (install with
`pip install personanexus` or via your project's dependency manager). For
reproducibility, prefer pinning the version in the same place you pin the
rest of your tooling (`pyproject.toml`, `requirements.txt`, `uv.lock`, etc.).

## What runs under the hood

The composite action does three things in order:

1. Installs PersonaNexus from PyPI.
2. Runs `personanexus doctor <path>` for repo-wide health checks
   (broken inheritance, schema drift, optionally compile checks).
3. Runs `personanexus lint <file>` for each identity YAML found, honoring
   the `lint-severity` input.

If `check-compile=true`, the doctor step also verifies each identity
compiles to the configured target(s) without errors.

## Troubleshooting

- **`No YAML files found under <path>`** — adjust the `path` input or move
  your identities under `agents/`.
- **`Could not resolve archetype/mixin`** — pass the directory that holds
  shared building blocks via `search-path` (one path per line).
- **Lint passes locally but fails in CI** — the action installs the latest
  PersonaNexus release by default. Pin `personanexus-version` to match the
  version you use locally.
