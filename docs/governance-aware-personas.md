# Governance-aware personas

PersonaNexus can now separate voice and style from a behavioral contract.

## Behavioral contract

Use `behavioral_contract` for governance-sensitive expectations that should stay distinct from tone:

- honesty
- uncertainty_disclosure
- refusal_posture
- boundary_strictness
- user_corrigibility
- confidentiality
- governance_sensitivity

Keep rhetorical voice in `communication`, and keep situational voice shifts in `behavioral_modes`.

## Task-mode overlays

Use `behavioral_contract.task_modes` when one identity needs different governance defaults for different jobs.

Example:

```bash
personanexus compile examples/identities/high-trust-board-advisor.yaml \
  --target anthropic \
  --task-mode careful_operator
```

The active task mode is reflected in structured compile outputs and in eval runs.

## Provider compatibility and drift hooks

Use `provider_compatibility` to declare where a persona is expected to behave well, and `drift_hooks` to record when re-certification should happen.

Compilation emits warnings when:

- a governance-sensitive identity is compiled to generic `text`
- the compile target is outside the declared provider matrix
- drift hooks exist without a compatibility matrix

## Governance evals

The eval harness now supports a `governance` assertion block so high-trust personas can be checked for contract alignment without needing a live model run.

Example suite fragment:

```yaml
assertions:
  governance:
    honesty: maximally_candid
    uncertainty_disclosure: explicit
    confidentiality: strict
    required_notes:
      - Escalate material ambiguity instead of bluffing.
```
