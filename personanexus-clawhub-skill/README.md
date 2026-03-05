# personanexus-clawhub-skill

**PersonaNexus as an OpenClaw skill**: Build AI agent personalities using
OCEAN, DISC, and Jungian business frameworks.

This is a minimal, focused ClawHub skill extracted from the full
[PersonaNexus](https://github.com/PersonaNexus/personanexus) framework.

## Install

```bash
clawhub install personanexus
```

Or clone locally:

```bash
git clone https://github.com/PersonaNexus/personanexus-clawhub-skill.git
pip install pydantic pyyaml
```

## Quick Start

See [SKILL.md](SKILL.md) for usage instructions and API reference.

## Dynamic & Stateful Personality (v1.5)

Agents can adapt their personality in real-time based on context and evolve
over time through memory:

```python
from personanexus_skill import DynamicSession, parse_identity_file

identity = parse_identity_file("templates/dynamics-example.yaml")
session = DynamicSession(identity, user_id="user_123")
result = session.process("Hello!", sentiment=0.7)
print(result.active_mood, result.active_mode, result.adjusted_traits)
session.save()
```

Simulate personality shifts from the CLI:

```bash
python -m personanexus_skill simulate templates/dynamics-example.yaml --steps 10
```

## CLI

```bash
pip install pydantic pyyaml typer rich
python -m personanexus_skill validate agents/my-agent.yaml
python -m personanexus_skill compile agents/my-agent.yaml --target anthropic
python -m personanexus_skill init "My Agent"
python -m personanexus_skill simulate templates/dynamics-example.yaml
python -m personanexus_skill personality disc-to-traits --preset the_analyst
```

Run `python -m personanexus_skill --help` for all available commands.

## Full Framework

For advanced features (CLI, web UI, inheritance, mixins, teams, drift detection,
linting, and more), see the full PersonaNexus repository:

https://github.com/PersonaNexus/personanexus
